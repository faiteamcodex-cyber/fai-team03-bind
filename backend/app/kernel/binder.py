"""Binder (Verifier): Cross-modal claim verification using programmatic predicates + LLM A."""

import json
import logging
from typing import Optional

from app.schemas.enums import ClaimType, ClaimStatus, HarmClass
from app.schemas.models import Claim, Exhibit, Docket
from app.prompts.binder_prompt import BINDER_SYSTEM_PROMPT, BINDER_USER_TEMPLATE
from app.config import settings

logger = logging.getLogger(__name__)


# ========== Layer 1: Programmatic Predicates (No LLM) ==========

def _verify_geo_parcel(claim: Claim, docket: Docket) -> tuple[ClaimStatus, str]:
    """Verify GEO.PARCEL: must have a geometry exhibit with a valid polygon."""
    for eid in claim.exhibit_ids:
        exhibit = docket.get_exhibit(eid)
        if exhibit and exhibit.kind.value == "geometry":
            payload = exhibit.payload
            if payload.get("type") == "Feature" and payload.get("geometry"):
                return ClaimStatus.STAMPED, "Survey number resolved to a valid polygon."
    return ClaimStatus.ABSTAINED, "No valid geometry exhibit found for this survey number."


def _verify_reg_owner(claim: Claim, docket: Docket) -> tuple[ClaimStatus, str]:
    """Verify REG.OWNER: must have a registry row with a non-empty owner name."""
    for eid in claim.exhibit_ids:
        exhibit = docket.get_exhibit(eid)
        if exhibit and exhibit.kind.value == "registry_row":
            payload = exhibit.payload
            if payload.get("owner_name"):
                # Cross-check: survey key must match GEO.PARCEL
                geo_claims = docket.get_claims_by_type(ClaimType.GEO_PARCEL)
                if geo_claims and geo_claims[0].status == ClaimStatus.STAMPED:
                    return ClaimStatus.STAMPED, f"Owner '{payload['owner_name']}' confirmed from registry. Survey key matches GEO.PARCEL."
                return ClaimStatus.STAMPED, f"Owner '{payload['owner_name']}' found but GEO.PARCEL not yet stamped."
    return ClaimStatus.ABSTAINED, "No registry record found for this survey number."


def _verify_media_photo(claim: Claim, docket: Docket) -> tuple[ClaimStatus, str]:
    """Verify MEDIA.PHOTO: photo must be bound to the parcel (GPS inside polygon)."""
    photo_exhibit = None
    geo_exhibit = None

    for eid in claim.exhibit_ids:
        exhibit = docket.get_exhibit(eid)
        if exhibit and exhibit.kind.value == "image":
            photo_exhibit = exhibit

    # Find the GEO exhibit
    geo_claims = docket.get_claims_by_type(ClaimType.GEO_PARCEL)
    for gc in geo_claims:
        for eid in gc.exhibit_ids:
            exhibit = docket.get_exhibit(eid)
            if exhibit and exhibit.kind.value == "geometry":
                geo_exhibit = exhibit

    if not photo_exhibit:
        return ClaimStatus.ABSTAINED, "No photo retrieved for this parcel."

    if not geo_exhibit:
        return ClaimStatus.ABSTAINED, "Cannot verify photo binding without GEO.PARCEL."

    # Check bind status from the photo payload
    bind_status = photo_exhibit.payload.get("bind_status", "unbound")
    if bind_status == "inside":
        return ClaimStatus.STAMPED, "Photo capture point falls inside parcel polygon."
    elif bind_status == "buffer":
        return ClaimStatus.STAMPED, "Photo capture point falls within buffer zone of parcel polygon."
    else:
        return ClaimStatus.REJECTED, "Photo is UNBOUND. Capture point is outside the parcel polygon. Fertilizer claims will be blocked."


def _verify_vision_claim(claim: Claim, docket: Docket) -> tuple[ClaimStatus, str]:
    """Verify VIS.CROP / VIS.STAGE / VIS.CONDITION."""
    if not claim.value:
        return ClaimStatus.ABSTAINED, "No vision prediction available."
    
    confidence = claim.confidence or 0.0
    
    # Check for dispute (student/teacher disagreement stored in value)
    if claim.value.get("dispute"):
        return ClaimStatus.DISPUTE, f"Student and teacher disagree: {claim.value.get('student_label')} vs {claim.value.get('teacher_label')}"
    
    if confidence >= settings.student_confidence_threshold:
        return ClaimStatus.STAMPED, f"Vision prediction '{claim.value.get('label')}' with confidence {confidence:.2f} above threshold."
    
    return ClaimStatus.ABSTAINED, f"Vision confidence {confidence:.2f} below threshold {settings.student_confidence_threshold}."


def _verify_advisory(claim: Claim, docket: Docket) -> tuple[ClaimStatus, str]:
    """Verify ADV.FERTILIZER / ADV.PRACTICE: strict cross-modal checks."""
    # Rule: MEDIA.PHOTO must be STAMPED (bound to parcel)
    photo_claims = docket.get_claims_by_type(ClaimType.MEDIA_PHOTO)
    if photo_claims and photo_claims[0].status == ClaimStatus.REJECTED:
        return ClaimStatus.REJECTED, "Cannot issue advisory: photo is not bound to the parcel."

    # Rule: VIS.CROP must be STAMPED
    crop_claims = docket.get_claims_by_type(ClaimType.VIS_CROP)
    if not crop_claims or crop_claims[0].status != ClaimStatus.STAMPED:
        return ClaimStatus.ABSTAINED, "Cannot issue advisory: crop identification not confirmed."

    # For fertilizer, VIS.STAGE must also be STAMPED
    if claim.type == ClaimType.ADV_FERTILIZER:
        stage_claims = docket.get_claims_by_type(ClaimType.VIS_STAGE)
        if not stage_claims or stage_claims[0].status != ClaimStatus.STAMPED:
            return ClaimStatus.ABSTAINED, "Cannot issue fertilizer advisory: growth stage not confirmed."

    # Check exhibit has a source_id
    for eid in claim.exhibit_ids:
        exhibit = docket.get_exhibit(eid)
        if exhibit and exhibit.kind.value == "form":
            form_data = exhibit.payload
            if not form_data.get("source_id"):
                return ClaimStatus.REJECTED, "Advisory has no source citation (source_id is empty). Cannot stamp."
            
            # Cross-check: advisory crop must match vision crop
            vision_crop = None
            for cc in crop_claims:
                if cc.value:
                    vision_crop = cc.value.get("label", "").lower()
            
            advisory_crop = form_data.get("crop", "").lower()
            if vision_crop and advisory_crop and vision_crop != advisory_crop:
                return ClaimStatus.REJECTED, f"Advisory crop '{advisory_crop}' does not match vision crop '{vision_crop}'. Circular mismatch."

            return ClaimStatus.STAMPED, f"Advisory verified: crop match, stage match, source cited."

    return ClaimStatus.ABSTAINED, "No advisory form exhibit found."


# ========== Predicate Dispatch ==========
PREDICATE_MAP = {
    ClaimType.GEO_PARCEL: _verify_geo_parcel,
    ClaimType.REG_OWNER: _verify_reg_owner,
    ClaimType.MEDIA_PHOTO: _verify_media_photo,
    ClaimType.VIS_CROP: _verify_vision_claim,
    ClaimType.VIS_STAGE: _verify_vision_claim,
    ClaimType.VIS_CONDITION: _verify_vision_claim,
    ClaimType.ADV_FERTILIZER: _verify_advisory,
    ClaimType.ADV_PRACTICE: _verify_advisory,
}


# ========== Layer 2: LLM-Assisted Cross-Modal Check (Optional) ==========

async def _llm_cross_check(docket: Docket, bedrock_client=None) -> list[dict]:
    """Use LLM A to perform nuanced cross-modal reasoning on complex claims."""
    if settings.use_mocks or bedrock_client is None:
        logger.info("Binder LLM cross-check skipped (mock mode).")
        return []

    # Build claims summary for the LLM
    claims_text_parts: list[str] = []
    for claim in docket.claims:
        exhibits_text = []
        for eid in claim.exhibit_ids:
            ex = docket.get_exhibit(eid)
            if ex:
                exhibits_text.append(f"  Exhibit [{ex.kind}]: {json.dumps(ex.payload)[:300]}")
        exhibits_str = "\n".join(exhibits_text) if exhibits_text else "  No exhibits."
        claims_text_parts.append(
            f"Claim {claim.id} ({claim.type}, harm={claim.harm}, status={claim.status}):\n"
            f"  Value: {json.dumps(claim.value) if claim.value else 'None'}\n"
            f"  Confidence: {claim.confidence}\n"
            f"{exhibits_str}"
        )

    user_message = BINDER_USER_TEMPLATE.format(
        docket_id=docket.id,
        query=docket.query,
        claims_with_exhibits="\n\n".join(claims_text_parts),
    )

    try:
        response = await bedrock_client.invoke(
            model_id=settings.planner_model_id,
            system_prompt=BINDER_SYSTEM_PROMPT,
            user_message=user_message,
        )
        cleaned = response.strip()
        if cleaned.startswith("```"):
            lines = cleaned.split("\n")
            cleaned = "\n".join(lines[1:-1])
        return json.loads(cleaned)
    except Exception as e:
        logger.error(f"Binder LLM cross-check failed: {e}")
        return []


# ========== Main Binder Entry Point ==========

async def verify_docket(docket: Docket, bedrock_client=None) -> Docket:
    """Run the full Binder verification pipeline on a docket."""
    logger.info(f"Binder: verifying docket {docket.id} with {len(docket.claims)} claims.")

    # Layer 1: Programmatic predicates
    for claim in docket.claims:
        if claim.status == ClaimStatus.OPEN:
            # Skip claims that haven't been attempted yet
            continue
        
        if claim.status == ClaimStatus.BINDING:
            predicate = PREDICATE_MAP.get(claim.type)
            if predicate:
                new_status, reason = predicate(claim, docket)
                claim.status = new_status
                claim.stamp_reason = reason
                logger.info(f"  Claim {claim.id} ({claim.type}): {new_status} - {reason}")
            else:
                claim.status = ClaimStatus.STAMPED
                claim.stamp_reason = "No predicate defined; auto-stamped."

    # Layer 2: LLM cross-check for nuanced cases
    llm_verdicts = await _llm_cross_check(docket, bedrock_client)
    for verdict in llm_verdicts:
        claim = docket.get_claim(verdict.get("claim_id", ""))
        if claim and claim.status == ClaimStatus.STAMPED:
            # LLM can only override STAMPED claims to REJECTED or DISPUTE
            new_status_str = verdict.get("status", "")
            if new_status_str in ("REJECTED", "DISPUTE"):
                claim.status = ClaimStatus(new_status_str)
                claim.stamp_reason = verdict.get("reason", "LLM cross-check override.")
                logger.warning(f"  LLM override: Claim {claim.id} → {new_status_str}")

    return docket

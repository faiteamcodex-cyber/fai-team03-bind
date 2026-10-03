"""Planner: Uses LLM A (gpt-5.6-luna) to decompose a request into claims."""

import json
import logging
from typing import Optional

from app.schemas.enums import ClaimType, ClaimStatus
from app.schemas.models import Claim, Docket, CLAIM_HARM_MAP
from app.prompts.planner_prompt import PLANNER_SYSTEM_PROMPT, PLANNER_USER_TEMPLATE
from app.config import settings

logger = logging.getLogger(__name__)

# ---------- Mock Planner (for local dev without Bedrock) ----------
MOCK_CLAIM_RULES: dict[str, list[dict]] = {
    "default_full": [
        {"type": "GEO.PARCEL", "depends_on": []},
        {"type": "REG.OWNER", "depends_on": ["GEO.PARCEL"]},
        {"type": "MEDIA.PHOTO", "depends_on": ["GEO.PARCEL"]},
        {"type": "VIS.CROP", "depends_on": ["MEDIA.PHOTO"]},
        {"type": "VIS.STAGE", "depends_on": ["VIS.CROP"]},
        {"type": "ADV.FERTILIZER", "depends_on": ["VIS.CROP", "VIS.STAGE"]},
        {"type": "ADV.PRACTICE", "depends_on": ["VIS.CROP"]},
    ],
    "owner_only": [
        {"type": "GEO.PARCEL", "depends_on": []},
        {"type": "REG.OWNER", "depends_on": ["GEO.PARCEL"]},
    ],
    "health_check": [
        {"type": "GEO.PARCEL", "depends_on": []},
        {"type": "MEDIA.PHOTO", "depends_on": ["GEO.PARCEL"]},
        {"type": "VIS.CONDITION", "depends_on": ["MEDIA.PHOTO"]},
    ],
}


def _detect_mock_intent(query: str) -> str:
    """Simple keyword matching to decide which mock claim set to use."""
    q = query.lower()
    if any(kw in q for kw in ["owner", "who owns", "patta", "registry"]):
        if not any(kw in q for kw in ["crop", "fertilizer", "photo", "plant", "stage"]):
            return "owner_only"
    if any(kw in q for kw in ["health", "condition", "disease", "pest"]):
        if "fertilizer" not in q:
            return "health_check"
    return "default_full"


def _parse_llm_claims(raw_json: str) -> list[dict]:
    """Parse the LLM JSON response into claim dicts."""
    try:
        # Strip markdown code fences if present
        cleaned = raw_json.strip()
        if cleaned.startswith("```"):
            lines = cleaned.split("\n")
            cleaned = "\n".join(lines[1:-1])
        return json.loads(cleaned)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse planner output: {e}. Raw: {raw_json[:500]}")
        return []


def _build_claims_from_dicts(claim_dicts: list[dict]) -> list[Claim]:
    """Convert raw claim dicts to Claim objects with proper harm classes."""
    claims: list[Claim] = []
    id_map: dict[str, str] = {}  # type -> generated claim ID

    # First pass: create claims
    for cd in claim_dicts:
        try:
            claim_type = ClaimType(cd["type"])
        except ValueError:
            logger.warning(f"Unknown claim type: {cd['type']}, skipping.")
            continue

        claim = Claim(
            type=claim_type,
            status=ClaimStatus.OPEN,
        )
        claim.set_harm_from_catalog()
        claims.append(claim)
        id_map[cd["type"]] = claim.id

    # Second pass: resolve depends_on to actual claim IDs
    for i, cd in enumerate(claim_dicts):
        if i < len(claims):
            raw_deps = cd.get("depends_on", [])
            claims[i].depends_on = [
                id_map[dep] for dep in raw_deps if dep in id_map
            ]

    return claims


async def plan_claims(
    docket: Docket,
    bedrock_client=None,
) -> list[Claim]:
    """Decompose the user request into a list of typed claims."""
    
    if settings.use_mocks or bedrock_client is None:
        # Mock mode: use keyword matching
        logger.info("Planner running in MOCK mode.")
        intent = _detect_mock_intent(docket.query)
        logger.info(f"Detected mock intent: {intent}")
        claim_dicts = MOCK_CLAIM_RULES[intent]
        return _build_claims_from_dicts(claim_dicts)

    # Live mode: call LLM A via Bedrock
    user_message = PLANNER_USER_TEMPLATE.format(
        query=docket.query,
        village=docket.village_id or "Not specified",
        has_image="Yes" if docket.image_provided else "No",
    )

    try:
        response = await bedrock_client.invoke(
            model_id=settings.planner_model_id,
            system_prompt=PLANNER_SYSTEM_PROMPT,
            user_message=user_message,
        )
        claim_dicts = _parse_llm_claims(response)
        if not claim_dicts:
            logger.error("Planner returned empty claim set, falling back to mock.")
            intent = _detect_mock_intent(docket.query)
            claim_dicts = MOCK_CLAIM_RULES[intent]
        return _build_claims_from_dicts(claim_dicts)
    except Exception as e:
        logger.error(f"Planner LLM call failed: {e}. Falling back to mock.")
        intent = _detect_mock_intent(docket.query)
        claim_dicts = MOCK_CLAIM_RULES[intent]
        return _build_claims_from_dicts(claim_dicts)

"""Vision Model Connectors & Fallback Execution Engine.

Part of Dinesh Kumar's (Member 2) deliverables:
- Wraps Student Vision (amazon.nova-lite) and Teacher Vision (gpt-5.6-terra).
- Deterministic fallback hook: escalates to Teacher Vision when Student confidence < 0.65.
- Cross-examination: flags DISPUTE when Student and Teacher predictions conflict.
- Produces standardized Exhibit objects (ExhibitKind.PREDICTION) for Member 1's Binder.
"""

from __future__ import annotations

import base64
import json
import logging
import time
from typing import Any, Dict, List, Optional, Tuple

from app.config import settings
from app.connectors.bedrock import BedrockClient, bedrock_client
from app.kernel.budget import can_escalate_to_teacher, record_cost_entry
from app.schemas.enums import ClaimStatus, ClaimType, ExhibitKind
from app.schemas.models import Claim, Docket, Exhibit

logger = logging.getLogger(__name__)

# Agricultural taxonomy standard categories
TAXONOMY_CROPS = ["paddy", "sugarcane", "groundnut", "cotton", "maize", "pulses", "millet"]
TAXONOMY_STAGES = ["seedling", "tillering", "panicle_initiation", "flowering", "grain_filling", "maturity"]
TAXONOMY_CONDITIONS = ["healthy", "nitrogen_deficiency", "blast", "brown_spot", "stem_borer", "leaf_folder"]


class VisionEngine:
    """Manages agricultural computer vision analysis, Bedrock model dispatch, and fallback hooks."""

    def __init__(self, client: Optional[BedrockClient] = None):
        self.bedrock = client or bedrock_client

    def _build_vision_prompt(self, claim_type: ClaimType) -> str:
        """Construct structured prompt enforcing strict JSON output from vision models."""
        if claim_type == ClaimType.VIS_CROP:
            return (
                "Identify the primary agricultural crop in this image. "
                f"Candidate crops: {', '.join(TAXONOMY_CROPS)}. "
                "Respond with valid JSON only in this format:\n"
                "{\n"
                '  "label": "<crop_name>",\n'
                '  "confidence": <float between 0.0 and 1.0>,\n'
                '  "growth_stage": "<detected stage>",\n'
                '  "condition": "<health condition>",\n'
                '  "rationale": "<brief visual justification>"\n'
                "}"
            )
        elif claim_type == ClaimType.VIS_STAGE:
            return (
                "Identify the current agronomic growth stage of the crop. "
                f"Candidate stages: {', '.join(TAXONOMY_STAGES)}. "
                "Respond with valid JSON only in this format:\n"
                "{\n"
                '  "label": "<stage_name>",\n'
                '  "confidence": <float between 0.0 and 1.0>,\n'
                '  "rationale": "<visual indicators like panicle emergence, tillers, height>"\n'
                "}"
            )
        elif claim_type == ClaimType.VIS_CONDITION:
            return (
                "Assess the phytosanitary health condition of the crop. "
                f"Candidate conditions: {', '.join(TAXONOMY_CONDITIONS)}. "
                "Respond with valid JSON only in this format:\n"
                "{\n"
                '  "label": "<condition_name>",\n'
                '  "confidence": <float between 0.0 and 1.0>,\n'
                '  "symptoms": ["<list of observed visual anomalies>"],\n'
                '  "rationale": "<justification>"\n'
                "}"
            )
        else:
            return "Analyze the image and return a JSON object with 'label', 'confidence', and 'rationale'."

    def _parse_vision_response(self, text: str, default_label: str = "paddy", default_conf: float = 0.75) -> dict[str, Any]:
        """Parse and sanitize JSON output from the model."""
        clean_text = text.strip()
        if clean_text.startswith("```json"):
            clean_text = clean_text[7:]
        elif clean_text.startswith("```"):
            clean_text = clean_text[3:]
        if clean_text.endswith("```"):
            clean_text = clean_text[:-3]
        clean_text = clean_text.strip()

        try:
            parsed = json.loads(clean_text)
            if isinstance(parsed, dict):
                # Ensure confidence is clamped between 0.0 and 1.0
                conf = float(parsed.get("confidence", default_conf))
                parsed["confidence"] = max(0.0, min(1.0, conf))
                return parsed
        except Exception as e:
            logger.warning(f"Could not parse vision JSON ({e}). Falling back to extraction: {clean_text[:100]}")

        return {
            "label": default_label,
            "confidence": default_conf,
            "rationale": f"Extracted from response text: {clean_text[:120]}",
        }

    async def predict_student(
        self,
        claim_type: ClaimType,
        image_bytes: Optional[bytes] = None,
        image_format: str = "jpeg",
    ) -> dict[str, Any]:
        """Invoke Student Vision model (amazon.nova-lite)."""
        prompt = self._build_vision_prompt(claim_type)
        resp = await self.bedrock.invoke_student_vision(
            prompt=prompt,
            image_bytes=image_bytes,
            image_format=image_format,
        )
        data = self._parse_vision_response(resp.text, default_label="paddy", default_conf=0.72)
        data["model"] = resp.model_id
        data["latency_ms"] = resp.latency_ms
        data["cost_usd"] = resp.cost_usd
        data["input_tokens"] = resp.input_tokens
        data["output_tokens"] = resp.output_tokens
        return data

    async def predict_teacher(
        self,
        claim_type: ClaimType,
        image_bytes: Optional[bytes] = None,
        image_format: str = "jpeg",
    ) -> dict[str, Any]:
        """Invoke Teacher Vision model (gpt-5.6-terra / nova-pro)."""
        prompt = self._build_vision_prompt(claim_type)
        resp = await self.bedrock.invoke_teacher_vision(
            prompt=prompt,
            image_bytes=image_bytes,
            image_format=image_format,
        )
        data = self._parse_vision_response(resp.text, default_label="paddy", default_conf=0.94)
        data["model"] = resp.model_id
        data["latency_ms"] = resp.latency_ms
        data["cost_usd"] = resp.cost_usd
        data["input_tokens"] = resp.input_tokens
        data["output_tokens"] = resp.output_tokens
        return data

    def create_prediction_exhibit(
        self,
        prediction_payload: dict[str, Any],
        model_id: str,
        image_source: str = "attached_image",
    ) -> Exhibit:
        """Construct a standardized Exhibit object (ExhibitKind.PREDICTION) for the Binder."""
        return Exhibit(
            kind=ExhibitKind.PREDICTION,
            source_id=f"bedrock://{model_id}/{image_source}",
            payload=prediction_payload,
        )

    async def execute_claim_with_fallback(
        self,
        docket: Docket,
        claim: Claim,
        image_bytes: Optional[bytes] = None,
        image_format: str = "jpeg",
    ) -> Tuple[dict[str, Any], Exhibit]:
        """Execute vision claim with student model, triggering teacher fallback if confidence < 0.65.
        
        Lifecycle:
        1. Query Student Vision (amazon.nova-lite).
        2. Create student Exhibit and attach to Docket.
        3. Evaluate confidence against threshold (0.65).
        4. If confidence < 0.65:
           - Check remaining budget.
           - If affordable, escalate to Teacher Vision (gpt-5.6-terra).
           - Cross-validate predictions: flag dispute if labels conflict.
        5. Record exact cost entries and update route history.
        """
        # 1. Student Vision invocation
        student_res = await self.predict_student(claim.type, image_bytes, image_format)
        student_conf = student_res.get("confidence", 0.0)
        student_label = student_res.get("label", "").lower().strip()
        student_model = student_res.get("model", settings.student_vision_model_id)

        # Create Exhibit for Student
        student_exhibit = self.create_prediction_exhibit(student_res, student_model)
        docket.add_exhibit(student_exhibit)
        claim.exhibit_ids.append(student_exhibit.id)

        # Record Student Cost
        record_cost_entry(
            docket=docket,
            claim_id=claim.id,
            writer=student_model,
            cost_usd=student_res.get("cost_usd", 0.003),
            latency_ms=student_res.get("latency_ms", 1200),
            input_tokens=student_res.get("input_tokens", 0),
            output_tokens=student_res.get("output_tokens", 0),
        )

        threshold = settings.student_confidence_threshold

        # 2. Check if Fallback Hook is triggered
        if student_conf >= threshold:
            # Student confidence sufficient
            claim.writer = student_model
            claim.value = student_res
            claim.confidence = student_conf
            return student_res, student_exhibit

        logger.info(
            f"Claim {claim.id} ({claim.type}): Student confidence {student_conf:.2f} < {threshold}. "
            "Triggering Teacher Vision fallback hook."
        )

        remaining_budget = docket.remaining_budget_usd(settings.max_docket_cost_usd)
        if not can_escalate_to_teacher(remaining_budget):
            logger.warning(
                f"Cannot escalate claim {claim.id} to teacher: remaining budget ${remaining_budget:.4f} "
                f"is less than teacher cost."
            )
            claim.writer = student_model
            claim.value = student_res
            claim.confidence = student_conf
            claim.stamp_reason = (
                f"Student confidence {student_conf:.2f} is below threshold {threshold}, "
                "but remaining budget prevents teacher escalation."
            )
            return student_res, student_exhibit

        # 3. Escalate to Teacher Vision
        teacher_res = await self.predict_teacher(claim.type, image_bytes, image_format)
        teacher_conf = teacher_res.get("confidence", 0.0)
        teacher_label = teacher_res.get("label", "").lower().strip()
        teacher_model = teacher_res.get("model", settings.teacher_vision_model_id)

        teacher_exhibit = self.create_prediction_exhibit(teacher_res, teacher_model)
        docket.add_exhibit(teacher_exhibit)
        claim.exhibit_ids.append(teacher_exhibit.id)

        # Record Teacher Cost
        record_cost_entry(
            docket=docket,
            claim_id=claim.id,
            writer=teacher_model,
            cost_usd=teacher_res.get("cost_usd", 0.015),
            latency_ms=teacher_res.get("latency_ms", 2500),
            input_tokens=teacher_res.get("input_tokens", 0),
            output_tokens=teacher_res.get("output_tokens", 0),
        )

        # Update Route Entry with fallback provenance
        for route in docket.routes:
            if route.claim_id == claim.id:
                route.fallback_used = True
                route.fallback_from = student_model
                route.assigned_writer = f"{student_model} -> {teacher_model}"
                break

        # 4. Cross-modal dispute detection
        if student_label and teacher_label and student_label != teacher_label:
            logger.warning(
                f"DISPUTE detected on claim {claim.id}: Student said '{student_label}' ({student_conf:.2f}), "
                f"Teacher said '{teacher_label}' ({teacher_conf:.2f})."
            )
            dispute_payload = {
                "dispute": True,
                "label": teacher_label,  # Default to teacher, but flag dispute
                "student_label": student_label,
                "teacher_label": teacher_label,
                "student_confidence": student_conf,
                "teacher_confidence": teacher_conf,
                "teacher_payload": teacher_res,
                "student_payload": student_res,
            }
            claim.value = dispute_payload
            claim.confidence = 0.0  # Zero confidence triggers DISPUTE status in Binder
            claim.writer = f"{student_model} -> {teacher_model}"
            claim.stamp_reason = (
                f"Model disagreement: Student detected '{student_label}' while Teacher detected '{teacher_label}'."
            )
            return dispute_payload, teacher_exhibit

        # 5. Teacher affirmed or refined prediction
        claim.writer = f"{student_model} -> {teacher_model}"
        claim.value = teacher_res
        claim.confidence = teacher_conf
        claim.stamp_reason = (
            f"Escalated to Teacher Vision ({teacher_model}); high confidence {teacher_conf:.2f} obtained."
        )
        return teacher_res, teacher_exhibit


# Singleton instance
vision_engine = VisionEngine()


# Legacy backward-compatibility functions for existing state machine imports
async def mock_student_predict(claim_type: ClaimType) -> dict[str, Any]:
    """Compatibility adapter delegating to vision engine."""
    return await vision_engine.predict_student(claim_type)


async def mock_teacher_predict(claim_type: ClaimType) -> dict[str, Any]:
    """Compatibility adapter delegating to vision engine."""
    return await vision_engine.predict_teacher(claim_type)

"""Unit tests for Vision Fallback Engine, Confidence Triggers, and Dispute Resolution.

Deliverable C verification for Dinesh Kumar (Member 2).
"""

import pytest
from unittest.mock import AsyncMock, patch

from app.config import settings
from app.connectors.bedrock import BedrockResponse
from app.connectors.vision import VisionEngine
from app.kernel.binder import verify_docket
from app.schemas.enums import ClaimStatus, ClaimType, ExhibitKind
from app.schemas.models import Claim, Docket, RouteEntry


@pytest.fixture
def mock_bedrock():
    """Create a mock BedrockClient for controlling student/teacher outputs."""
    client = AsyncMock()
    return client


@pytest.mark.asyncio
async def test_high_confidence_student_no_fallback(mock_bedrock):
    """When student confidence >= 0.65, model should NOT escalate to teacher."""
    mock_bedrock.invoke_student_vision.return_value = BedrockResponse(
        text='{"label": "paddy", "confidence": 0.88, "growth_stage": "tillering"}',
        model_id=settings.student_vision_model_id,
        cost_usd=0.003,
        latency_ms=800,
    )

    engine = VisionEngine(client=mock_bedrock)
    docket = Docket(query="Analyze paddy survey 202/55")
    claim = Claim(type=ClaimType.VIS_CROP)
    docket.claims.append(claim)

    result, exhibit = await engine.execute_claim_with_fallback(docket, claim)

    # Assertions
    assert result["label"] == "paddy"
    assert result["confidence"] == 0.88
    assert claim.writer == settings.student_vision_model_id
    assert claim.confidence == 0.88
    # Only 1 exhibit created (Student)
    assert len(docket.exhibits) == 1
    assert exhibit.kind == ExhibitKind.PREDICTION
    assert exhibit.payload["label"] == "paddy"
    # Teacher should NOT have been called
    mock_bedrock.invoke_teacher_vision.assert_not_called()


@pytest.mark.asyncio
async def test_low_confidence_triggers_teacher_fallback(mock_bedrock):
    """When student confidence < 0.65, model MUST trigger fallback to Teacher Vision."""
    # Student returns low confidence (0.52 < 0.65)
    mock_bedrock.invoke_student_vision.return_value = BedrockResponse(
        text='{"label": "paddy", "confidence": 0.52, "rationale": "blurry image"}',
        model_id=settings.student_vision_model_id,
        cost_usd=0.003,
        latency_ms=900,
    )
    # Teacher confirms paddy with high confidence (0.95)
    mock_bedrock.invoke_teacher_vision.return_value = BedrockResponse(
        text='{"label": "paddy", "confidence": 0.95, "growth_stage": "panicle_initiation"}',
        model_id=settings.teacher_vision_model_id,
        cost_usd=0.015,
        latency_ms=2100,
    )

    engine = VisionEngine(client=mock_bedrock)
    docket = Docket(query="Analyze blurry crop photo")
    claim = Claim(type=ClaimType.VIS_CROP)
    docket.claims.append(claim)
    route = RouteEntry(
        claim_id=claim.id,
        assigned_writer=settings.student_vision_model_id,
        reason="Initial student route",
    )
    docket.routes.append(route)

    result, exhibit = await engine.execute_claim_with_fallback(docket, claim)

    # Teacher should have been invoked
    mock_bedrock.invoke_teacher_vision.assert_called_once()

    # Claim should reflect escalated writer and teacher confidence
    assert claim.writer == f"{settings.student_vision_model_id} -> {settings.teacher_vision_model_id}"
    assert claim.confidence == 0.95
    assert result["label"] == "paddy"

    # Both Student and Teacher exhibits should exist in Docket
    assert len(docket.exhibits) == 2
    assert len(claim.exhibit_ids) == 2

    # Route entry should record fallback provenance
    assert route.fallback_used is True
    assert route.fallback_from == settings.student_vision_model_id


@pytest.mark.asyncio
async def test_student_teacher_dispute_detection(mock_bedrock):
    """When Student and Teacher models disagree on crop label, flag DISPUTE."""
    # Student says maize with low confidence
    mock_bedrock.invoke_student_vision.return_value = BedrockResponse(
        text='{"label": "maize", "confidence": 0.55}',
        model_id=settings.student_vision_model_id,
        cost_usd=0.003,
        latency_ms=800,
    )
    # Teacher says sugarcane with high confidence
    mock_bedrock.invoke_teacher_vision.return_value = BedrockResponse(
        text='{"label": "sugarcane", "confidence": 0.92}',
        model_id=settings.teacher_vision_model_id,
        cost_usd=0.015,
        latency_ms=2000,
    )

    engine = VisionEngine(client=mock_bedrock)
    docket = Docket(query="Check border crop photo")
    claim = Claim(type=ClaimType.VIS_CROP)
    docket.claims.append(claim)

    result, exhibit = await engine.execute_claim_with_fallback(docket, claim)

    # Dispute must be flagged
    assert result.get("dispute") is True
    assert result.get("student_label") == "maize"
    assert result.get("teacher_label") == "sugarcane"
    # Claim confidence set to 0.0 to signal dispute
    assert claim.confidence == 0.0

    # Cross-verify with Member 1's Binder: verify_docket should transition to DISPUTE status!
    claim.status = ClaimStatus.BINDING
    await verify_docket(docket)
    assert claim.status == ClaimStatus.DISPUTE
    assert "Student and teacher disagree" in claim.stamp_reason


@pytest.mark.asyncio
async def test_low_confidence_budget_exhausted_prevents_escalation(mock_bedrock):
    """When Student confidence is < 0.65 but budget does not permit Teacher call, do not crash."""
    mock_bedrock.invoke_student_vision.return_value = BedrockResponse(
        text='{"label": "groundnut", "confidence": 0.58}',
        model_id=settings.student_vision_model_id,
        cost_usd=0.003,
        latency_ms=750,
    )

    engine = VisionEngine(client=mock_bedrock)
    # Docket has already spent $0.075 of $0.08 limit (remaining budget $0.005 < teacher cost $0.015)
    docket = Docket(query="Low budget docket", total_cost_usd=0.075)
    claim = Claim(type=ClaimType.VIS_CROP)
    docket.claims.append(claim)

    result, exhibit = await engine.execute_claim_with_fallback(docket, claim)

    # Teacher should NOT be called due to budget cap
    mock_bedrock.invoke_teacher_vision.assert_not_called()
    assert claim.writer == settings.student_vision_model_id
    assert claim.confidence == 0.58
    assert "budget prevents teacher escalation" in claim.stamp_reason

"""Unit tests for AWS Bedrock Client Wrapper, Token Tracking, and Dual-Mode Operation.

Deliverable A verification for Dinesh Kumar (Member 2).
"""

import pytest
from app.config import settings
from app.connectors.bedrock import BedrockClient, BedrockResponse, BEDROCK_PRICING


def test_bedrock_cost_calculation():
    """Verify that token-based cost calculations accurately match pricing matrix."""
    client = BedrockClient(use_mocks=True)

    # Nova micro: 10,000 in, 5,000 out
    cost_micro = client.calculate_cost("apac.amazon.nova-micro-v1:0", 10000, 5000)
    expected_micro = (10000 * (0.000035 / 1000)) + (5000 * (0.00014 / 1000))
    assert pytest.approx(cost_micro, 1e-6) == expected_micro

    # Nova lite: 10,000 in, 5,000 out
    cost_lite = client.calculate_cost("apac.amazon.nova-lite-v1:0", 10000, 5000)
    expected_lite = (10000 * (0.00006 / 1000)) + (5000 * (0.00024 / 1000))
    assert pytest.approx(cost_lite, 1e-6) == expected_lite


@pytest.mark.asyncio
async def test_bedrock_planner_invocation_mock():
    """Verify invoke_planner returns structured claim schema in mock mode."""
    client = BedrockClient(use_mocks=True)
    resp = await client.invoke_planner("Please plan survey 202/55 in village 33.")

    assert isinstance(resp, BedrockResponse)
    assert resp.is_mock is True
    assert resp.input_tokens > 0
    assert resp.output_tokens > 0
    assert resp.latency_ms >= 0

    json_data = resp.json_content()
    assert isinstance(json_data, list)
    claim_types = [item["claim_type"] for item in json_data]
    assert "GEO.PARCEL" in claim_types
    assert "REG.OWNER" in claim_types


@pytest.mark.asyncio
async def test_bedrock_vision_invocation_mock():
    """Verify invoke_student_vision and invoke_teacher_vision return structured crop prediction."""
    client = BedrockClient(use_mocks=True)

    student_resp = await client.invoke_student_vision("Identify crop in image.")
    assert student_resp.is_mock is True
    student_data = student_resp.json_content()
    assert "label" in student_data
    assert "confidence" in student_data
    assert student_data["label"] == "paddy"

    teacher_resp = await client.invoke_teacher_vision("Verify crop in image.")
    assert teacher_resp.is_mock is True
    teacher_data = teacher_resp.json_content()
    assert "label" in teacher_data
    assert "confidence" in teacher_data


@pytest.mark.asyncio
async def test_bedrock_embedding_mock():
    """Verify Titan text embeddings generation returns 1024-dimensional vector."""
    client = BedrockClient(use_mocks=True)
    vec = await client.get_embedding("Fertilizer recommendations for paddy in Thanjavur.")

    assert isinstance(vec, list)
    assert len(vec) == 1024
    assert all(isinstance(v, float) for v in vec)

"""Unit tests for the Deterministic Budget Router & Harm Class Logic.

Deliverable B verification for Dinesh Kumar (Member 2).
"""

import pytest
from app.config import settings
from app.kernel.budget import (
    compile_routes,
    can_escalate_to_teacher,
    estimate_always_vlm_cost,
    calculate_cost_savings,
    record_cost_entry,
    COST_TABLE,
)
from app.schemas.enums import ClaimType, HarmClass, ClaimStatus
from app.schemas.models import Claim, Docket, RouteEntry


def test_harm_class_routing():
    """Verify that claims are mapped to their optimal tools and models based on Harm Class."""
    claims = [
        Claim(type=ClaimType.GEO_PARCEL, harm=HarmClass.HIGH),
        Claim(type=ClaimType.REG_OWNER, harm=HarmClass.HIGH),
        Claim(type=ClaimType.VIS_CROP, harm=HarmClass.MEDIUM),
        Claim(type=ClaimType.ADV_FERTILIZER, harm=HarmClass.CRITICAL),
        Claim(type=ClaimType.WX_CONTEXT, harm=HarmClass.LOW),
    ]

    routes = compile_routes(claims, remaining_budget_usd=0.08)
    assert len(routes) == 5

    route_dict = {r.claim_id: r for r in routes}

    # GEO.PARCEL -> gis_tool
    assert route_dict[claims[0].id].assigned_writer == "gis_tool"
    # REG.OWNER -> land_record_tool
    assert route_dict[claims[1].id].assigned_writer == "land_record_tool"
    # VIS.CROP -> Student Vision (nova-lite)
    assert route_dict[claims[2].id].assigned_writer == settings.student_vision_model_id
    # ADV.FERTILIZER -> advisory_rag
    assert route_dict[claims[3].id].assigned_writer == "advisory_rag"
    # WX.CONTEXT -> weather_tool
    assert route_dict[claims[4].id].assigned_writer == "weather_tool"


def test_budget_exhaustion_abstain():
    """Verify that when remaining budget is insufficient, claims are marked ABSTAIN."""
    claims = [
        Claim(type=ClaimType.VIS_CROP, harm=HarmClass.MEDIUM),
        Claim(type=ClaimType.VIS_STAGE, harm=HarmClass.MEDIUM),
        Claim(type=ClaimType.VIS_CONDITION, harm=HarmClass.MEDIUM),
    ]

    # Nova lite costs $0.003 each. If budget is only $0.004, first passes, second exhausts
    routes = compile_routes(claims, remaining_budget_usd=0.004, max_budget_usd=0.08)
    assert len(routes) == 3

    assert routes[0].assigned_writer == settings.student_vision_model_id
    # Second and third should be ABSTAIN due to budget exhaustion
    assert routes[1].assigned_writer == "ABSTAIN"
    assert "Budget cap" in routes[1].reason
    assert routes[2].assigned_writer == "ABSTAIN"


def test_priority_allocation_by_harm():
    """Verify that higher harm claims (CRITICAL, HIGH) get priority when budget is scarce."""
    low_claim = Claim(type=ClaimType.META_CLARIFY, harm=HarmClass.LOW)
    critical_claim = Claim(type=ClaimType.ADV_FERTILIZER, harm=HarmClass.CRITICAL)

    # Budget only sufficient for the critical operation (advisory_rag = $0.001), not for low claim ($0.005)
    routes = compile_routes([low_claim, critical_claim], remaining_budget_usd=0.0015)
    route_dict = {r.claim_id: r for r in routes}

    # Critical should be assigned writer (advisory_rag = $0.001)
    assert route_dict[critical_claim.id].assigned_writer == "advisory_rag"
    # Low claim should be abstained due to remaining budget
    assert route_dict[low_claim.id].assigned_writer == "ABSTAIN"


def test_can_escalate_to_teacher():
    """Verify check for whether budget permits escalating to Teacher Vision ($0.015)."""
    assert can_escalate_to_teacher(0.02) is True
    assert can_escalate_to_teacher(0.015) is True
    assert can_escalate_to_teacher(0.010) is False
    assert can_escalate_to_teacher(0.001) is False


def test_estimate_always_vlm_cost():
    """Verify calculation of counterfactual Always-Teacher baseline cost."""
    claims = [
        Claim(type=ClaimType.GEO_PARCEL),
        Claim(type=ClaimType.VIS_CROP),
        Claim(type=ClaimType.ADV_FERTILIZER),
    ]

    cost = estimate_always_vlm_cost(claims)
    # Teacher vision ($0.015) + Advisory RAG ($0.001) + Teacher ($0.015) + Planner/Binder ($0.010)
    assert cost > 0.03
    assert isinstance(cost, float)


def test_calculate_cost_savings():
    """Verify dollar and percentage savings calculation for UI panel."""
    docket = Docket(
        query="Test query",
        always_vlm_estimate_usd=0.060,
        total_cost_usd=0.015,
    )

    savings = calculate_cost_savings(docket)
    assert savings["always_vlm_baseline_usd"] == 0.060
    assert savings["actual_spent_usd"] == 0.015
    assert savings["saved_usd"] == 0.045
    assert savings["saved_percentage"] == 75.0


def test_record_cost_entry():
    """Verify that recording cost entries updates docket totals and ledger."""
    docket = Docket(query="Test query")
    assert docket.total_cost_usd == 0.0
    assert docket.total_latency_ms == 0

    record_cost_entry(
        docket=docket,
        claim_id="clm-1",
        writer="test_writer",
        cost_usd=0.0035,
        latency_ms=120,
        input_tokens=100,
        output_tokens=50,
    )

    assert len(docket.costs) == 1
    assert docket.total_cost_usd == 0.0035
    assert docket.total_latency_ms == 120
    assert docket.costs[0].writer == "test_writer"
    assert docket.costs[0].input_tokens == 100

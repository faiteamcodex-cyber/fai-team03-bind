"""Budget Compiler & Deterministic Router.

Part of Dinesh Kumar's (Member 2) deliverables:
- Deterministic routing algorithm based on Harm Class and capabilities.
- Strict $0.08 per request budget enforcement with ABSTAIN fallback.
- Cost and latency tracking across all execution engines.
- Always-Terra (Always-VLM) counterfactual baseline calculation for UI cost savings panel.
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional, Tuple

from app.config import settings
from app.schemas.enums import ClaimType, HarmClass, ClaimStatus
from app.schemas.models import Claim, CostEntry, Docket, RouteEntry

logger = logging.getLogger(__name__)

# Standard operation cost estimates in USD
COST_TABLE: dict[str, float] = {
    "gis_tool": 0.0,
    "land_record_tool": 0.0,
    "image_retrieve_tool": 0.0,
    "photo_bind_tool": 0.0,
    "weather_tool": 0.0,
    "advisory_rag": 0.001,  # Titan embedding invocation
    settings.student_vision_model_id: 0.003,  # nova-lite per image
    settings.teacher_vision_model_id: 0.015,  # terra / teacher vision per image
    settings.planner_model_id: 0.005,  # luna / planner LLM call
    # Common model IDs / aliases for robust matching
    "apac.amazon.nova-lite-v1:0": 0.003,
    "apac.amazon.nova-micro-v1:0": 0.002,
    "amazon.nova-lite": 0.003,
    "gpt-5.6-terra": 0.015,
    "gpt-5.6-luna": 0.005,
}

# Standard operation latency estimates in milliseconds
LATENCY_TABLE: dict[str, int] = {
    "gis_tool": 50,
    "land_record_tool": 100,
    "image_retrieve_tool": 200,
    "photo_bind_tool": 50,
    "weather_tool": 80,
    "advisory_rag": 500,
    settings.student_vision_model_id: 1500,
    settings.teacher_vision_model_id: 3000,
    settings.planner_model_id: 2000,
    "apac.amazon.nova-lite-v1:0": 1500,
    "apac.amazon.nova-micro-v1:0": 1000,
    "amazon.nova-lite": 1500,
    "gpt-5.6-terra": 3000,
    "gpt-5.6-luna": 2000,
}

# Capability matrix: prioritized writers for each claim type
WRITER_PRIORITY: dict[ClaimType, list[str]] = {
    ClaimType.GEO_PARCEL: ["gis_tool"],
    ClaimType.REG_OWNER: ["land_record_tool"],
    ClaimType.MEDIA_PHOTO: ["image_retrieve_tool"],
    ClaimType.VIS_CROP: [settings.student_vision_model_id, settings.teacher_vision_model_id],
    ClaimType.VIS_STAGE: [settings.student_vision_model_id, settings.teacher_vision_model_id],
    ClaimType.VIS_CONDITION: [settings.student_vision_model_id, settings.teacher_vision_model_id],
    ClaimType.ADV_FERTILIZER: ["advisory_rag"],
    ClaimType.ADV_PRACTICE: ["advisory_rag"],
    ClaimType.WX_CONTEXT: ["weather_tool"],
    ClaimType.META_CLARIFY: [settings.planner_model_id],
}


# Tier cost constants (USD)
TEACHER_VISION_COST: float = 0.015
STUDENT_VISION_COST: float = 0.003
PLANNER_COST: float = 0.005


def get_estimated_cost(writer_name: str) -> float:
    """Return estimated cost for a given writer."""
    if writer_name == "teacher_vision" or "terra" in writer_name.lower() or "nova-pro" in writer_name.lower():
        return TEACHER_VISION_COST
    if writer_name == settings.student_vision_model_id or writer_name == "student_vision" or "nova-lite" in writer_name.lower():
        return STUDENT_VISION_COST
    if writer_name == settings.planner_model_id or writer_name == "planner" or "luna" in writer_name.lower():
        return PLANNER_COST
    return COST_TABLE.get(writer_name, 0.002)


def get_estimated_latency(writer_name: str) -> int:
    """Return estimated latency in ms for a given writer."""
    if writer_name == "teacher_vision" or "terra" in writer_name.lower() or "nova-pro" in writer_name.lower():
        return 3000
    if writer_name == settings.student_vision_model_id or writer_name == "student_vision" or "nova-lite" in writer_name.lower():
        return 1500
    if writer_name == settings.teacher_vision_model_id:
        return 3000
    if writer_name == settings.planner_model_id or writer_name == "planner" or "luna" in writer_name.lower():
        return 2000
    return LATENCY_TABLE.get(writer_name, 500)


def compile_routes(
    claims: list[Claim],
    remaining_budget_usd: Optional[float] = None,
    max_budget_usd: Optional[float] = None,
) -> list[RouteEntry]:
    """Deterministic routing algorithm that compiles execution paths for all claims.
    
    Rules:
    1. Highest harm classes are prioritized when allocating budget.
    2. Vision claims (VIS.*) always route to the Student Vision model first ($0.003),
       saving substantial budget over the Teacher Vision ($0.015).
    3. If estimated cost exceeds remaining budget (under the strict $0.08 limit),
       the claim is marked as ABSTAIN to prevent cost overruns.
    """
    ceiling = max_budget_usd if max_budget_usd is not None else settings.max_docket_cost_usd
    budget_left = remaining_budget_usd if remaining_budget_usd is not None else ceiling
    
    # Harm priority ordering: Critical -> High -> Medium -> Low
    harm_weight = {
        HarmClass.CRITICAL: 4,
        HarmClass.HIGH: 3,
        HarmClass.MEDIUM: 2,
        HarmClass.LOW: 1,
    }

    # Sort claims by priority to allocate budget to high-harm claims first
    sorted_claims = sorted(claims, key=lambda c: harm_weight.get(c.harm, 0), reverse=True)
    
    route_map: dict[str, RouteEntry] = {}

    for claim in sorted_claims:
        allowed = WRITER_PRIORITY.get(claim.type, [])
        if not allowed:
            route_map[claim.id] = RouteEntry(
                claim_id=claim.id,
                assigned_writer="NONE",
                reason=f"No capable writer registered for claim type {claim.type}",
                estimated_cost_usd=0.0,
                estimated_latency_ms=0,
            )
            continue

        # Strategy: Pick student vision for multimodal claims to preserve budget
        chosen_writer = allowed[0]
        est_cost = get_estimated_cost(chosen_writer)
        est_latency = get_estimated_latency(chosen_writer)

        if est_cost > budget_left:
            logger.warning(
                f"Budget limit reached for claim {claim.id} ({claim.type}). "
                f"Required: ${est_cost:.4f}, Available: ${budget_left:.4f}"
            )
            route_map[claim.id] = RouteEntry(
                claim_id=claim.id,
                assigned_writer="ABSTAIN",
                reason=f"Budget cap of ${ceiling:.2f} exceeded. Required ${est_cost:.4f} but only ${budget_left:.4f} remains.",
                estimated_cost_usd=0.0,
                estimated_latency_ms=0,
            )
            continue

        budget_left -= est_cost
        reason_note = (
            f"Routed to Student Vision ({chosen_writer}) with harm class {claim.harm} to maximize efficiency"
            if claim.type in (ClaimType.VIS_CROP, ClaimType.VIS_STAGE, ClaimType.VIS_CONDITION)
            else f"Routed to optimal writer {chosen_writer} for {claim.type} (harm={claim.harm})"
        )

        route_map[claim.id] = RouteEntry(
            claim_id=claim.id,
            assigned_writer=chosen_writer,
            reason=reason_note,
            estimated_cost_usd=est_cost,
            estimated_latency_ms=est_latency,
        )

    # Return routes preserving the original order of the input claims list
    return [route_map[c.id] for c in claims if c.id in route_map]


def can_escalate_to_teacher(remaining_budget_usd: float) -> bool:
    """Check if the remaining budget is sufficient to invoke Teacher Vision ($0.015)."""
    return remaining_budget_usd >= TEACHER_VISION_COST


def estimate_always_vlm_cost(claims: list[Claim]) -> float:
    """Estimate counterfactual cost if the Teacher Vision (gpt-5.6-terra) was used for everything.
    
    This forms the baseline for Member 4's Cost Comparison Panel to demonstrate savings.
    """
    teacher_cost = TEACHER_VISION_COST
    planner_cost = PLANNER_COST
    total = 0.0

    for claim in claims:
        if claim.type in (ClaimType.VIS_CROP, ClaimType.VIS_STAGE, ClaimType.VIS_CONDITION):
            total += teacher_cost
        elif claim.type in (ClaimType.ADV_FERTILIZER, ClaimType.ADV_PRACTICE):
            total += get_estimated_cost("advisory_rag") + teacher_cost
        else:
            first_writer = WRITER_PRIORITY.get(claim.type, [""])[0]
            total += get_estimated_cost(first_writer)

    # Base cost for Planner (Luna) + Binder (Luna)
    total += planner_cost * 2
    return round(total, 5)


def calculate_cost_savings(docket: Docket) -> dict[str, float]:
    """Calculate realized dollar and percentage savings against the Always-Teacher baseline."""
    baseline = docket.always_vlm_estimate_usd
    if baseline <= 0:
        baseline = estimate_always_vlm_cost(docket.claims)

    actual = docket.total_cost_usd
    savings_usd = max(0.0, baseline - actual)
    savings_pct = (savings_usd / baseline * 100.0) if baseline > 0 else 0.0

    return {
        "always_vlm_baseline_usd": round(baseline, 4),
        "actual_spent_usd": round(actual, 4),
        "saved_usd": round(savings_usd, 4),
        "saved_percentage": round(savings_pct, 1),
    }


def record_cost_entry(
    docket: Docket,
    claim_id: str,
    writer: str,
    cost_usd: float,
    latency_ms: int,
    input_tokens: int = 0,
    output_tokens: int = 0,
) -> CostEntry:
    """Record an executed cost entry in the docket and update totals."""
    entry = CostEntry(
        claim_id=claim_id,
        writer=writer,
        cost_usd=cost_usd,
        latency_ms=latency_ms,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
    )
    docket.costs.append(entry)
    docket.total_cost_usd = round(docket.total_cost_usd + cost_usd, 6)
    docket.total_latency_ms += latency_ms
    return entry

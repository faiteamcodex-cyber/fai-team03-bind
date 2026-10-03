"""Budget Compiler: assigns writers to claims based on harm class, cost, and capability."""

from app.schemas.enums import ClaimType, HarmClass
from app.schemas.models import Claim, RouteEntry
from app.config import settings

# Cost estimates per invocation (USD)
COST_TABLE: dict[str, float] = {
    "gis_tool": 0.0,
    "land_record_tool": 0.0,
    "image_retrieve_tool": 0.0,
    "photo_bind_tool": 0.0,
    "advisory_rag": 0.001,  # Titan embedding cost
    settings.student_vision_model_id: 0.003,  # nova-lite per image
    settings.teacher_vision_model_id: 0.015,  # terra per image
    settings.planner_model_id: 0.005,  # luna per call
}

# Latency estimates per invocation (ms)
LATENCY_TABLE: dict[str, int] = {
    "gis_tool": 50,
    "land_record_tool": 100,
    "image_retrieve_tool": 200,
    "photo_bind_tool": 50,
    "advisory_rag": 500,
    settings.student_vision_model_id: 1500,
    settings.teacher_vision_model_id: 3000,
    settings.planner_model_id: 2000,
}

# Capability matrix: which writers are allowed for each claim type
WRITER_MATRIX: dict[ClaimType, list[str]] = {
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


def compile_routes(claims: list[Claim], remaining_budget_usd: float) -> list[RouteEntry]:
    """Assign a writer to each claim based on harm class, budget, and capability."""
    routes: list[RouteEntry] = []
    budget_left = remaining_budget_usd

    for claim in claims:
        allowed_writers = WRITER_MATRIX.get(claim.type, [])
        if not allowed_writers:
            routes.append(RouteEntry(
                claim_id=claim.id,
                assigned_writer="NONE",
                reason=f"No writer available for claim type {claim.type}",
                estimated_cost_usd=0.0,
            ))
            continue

        # For VIS.* claims, always try student first (cheapest)
        if claim.type in (ClaimType.VIS_CROP, ClaimType.VIS_STAGE, ClaimType.VIS_CONDITION):
            chosen = allowed_writers[0]  # Student first
        else:
            chosen = allowed_writers[0]  # Default to first allowed

        est_cost = COST_TABLE.get(chosen, 0.0)
        est_latency = LATENCY_TABLE.get(chosen, 0)

        # Check budget
        if est_cost > budget_left:
            routes.append(RouteEntry(
                claim_id=claim.id,
                assigned_writer="ABSTAIN",
                reason=f"Budget exhausted. Need ${est_cost:.4f} but only ${budget_left:.4f} remains.",
                estimated_cost_usd=0.0,
            ))
            continue

        budget_left -= est_cost

        routes.append(RouteEntry(
            claim_id=claim.id,
            assigned_writer=chosen,
            reason=f"Cheapest capable writer for {claim.type} (harm={claim.harm})",
            estimated_cost_usd=est_cost,
            estimated_latency_ms=est_latency,
        ))

    return routes


def can_escalate_to_teacher(remaining_budget_usd: float) -> bool:
    """Check if budget allows escalation to the teacher vision model."""
    teacher_cost = COST_TABLE.get(settings.teacher_vision_model_id, 0.015)
    return remaining_budget_usd >= teacher_cost


def estimate_always_vlm_cost(claims: list[Claim]) -> float:
    """Estimate what the docket would cost if VLM B was used for everything."""
    total = 0.0
    teacher_cost = COST_TABLE.get(settings.teacher_vision_model_id, 0.015)
    planner_cost = COST_TABLE.get(settings.planner_model_id, 0.005)

    for claim in claims:
        if claim.type in (ClaimType.VIS_CROP, ClaimType.VIS_STAGE, ClaimType.VIS_CONDITION):
            total += teacher_cost
        elif claim.type in (ClaimType.ADV_FERTILIZER, ClaimType.ADV_PRACTICE):
            total += COST_TABLE.get("advisory_rag", 0.001) + planner_cost
        else:
            total += COST_TABLE.get(WRITER_MATRIX.get(claim.type, [""])[0], 0.0)
    
    total += planner_cost * 2  # Planner + Binder
    return total

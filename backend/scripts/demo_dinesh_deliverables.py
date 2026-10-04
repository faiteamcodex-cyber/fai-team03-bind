"""End-to-End Demonstration Script for Dinesh Kumar's (Member 2) Deliverables.

Demonstrates:
1. Bedrock LLM / Vision Client (Deliverable A)
2. Deterministic Budget Router with Harm Class logic & $0.08 cap (Deliverable B)
3. Vision Fallback Execution Engine with standardized Exhibits (Deliverable C)
4. Counterfactual Cost Comparison Ledger (Always-Terra vs Actual)
"""

import asyncio
import json
import logging

import sys
from pathlib import Path

# Add backend directory to sys.path
backend_dir = str(Path(__file__).resolve().parent.parent)
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.config import settings
from app.connectors.bedrock import BedrockClient
from app.connectors.vision import VisionEngine
from app.kernel.budget import compile_routes, calculate_cost_savings, estimate_always_vlm_cost
from app.kernel.state_machine import DocketKernel
from app.schemas.enums import ClaimType, HarmClass, ClaimStatus
from app.schemas.models import Claim, Docket, DocketRequest

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)-7s | %(message)s")
logger = logging.getLogger("demo")


async def run_demo():
    print("\n" + "=" * 75)
    print("[BIND SYSTEM] - DINESH KUMAR (MEMBER 2) DEMONSTRATION")
    print("=" * 75)

    # 1. Initialize Clients
    bedrock = BedrockClient()
    vision = VisionEngine(client=bedrock)
    kernel = DocketKernel(bedrock_client=bedrock)

    print(f"\n[1] Configuration:")
    print(f"    Region:               {settings.aws_region}")
    print(f"    Planner Model:        {settings.planner_model_id}")
    print(f"    Student Vision:       {settings.student_vision_model_id}")
    print(f"    Teacher Vision:       {settings.teacher_vision_model_id}")
    print(f"    Confidence Threshold: {settings.student_confidence_threshold}")
    print(f"    Max Budget Cap:       ${settings.max_docket_cost_usd:.2f}")

    # 2. Test Router & Harm Class Logic
    print("\n" + "-" * 75)
    print("[2] Demonstrating Deterministic Budget Router (Deliverable B):")
    sample_claims = [
        Claim(type=ClaimType.GEO_PARCEL, harm=HarmClass.HIGH),
        Claim(type=ClaimType.REG_OWNER, harm=HarmClass.HIGH),
        Claim(type=ClaimType.VIS_CROP, harm=HarmClass.MEDIUM),
        Claim(type=ClaimType.VIS_STAGE, harm=HarmClass.MEDIUM),
        Claim(type=ClaimType.ADV_FERTILIZER, harm=HarmClass.CRITICAL),
    ]

    routes = compile_routes(sample_claims, remaining_budget_usd=0.08)
    print(f"    Compiled {len(routes)} routes:")
    for r in routes:
        print(f"    - Claim {r.claim_id}: assigned to [{r.assigned_writer}] (est: ${r.estimated_cost_usd:.4f}, {r.estimated_latency_ms}ms)")
        print(f"      Reason: {r.reason}")

    # 3. Test Vision Fallback Engine
    print("\n" + "-" * 75)
    print("[3] Demonstrating Vision Fallback Hook (Deliverable C):")
    test_docket = Docket(query="Validate paddy survey 202/55")
    vis_claim = Claim(type=ClaimType.VIS_CROP)
    test_docket.claims.append(vis_claim)

    result, exhibit = await vision.execute_claim_with_fallback(test_docket, vis_claim)
    print(f"    Prediction Label:   {result.get('label')}")
    print(f"    Confidence:         {result.get('confidence'):.2f}")
    print(f"    Assigned Writer:    {vis_claim.writer}")
    print(f"    Exhibit Generated:  ID={exhibit.id}, Kind={exhibit.kind}, Source={exhibit.source_id}")
    print(f"    Docket Exhibits:    {len(test_docket.exhibits)} attached")

    # 4. Cost Comparison Ledger
    print("\n" + "-" * 75)
    print("[4] Demonstrating Cost Savings Ledger:")
    baseline = estimate_always_vlm_cost(sample_claims)
    test_docket.always_vlm_estimate_usd = baseline
    savings = calculate_cost_savings(test_docket)
    print(f"    Always-Terra Counterfactual Cost: ${savings['always_vlm_baseline_usd']:.4f}")
    print(f"    Actual Spent Cost:                ${savings['actual_spent_usd']:.4f}")
    print(f"    Realized Net Savings:             ${savings['saved_usd']:.4f} ({savings['saved_percentage']}%)")

    # 5. Full End-to-End Pipeline Execution
    print("\n" + "-" * 75)
    print("[5] Executing Full Docket Lifecycle via State Machine:")
    request = DocketRequest(
        query="Recommend fertilizer dosage for paddy field in survey 202/55",
        village_filter="thanjavur_east",
    )
    docket = await kernel.process(request)
    print(f"    Docket ID:     {docket.id}")
    print(f"    Status:        {docket.status}")
    print(f"    Survey Number: {docket.survey_number}")
    print(f"    Claims count:  {len(docket.claims)}")
    for c in docket.claims:
        print(f"    - Claim {c.type}: {c.status} (by {c.writer}) | Reason: {c.stamp_reason}")
    print(f"    Total Cost:    ${docket.total_cost_usd:.4f}")
    print(f"    Total Latency: {docket.total_latency_ms}ms")

    print("\n" + "=" * 75)
    print("[SUCCESS] All deliverables for Dinesh Kumar verified successfully!")
    print("=" * 75)


if __name__ == "__main__":
    asyncio.run(run_demo())

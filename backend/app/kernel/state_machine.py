"""DocketKernel: The core state machine that drives the BIND claim lifecycle."""

import time
import logging
from typing import Optional

from app.schemas.enums import ClaimType, ClaimStatus, DocketStatus
from app.schemas.models import Claim, Docket, DocketRequest, CostEntry
from app.kernel.planner import plan_claims
from app.kernel.binder import verify_docket
from app.kernel.budget import compile_routes, estimate_always_vlm_cost, can_escalate_to_teacher
from app.config import settings

logger = logging.getLogger(__name__)


class DocketKernel:
    """The main orchestrator. Drives a Docket through its lifecycle."""

    def __init__(self, bedrock_client=None, connectors: Optional[dict] = None):
        """
        Args:
            bedrock_client: The AWS Bedrock client wrapper (from Dinesh's code).
            connectors: A dict of connector instances keyed by name:
                - "geography": GIS tool
                - "land_record": Land record connector
                - "image_retrieve": Image retrieval
                - "photo_bind": Photo binding (point-in-polygon)
                - "advisory_store": RAG advisory
                - "student_vision": Student vision model
                - "teacher_vision": Teacher vision model
                - "weather": Weather connector
        """
        self.bedrock_client = bedrock_client
        self.connectors = connectors or {}

    async def process(self, request: DocketRequest) -> Docket:
        """Execute the full docket lifecycle: Parse → Plan → Compile → Bind → Stamp → Close."""
        start_ms = int(time.time() * 1000)

        # ---- 1. PARSE: Create docket and extract entities ----
        docket = self._parse_request(request)
        logger.info(f"Docket {docket.id} created for query: {docket.query[:80]}...")

        # ---- 2. PLAN: Use LLM A to generate claims ----
        docket.status = DocketStatus.PLANNING
        claims = await plan_claims(docket, self.bedrock_client)
        docket.claims = claims
        logger.info(f"Planner opened {len(claims)} claims: {[c.type.value for c in claims]}")

        # ---- 3. COMPILE: Route claims to writers ----
        routes = compile_routes(claims, settings.max_docket_cost_usd)
        docket.routes = routes
        docket.always_vlm_estimate_usd = estimate_always_vlm_cost(claims)
        logger.info(f"Router compiled {len(routes)} routes.")

        # ---- 4. EXECUTE: Run writers for each claim ----
        docket.status = DocketStatus.EXECUTING
        await self._execute_claims(docket)

        # ---- 5. VERIFY: Run the Binder ----
        docket.status = DocketStatus.VERIFYING
        docket = await verify_docket(docket, self.bedrock_client)

        # ---- 6. CLOSE ----
        docket.status = DocketStatus.CLOSED
        docket.closed_ms = int(time.time() * 1000)
        docket.total_latency_ms = docket.closed_ms - start_ms
        docket.total_cost_usd = sum(c.cost_usd for c in docket.costs)

        logger.info(
            f"Docket {docket.id} CLOSED. "
            f"Claims: {len(docket.claims)}, "
            f"Cost: ${docket.total_cost_usd:.4f}, "
            f"Latency: {docket.total_latency_ms}ms"
        )
        return docket

    def _parse_request(self, request: DocketRequest) -> Docket:
        """Parse the incoming request into a Docket with extracted entities."""
        # Simple survey number extraction (deterministic, not LLM)
        survey_number = self._extract_survey_number(request.query)
        village_id = request.village_filter

        return Docket(
            query=request.query,
            village_id=village_id,
            survey_number=survey_number,
            image_provided=request.image_base64 is not None,
        )

    def _extract_survey_number(self, query: str) -> Optional[str]:
        """Extract survey number from query using deterministic rules."""
        import re
        # Match patterns like 202/55, 145/2, 88/1B, 202/55A
        pattern = r'\b(\d{1,4}[/-]\d{1,4}[A-Za-z]?)\b'
        matches = re.findall(pattern, query)
        if matches:
            # Normalize: replace hyphen with slash
            return matches[0].replace('-', '/')
        return None

    async def _execute_claims(self, docket: Docket) -> None:
        """Execute each claim by calling the assigned writer."""
        # Build a map of claim_id -> route
        route_map = {r.claim_id: r for r in docket.routes}

        # Resolve claims in dependency order
        resolved: set[str] = set()
        max_iterations = len(docket.claims) * 2  # Safety bound
        iteration = 0

        while len(resolved) < len(docket.claims) and iteration < max_iterations:
            iteration += 1
            progress = False

            for claim in docket.claims:
                if claim.id in resolved:
                    continue

                # Check dependencies
                deps_met = all(dep_id in resolved for dep_id in claim.depends_on)
                if not deps_met:
                    continue

                route = route_map.get(claim.id)
                if not route or route.assigned_writer in ("NONE", "ABSTAIN"):
                    claim.status = ClaimStatus.ABSTAINED
                    claim.stamp_reason = route.reason if route else "No route assigned."
                    resolved.add(claim.id)
                    progress = True
                    continue

                # Execute the writer
                claim.status = ClaimStatus.BINDING
                await self._run_writer(docket, claim, route)
                resolved.add(claim.id)
                progress = True

            if not progress:
                # Break circular dependencies
                for claim in docket.claims:
                    if claim.id not in resolved:
                        claim.status = ClaimStatus.ABSTAINED
                        claim.stamp_reason = "Dependency deadlock detected."
                        resolved.add(claim.id)
                break

    async def _run_writer(self, docket: Docket, claim: Claim, route) -> None:
        """Dispatch a claim to its assigned writer (connector or model)."""
        writer_name = route.assigned_writer
        start_ms = int(time.time() * 1000)

        try:
            if writer_name == "gis_tool":
                await self._run_gis(docket, claim)
            elif writer_name == "land_record_tool":
                await self._run_land_record(docket, claim)
            elif writer_name == "image_retrieve_tool":
                await self._run_image_retrieve(docket, claim)
            elif writer_name == settings.student_vision_model_id:
                await self._run_student_vision(docket, claim)
            elif writer_name == settings.teacher_vision_model_id:
                await self._run_teacher_vision(docket, claim)
            elif writer_name == "advisory_rag":
                await self._run_advisory_rag(docket, claim)
            else:
                claim.status = ClaimStatus.ABSTAINED
                claim.stamp_reason = f"Unknown writer: {writer_name}"
        except Exception as e:
            logger.error(f"Writer {writer_name} failed for claim {claim.id}: {e}")
            claim.status = ClaimStatus.ABSTAINED
            claim.stamp_reason = f"Writer failed: {str(e)}"
            route.fallback_used = True

        elapsed_ms = int(time.time() * 1000) - start_ms
        docket.costs.append(CostEntry(
            claim_id=claim.id,
            writer=writer_name,
            cost_usd=route.estimated_cost_usd,
            latency_ms=elapsed_ms,
        ))

    # ---- Writer Implementations (delegate to connectors or use mocks) ----

    async def _run_gis(self, docket: Docket, claim: Claim) -> None:
        connector = self.connectors.get("geography")
        if connector:
            exhibit = await connector.resolve_parcel(docket.survey_number, docket.village_id)
        else:
            # Mock
            from app.connectors.geography import mock_resolve_parcel
            exhibit = await mock_resolve_parcel(docket.survey_number, docket.village_id)
        
        claim.writer = "gis_tool"
        if exhibit:
            docket.add_exhibit(exhibit)
            claim.exhibit_ids.append(exhibit.id)
            claim.value = {"survey_number": docket.survey_number, "village": docket.village_id}
            claim.confidence = 1.0

    async def _run_land_record(self, docket: Docket, claim: Claim) -> None:
        connector = self.connectors.get("land_record")
        if connector:
            exhibit = await connector.get_owner(docket.survey_number)
        else:
            from app.connectors.land_record import mock_get_owner
            exhibit = await mock_get_owner(docket.survey_number)

        claim.writer = "land_record_tool"
        if exhibit:
            docket.add_exhibit(exhibit)
            claim.exhibit_ids.append(exhibit.id)
            claim.value = exhibit.payload
            claim.confidence = 1.0

    async def _run_image_retrieve(self, docket: Docket, claim: Claim) -> None:
        connector = self.connectors.get("image_retrieve")
        if connector:
            exhibit = await connector.get_photo(docket.survey_number)
        else:
            from app.connectors.geography import mock_retrieve_photo
            exhibit = await mock_retrieve_photo(docket.survey_number, docket.village_id)

        claim.writer = "image_retrieve_tool"
        if exhibit:
            docket.add_exhibit(exhibit)
            claim.exhibit_ids.append(exhibit.id)
            claim.value = {"image_id": exhibit.id, "bind_status": exhibit.payload.get("bind_status", "unbound")}
            claim.confidence = 1.0

    async def _run_student_vision(self, docket: Docket, claim: Claim) -> None:
        connector = self.connectors.get("student_vision")
        if connector:
            result = await connector.predict(docket, claim)
            claim.writer = settings.student_vision_model_id
            claim.value = result
            claim.confidence = result.get("confidence", 0.0)
            from app.connectors.vision import vision_engine
            exhibit = vision_engine.create_prediction_exhibit(result, settings.student_vision_model_id)
            docket.add_exhibit(exhibit)
            claim.exhibit_ids.append(exhibit.id)
            if claim.confidence < settings.student_confidence_threshold:
                logger.info(f"Student confidence {claim.confidence:.2f} < {settings.student_confidence_threshold}. Escalating to teacher.")
                remaining = docket.remaining_budget_usd(settings.max_docket_cost_usd)
                if can_escalate_to_teacher(remaining):
                    await self._run_teacher_vision(docket, claim)
                else:
                    claim.stamp_reason = "Low confidence but budget exhausted for teacher escalation."
        else:
            from app.connectors.vision import vision_engine
            image_bytes = getattr(docket, "_raw_image_bytes", None)
            await vision_engine.execute_claim_with_fallback(docket, claim, image_bytes)

    async def _run_teacher_vision(self, docket: Docket, claim: Claim) -> None:
        connector = self.connectors.get("teacher_vision")
        if connector:
            result = await connector.predict(docket, claim)
        else:
            from app.connectors.vision import vision_engine
            result = await vision_engine.predict_teacher(claim.type)

        from app.connectors.vision import vision_engine
        teacher_exhibit = vision_engine.create_prediction_exhibit(result, settings.teacher_vision_model_id)
        docket.add_exhibit(teacher_exhibit)
        claim.exhibit_ids.append(teacher_exhibit.id)

        # Check for dispute
        student_label = claim.value.get("label") if claim.value else None
        teacher_label = result.get("label")

        if student_label and teacher_label and student_label != teacher_label:
            claim.value = {
                "dispute": True,
                "student_label": student_label,
                "teacher_label": teacher_label,
                "student_confidence": claim.confidence,
                "teacher_confidence": result.get("confidence", 0.0),
            }
            claim.confidence = 0.0  # Disputed
        else:
            claim.value = result
            claim.confidence = result.get("confidence", 0.0)

        claim.writer = f"{settings.student_vision_model_id} → {settings.teacher_vision_model_id}"
        # Update route to show fallback
        for route in docket.routes:
            if route.claim_id == claim.id:
                route.fallback_used = True
                route.fallback_from = settings.student_vision_model_id
                break

    async def _run_advisory_rag(self, docket: Docket, claim: Claim) -> None:
        # Get the crop from VIS.CROP
        crop_label = None
        stage_label = None
        for c in docket.claims:
            if c.type == ClaimType.VIS_CROP and c.value:
                crop_label = c.value.get("label")
            if c.type == ClaimType.VIS_STAGE and c.value:
                stage_label = c.value.get("label")

        connector = self.connectors.get("advisory_store")
        if connector:
            exhibit = await connector.query(crop_label, stage_label)
        else:
            from app.connectors.advisory_store import mock_query_advisory
            exhibit = await mock_query_advisory(crop_label, stage_label)

        claim.writer = "advisory_rag"
        if exhibit:
            docket.add_exhibit(exhibit)
            claim.exhibit_ids.append(exhibit.id)
            claim.value = exhibit.payload
            claim.confidence = 0.9

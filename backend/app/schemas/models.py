from __future__ import annotations

import uuid
import time
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator

from app.schemas.enums import (
    ClaimType,
    HarmClass,
    ClaimStatus,
    ExhibitKind,
    DocketStatus,
)


# ---------- Claim Catalog (harm defaults) ----------
CLAIM_HARM_MAP: dict[ClaimType, HarmClass] = {
    ClaimType.GEO_PARCEL: HarmClass.HIGH,
    ClaimType.REG_OWNER: HarmClass.HIGH,
    ClaimType.MEDIA_PHOTO: HarmClass.HIGH,
    ClaimType.VIS_CROP: HarmClass.MEDIUM,
    ClaimType.VIS_STAGE: HarmClass.MEDIUM,
    ClaimType.VIS_CONDITION: HarmClass.MEDIUM,
    ClaimType.ADV_FERTILIZER: HarmClass.CRITICAL,
    ClaimType.ADV_PRACTICE: HarmClass.HIGH,
    ClaimType.WX_CONTEXT: HarmClass.LOW,
    ClaimType.META_CLARIFY: HarmClass.LOW,
}


# ---------- Core Models ----------
class Exhibit(BaseModel):
    """A piece of evidence attached to a claim."""
    id: str = Field(default_factory=lambda: f"exh-{uuid.uuid4().hex[:8]}")
    kind: ExhibitKind
    source_id: str = ""  # Resolvable reference (e.g., registry row ID, S3 URI)
    payload: dict[str, Any] = Field(default_factory=dict)
    created_ms: int = Field(default_factory=lambda: int(time.time() * 1000))


class Claim(BaseModel):
    """A single claim within a docket."""
    id: str = Field(default_factory=lambda: f"clm-{uuid.uuid4().hex[:8]}")
    type: ClaimType
    harm: HarmClass = HarmClass.MEDIUM
    status: ClaimStatus = ClaimStatus.OPEN
    value: Optional[dict[str, Any]] = None  # The resolved value (crop name, owner, etc.)
    confidence: Optional[float] = None
    writer: Optional[str] = None  # Which model/tool wrote this
    exhibit_ids: list[str] = Field(default_factory=list)
    stamp_reason: Optional[str] = None
    depends_on: list[str] = Field(default_factory=list)  # Claim IDs this depends on

    def set_harm_from_catalog(self) -> None:
        """Set harm class from the default catalog."""
        self.harm = CLAIM_HARM_MAP.get(self.type, HarmClass.MEDIUM)


class RouteEntry(BaseModel):
    """A routing decision logged in the ledger."""
    claim_id: str
    assigned_writer: str
    reason: str
    estimated_cost_usd: float = 0.0
    estimated_latency_ms: int = 0
    fallback_used: bool = False
    fallback_from: Optional[str] = None


class CostEntry(BaseModel):
    """Actual cost tracking for a single operation."""
    claim_id: str
    writer: str
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    latency_ms: int = 0


class AdvisoryForm(BaseModel):
    """Structured fertilizer/practice advisory. Extra keys are forbidden."""
    crop: str
    stage: str
    product: Optional[str] = None
    dose: Optional[str] = None
    unit: Optional[str] = None
    timing: Optional[str] = None
    source_id: str = ""  # Citation to advisory circular
    page: Optional[str] = None

    model_config = {"extra": "forbid"}


class Docket(BaseModel):
    """The top-level docket that drives the entire BIND lifecycle."""
    id: str = Field(default_factory=lambda: f"dkt-{uuid.uuid4().hex[:8]}")
    query: str
    village_id: Optional[str] = None
    survey_number: Optional[str] = None
    image_provided: bool = False
    status: DocketStatus = DocketStatus.PLANNING

    claims: list[Claim] = Field(default_factory=list)
    exhibits: list[Exhibit] = Field(default_factory=list)
    routes: list[RouteEntry] = Field(default_factory=list)
    costs: list[CostEntry] = Field(default_factory=list)

    total_cost_usd: float = 0.0
    total_latency_ms: int = 0
    always_vlm_estimate_usd: float = 0.0  # What it would cost with VLM B for everything

    created_ms: int = Field(default_factory=lambda: int(time.time() * 1000))
    closed_ms: Optional[int] = None

    def get_claim(self, claim_id: str) -> Optional[Claim]:
        """Get a claim by its ID."""
        for c in self.claims:
            if c.id == claim_id:
                return c
        return None

    def get_claims_by_type(self, claim_type: ClaimType) -> list[Claim]:
        """Get all claims of a given type."""
        return [c for c in self.claims if c.type == claim_type]

    def add_exhibit(self, exhibit: Exhibit) -> None:
        """Add an exhibit to the docket."""
        self.exhibits.append(exhibit)

    def get_exhibit(self, exhibit_id: str) -> Optional[Exhibit]:
        """Get an exhibit by its ID."""
        for e in self.exhibits:
            if e.id == exhibit_id:
                return e
        return None

    def remaining_budget_usd(self, max_budget: float) -> float:
        """Calculate remaining budget."""
        return max(0.0, max_budget - self.total_cost_usd)


# ---------- API Request / Response ----------
class DocketRequest(BaseModel):
    """Incoming request to open a new docket."""
    query: str = Field(..., min_length=5, description="The user's natural language request")
    village_filter: Optional[str] = None
    image_base64: Optional[str] = None  # Optional attached photo


class DocketResponse(BaseModel):
    """The full docket returned to the client."""
    docket: Docket
    summary: Optional[str] = None  # Officer-facing one-paragraph note

"""FastAPI route definitions for the BIND Docket API."""

import logging
from fastapi import APIRouter, HTTPException

from app.schemas.models import DocketRequest, DocketResponse, Docket
from app.kernel.state_machine import DocketKernel
from app.connectors.bedrock import BedrockClient

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["docket"])

# In-memory docket storage (for demo; replace with DynamoDB in production)
_docket_store: dict[str, Docket] = {}

# Singleton kernel and connector instances
from app.connectors.geography import GeographyConnector
from app.connectors.land_record import LandRecordConnector
from app.connectors.advisory_store import AdvisoryStoreConnector

_bedrock_client = BedrockClient()
_connectors = {
    "geography": GeographyConnector(),
    "land_record": LandRecordConnector(),
    "advisory_store": AdvisoryStoreConnector(),
}
_kernel = DocketKernel(bedrock_client=_bedrock_client, connectors=_connectors)


@router.post("/docket", response_model=DocketResponse)
async def open_docket(request: DocketRequest):
    """Open a new docket and process the user's request through the BIND kernel."""
    try:
        logger.info(f"Opening docket for query: {request.query[:100]}")
        docket = await _kernel.process(request)
        _docket_store[docket.id] = docket

        # Generate summary
        stamped = [c for c in docket.claims if c.status.value == "STAMPED"]
        abstained = [c for c in docket.claims if c.status.value == "ABSTAINED"]
        rejected = [c for c in docket.claims if c.status.value == "REJECTED"]

        summary = (
            f"Docket {docket.id} closed with {len(stamped)} stamped, "
            f"{len(abstained)} abstained, {len(rejected)} rejected claims. "
            f"Total cost: ${docket.total_cost_usd:.4f} "
            f"(vs ${docket.always_vlm_estimate_usd:.4f} always-VLM estimate)."
        )

        return DocketResponse(docket=docket, summary=summary)
    except Exception as e:
        logger.error(f"Docket processing failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Docket processing failed: {str(e)}")


@router.get("/docket/{docket_id}", response_model=DocketResponse)
async def get_docket(docket_id: str):
    """Retrieve a previously processed docket."""
    docket = _docket_store.get(docket_id)
    if not docket:
        raise HTTPException(status_code=404, detail=f"Docket {docket_id} not found.")
    return DocketResponse(docket=docket, summary=None)


@router.get("/dockets", response_model=list[dict])
async def list_dockets():
    """List all dockets (for demo purposes)."""
    return [
        {
            "id": d.id,
            "query": d.query[:80],
            "status": d.status.value,
            "claims_count": len(d.claims),
            "cost_usd": d.total_cost_usd,
        }
        for d in _docket_store.values()
    ]


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "bind-kernel", "team": "fai-tce-team03"}

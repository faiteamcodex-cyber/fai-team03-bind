"""Advisory Store (RAG). Harsith will replace with ChromaDB + Titan Embeddings."""

import logging
from typing import Optional

from app.schemas.enums import ExhibitKind
from app.schemas.models import Exhibit

logger = logging.getLogger(__name__)

# Mock advisory circulars
MOCK_ADVISORIES = {
    "paddy": {
        "panicle_initiation": {
            "crop": "paddy",
            "stage": "panicle_initiation",
            "product": "Urea + MOP",
            "dose": "35 kg/acre Urea + 20 kg/acre MOP",
            "unit": "kg/acre",
            "timing": "Apply at panicle initiation stage, before irrigation",
            "source_id": "TNAU-Circular-2026-Paddy-Kharif-003",
            "page": "Page 12, Section 4.2",
        },
        "tillering": {
            "crop": "paddy",
            "stage": "tillering",
            "product": "DAP + Zinc Sulphate",
            "dose": "25 kg/acre DAP + 5 kg/acre ZnSO4",
            "unit": "kg/acre",
            "timing": "Apply 21 days after transplanting",
            "source_id": "TNAU-Circular-2026-Paddy-Kharif-002",
            "page": "Page 8, Section 3.1",
        },
        "flowering": {
            "crop": "paddy",
            "stage": "flowering",
            "product": "Potash (KCl)",
            "dose": "15 kg/acre",
            "unit": "kg/acre",
            "timing": "Apply at 50% flowering",
            "source_id": "TNAU-Circular-2026-Paddy-Kharif-004",
            "page": "Page 15, Section 5.1",
        },
    },
    "sugarcane": {
        "panicle_initiation": {
            "crop": "sugarcane",
            "stage": "grand_growth",
            "product": "Urea",
            "dose": "65 kg/acre",
            "unit": "kg/acre",
            "timing": "Apply at grand growth phase with irrigation",
            "source_id": "TNAU-Circular-2026-Sugarcane-001",
            "page": "Page 6, Section 2.3",
        },
    },
}


async def mock_query_advisory(crop: Optional[str], stage: Optional[str]) -> Optional[Exhibit]:
    """Mock RAG query. Harsith will replace with real vector search."""
    if not crop:
        logger.warning("AdvisoryStore: No crop specified, cannot query.")
        return None

    crop_lower = crop.lower()
    stage_lower = (stage or "").lower()

    crop_advisories = MOCK_ADVISORIES.get(crop_lower)
    if not crop_advisories:
        logger.warning(f"AdvisoryStore: No advisories found for crop '{crop}'.")
        return None

    advisory = crop_advisories.get(stage_lower)
    if not advisory:
        # Try to find any advisory for the crop
        first_key = next(iter(crop_advisories), None)
        if first_key:
            advisory = crop_advisories[first_key]
            logger.info(f"AdvisoryStore: Exact stage not found, using '{first_key}' advisory.")
        else:
            return None

    logger.info(f"AdvisoryStore: Found advisory for {crop}/{stage}: {advisory['product']}")
    return Exhibit(
        kind=ExhibitKind.FORM,
        source_id=advisory["source_id"],
        payload=advisory,
    )

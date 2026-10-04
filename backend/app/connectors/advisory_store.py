import os
import sys
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List

_src_path = str(Path(__file__).resolve().parent.parent.parent / "src")
if _src_path not in sys.path:
    sys.path.insert(0, _src_path)

from app.schemas.enums import ExhibitKind
from app.schemas.models import Exhibit
from bind_data.rag.chroma_index import query_advisories as _query_chroma, ChromaAdvisoryStore
from bind_data.rag.titan_embeddings import EmbeddingProvider

logger = logging.getLogger(__name__)

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
        "grand_growth": {
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


class AdvisoryStoreConnector:
    """RAG Advisory Store Connector querying persistent ChromaDB vector store."""

    def __init__(
        self,
        persist_dir: str = "./artifacts/chroma",
        collection_name: str = "advisory_store",
        embedding_provider: Optional[EmbeddingProvider] = None,
    ):
        self.persist_dir = persist_dir
        self.collection_name = collection_name
        self.embedding_provider = embedding_provider

    async def query(
        self,
        crop: Optional[str],
        stage: Optional[str],
        zone: Optional[str] = None,
        query_text: str = "recommended fertilizer dosage and agronomic practices"
    ) -> Optional[Exhibit]:
        if not crop:
            logger.warning("AdvisoryStore: No crop specified, cannot query.")
            return None

        # 1. If Chroma persist dir exists and has data, query ChromaDB
        if os.path.exists(self.persist_dir):
            try:
                results = _query_chroma(
                    query_text=query_text,
                    crop=crop,
                    growth_stage=stage or "unknown",
                    zone=zone,
                    persist_dir=self.persist_dir,
                    collection_name=self.collection_name,
                    embedding_provider=self.embedding_provider,
                    top_k=1,
                )
                if results:
                    top_match = results[0]
                    return Exhibit(
                        kind=ExhibitKind.CHUNK,
                        source_id=top_match.get("source", "chroma-advisory"),
                        payload=top_match,
                    )
            except Exception as e:
                logger.warning(f"ChromaDB query failed: {e}. Falling back to mock advisories.")

        # 2. Fallback to mock dictionary
        return await mock_query_advisory(crop, stage)


async def mock_query_advisory(crop: Optional[str], stage: Optional[str]) -> Optional[Exhibit]:
    """Mock RAG query fallback."""
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


def query_advisories(
    query_text: str,
    crop: str,
    growth_stage: str,
    zone: Optional[str] = None,
    top_k: int = 5
) -> List[Dict[str, Any]]:
    """Public helper function for Member 1 / Member 2."""
    return _query_chroma(query_text=query_text, crop=crop, growth_stage=growth_stage, zone=zone, top_k=top_k)

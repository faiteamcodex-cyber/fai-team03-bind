"""Vision model connectors. Dinesh will replace with real Bedrock vision calls."""

import logging
import random
from typing import Optional

from app.schemas.enums import ClaimType

logger = logging.getLogger(__name__)

# Mock crop taxonomy
MOCK_CROPS = ["paddy", "sugarcane", "groundnut", "cotton", "maize"]
MOCK_STAGES = ["seedling", "tillering", "panicle_initiation", "flowering", "grain_filling", "maturity"]
MOCK_CONDITIONS = ["healthy", "nitrogen_deficiency", "blast", "brown_spot", "stem_borer"]


async def mock_student_predict(claim_type: ClaimType) -> dict:
    """Mock Student Vision (amazon.nova-lite) prediction."""
    if claim_type == ClaimType.VIS_CROP:
        # Default mock: paddy with decent confidence
        return {
            "label": "paddy",
            "confidence": 0.72,
            "model": "amazon.nova-lite",
            "taxonomy": MOCK_CROPS,
        }
    elif claim_type == ClaimType.VIS_STAGE:
        return {
            "label": "panicle_initiation",
            "confidence": 0.68,
            "model": "amazon.nova-lite",
            "taxonomy": MOCK_STAGES,
        }
    elif claim_type == ClaimType.VIS_CONDITION:
        return {
            "label": "healthy",
            "confidence": 0.81,
            "model": "amazon.nova-lite",
            "taxonomy": MOCK_CONDITIONS,
        }
    return {"label": "unknown", "confidence": 0.0, "model": "amazon.nova-lite"}


async def mock_teacher_predict(claim_type: ClaimType) -> dict:
    """Mock Teacher Vision (gpt-5.6-terra) prediction."""
    if claim_type == ClaimType.VIS_CROP:
        return {
            "label": "paddy",
            "confidence": 0.94,
            "model": "gpt-5.6-terra",
        }
    elif claim_type == ClaimType.VIS_STAGE:
        return {
            "label": "panicle_initiation",
            "confidence": 0.91,
            "model": "gpt-5.6-terra",
        }
    elif claim_type == ClaimType.VIS_CONDITION:
        return {
            "label": "healthy",
            "confidence": 0.95,
            "model": "gpt-5.6-terra",
        }
    return {"label": "unknown", "confidence": 0.0, "model": "gpt-5.6-terra"}

"""Land Record connector. Harsith will replace mocks with DynamoDB/SQLite."""

import logging
from typing import Optional

from app.schemas.enums import ExhibitKind
from app.schemas.models import Exhibit

logger = logging.getLogger(__name__)

# Mock land registry data
MOCK_REGISTRY = {
    "202/55": {
        "survey_key": "202/55",
        "owner_name": "Ramasamy S.",
        "extent_acres": 2.5,
        "mutation_date": "2019-03-14",
        "registry_source": "TN-DLRS-Thanjavur-2024",
        "patta_number": "P-4521",
    },
    "202/54": {
        "survey_key": "202/54",
        "owner_name": "Lakshmi K.",
        "extent_acres": 3.1,
        "mutation_date": "2020-07-22",
        "registry_source": "TN-DLRS-Thanjavur-2024",
        "patta_number": "P-4520",
    },
    "145/2": {
        "survey_key": "145/2",
        "owner_name": "Murugan V.",
        "extent_acres": 1.8,
        "mutation_date": "2021-01-05",
        "registry_source": "TN-DLRS-Thanjavur-2024",
        "patta_number": "P-6012",
    },
    "88/1B": {
        "survey_key": "88/1B",
        "owner_name": "Selvaraj P.",
        "extent_acres": 4.2,
        "mutation_date": "2018-11-30",
        "registry_source": "TN-DLRS-Thanjavur-2023",
        "patta_number": "P-3301",
    },
}


async def mock_get_owner(survey_number: Optional[str]) -> Optional[Exhibit]:
    """Mock land record lookup. Harsith will replace with real DB queries."""
    if not survey_number:
        return None

    normalized = survey_number.replace("-", "/").strip()
    record = MOCK_REGISTRY.get(normalized)

    if record:
        logger.info(f"LandRecord: Found owner '{record['owner_name']}' for {normalized}.")
        return Exhibit(
            kind=ExhibitKind.REGISTRY_ROW,
            source_id=record["registry_source"],
            payload=record,
        )
    else:
        logger.warning(f"LandRecord: Survey number {normalized} not found in registry.")
        return None

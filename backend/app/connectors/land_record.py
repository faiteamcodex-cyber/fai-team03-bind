"""Land Record connector integrating DynamoDB and mock registry."""

import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any

from app.schemas.enums import ExhibitKind
from app.schemas.models import Exhibit
from app.config import settings

logger = logging.getLogger(__name__)

MOCK_REGISTRY = {
    "202/55": {
        "survey_key": "202/55",
        "owner_name": "Ramasamy S.",
        "owner_id": "OWN-TN-2024-0981",
        "extent_acres": 2.5,
        "village": "Kadambur",
        "taluk": "Orathanadu",
        "district": "Thanjavur",
        "mutation_date": "2019-03-14",
        "registry_source": "TN-DLRS-Thanjavur-2024",
        "patta_number": "P-4521",
    },
    "202/54": {
        "survey_key": "202/54",
        "owner_name": "Lakshmi K.",
        "owner_id": "OWN-TN-2024-0982",
        "extent_acres": 3.1,
        "village": "Kadambur",
        "taluk": "Orathanadu",
        "district": "Thanjavur",
        "mutation_date": "2020-07-22",
        "registry_source": "TN-DLRS-Thanjavur-2024",
        "patta_number": "P-4520",
    },
    "145/2": {
        "survey_key": "145/2",
        "owner_name": "Murugan V.",
        "owner_id": "OWN-TN-2024-0983",
        "extent_acres": 1.8,
        "village": "Kadambur",
        "taluk": "Orathanadu",
        "district": "Thanjavur",
        "mutation_date": "2021-01-05",
        "registry_source": "TN-DLRS-Thanjavur-2024",
        "patta_number": "P-6012",
    },
    "88/1B": {
        "survey_key": "88/1B",
        "owner_name": "Selvaraj P.",
        "owner_id": "OWN-TN-2023-0451",
        "extent_acres": 4.2,
        "village": "Kadambur",
        "taluk": "Orathanadu",
        "district": "Thanjavur",
        "mutation_date": "2018-11-30",
        "registry_source": "TN-DLRS-Thanjavur-2023",
        "patta_number": "P-3301",
    },
}


class LandRecordConnector:
    """Land record connector checking DynamoDB when live, or fallback mock registry."""

    def __init__(self, table_name: str = "fai-tce-team03-land-records", dynamodb_resource: Any = None):
        self.table_name = table_name
        self._dynamodb_resource = dynamodb_resource

    async def get_owner(self, survey_number: Optional[str]) -> Optional[Exhibit]:
        if not survey_number:
            return None

        normalized = survey_number.replace("-", "/").strip()

        # 1. If not mock mode and DynamoDB configured, query DynamoDB
        if not settings.use_mocks and self._dynamodb_resource is not None:
            try:
                table = self._dynamodb_resource.Table(self.table_name)
                response = table.get_item(Key={"survey_number": normalized})
                item = response.get("Item")
                if item:
                    logger.info(f"LandRecord: Found item in DynamoDB for {normalized}: {item.get('owner_name')}")
                    return Exhibit(
                        kind=ExhibitKind.REGISTRY_ROW,
                        source_id=item.get("registry_source", f"dynamodb-{self.table_name}"),
                        payload=item,
                    )
            except Exception as e:
                logger.warning(f"Failed querying DynamoDB table '{self.table_name}': {e}. Falling back to mock registry.")

        # 2. Fallback to mock dictionary
        record = MOCK_REGISTRY.get(normalized)
        if record:
            logger.info(f"LandRecord: Found owner '{record['owner_name']}' for {normalized} in mock registry.")
            return Exhibit(
                kind=ExhibitKind.REGISTRY_ROW,
                source_id=record.get("registry_source", "TN-DLRS-Thanjavur-2024"),
                payload=record,
            )

        logger.warning(f"LandRecord: Survey number {normalized} not found.")
        return None


async def mock_get_owner(survey_number: Optional[str]) -> Optional[Exhibit]:
    """Mock land record lookup fallback."""
    connector = LandRecordConnector()
    return await connector.get_owner(survey_number)

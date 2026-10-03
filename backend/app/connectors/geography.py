"""GIS connector using GeoPandas and Shapely. Harsith will replace mocks with real data."""

import logging
from typing import Optional

from app.schemas.enums import ExhibitKind
from app.schemas.models import Exhibit

logger = logging.getLogger(__name__)

# Mock cadastral data for the Kadambur test village
MOCK_PARCELS = {
    "202/55": {
        "type": "Feature",
        "properties": {
            "survey_number": "202/55",
            "village": "Kadambur",
            "taluk": "Orathanadu",
            "district": "Thanjavur",
            "extent_acres": 2.5,
        },
        "geometry": {
            "type": "Polygon",
            "coordinates": [[
                [79.3245, 10.7890],
                [79.3255, 10.7890],
                [79.3255, 10.7900],
                [79.3245, 10.7900],
                [79.3245, 10.7890],
            ]]
        }
    },
    "202/54": {
        "type": "Feature",
        "properties": {
            "survey_number": "202/54",
            "village": "Kadambur",
            "taluk": "Orathanadu",
            "district": "Thanjavur",
            "extent_acres": 3.1,
        },
        "geometry": {
            "type": "Polygon",
            "coordinates": [[
                [79.3235, 10.7890],
                [79.3245, 10.7890],
                [79.3245, 10.7900],
                [79.3235, 10.7900],
                [79.3235, 10.7890],
            ]]
        }
    },
    "145/2": {
        "type": "Feature",
        "properties": {
            "survey_number": "145/2",
            "village": "Kadambur",
            "taluk": "Orathanadu",
            "district": "Thanjavur",
            "extent_acres": 1.8,
        },
        "geometry": {
            "type": "Polygon",
            "coordinates": [[
                [79.3260, 10.7910],
                [79.3270, 10.7910],
                [79.3270, 10.7920],
                [79.3260, 10.7920],
                [79.3260, 10.7910],
            ]]
        }
    },
    "88/1B": {
        "type": "Feature",
        "properties": {
            "survey_number": "88/1B",
            "village": "Kadambur",
            "taluk": "Orathanadu",
            "district": "Thanjavur",
            "extent_acres": 4.2,
        },
        "geometry": {
            "type": "Polygon",
            "coordinates": [[
                [79.3280, 10.7870],
                [79.3295, 10.7870],
                [79.3295, 10.7885],
                [79.3280, 10.7885],
                [79.3280, 10.7870],
            ]]
        }
    },
}


async def mock_resolve_parcel(survey_number: Optional[str], village_id: Optional[str]) -> Optional[Exhibit]:
    """Mock GIS resolution. Harsith will replace with GeoPandas logic."""
    if not survey_number:
        return None

    # Normalize survey number
    normalized = survey_number.replace("-", "/").strip()
    parcel = MOCK_PARCELS.get(normalized)

    if parcel:
        logger.info(f"GIS: Resolved parcel {normalized} in Kadambur.")
        return Exhibit(
            kind=ExhibitKind.GEOMETRY,
            source_id=f"cadastral-kadambur-{normalized}",
            payload=parcel,
        )
    else:
        logger.warning(f"GIS: Survey number {normalized} not found.")
        return None


async def mock_retrieve_photo(survey_number: Optional[str], village_id: Optional[str]) -> Optional[Exhibit]:
    """Mock image retrieval with bind status."""
    if not survey_number:
        return None

    normalized = survey_number.replace("-", "/").strip()

    # Mock: 202/55 has a bound photo, 202/54 has an unbound photo
    mock_photos = {
        "202/55": {
            "image_uri": "s3://fai-tce-team03-datasets/images/202_55_field.jpg",
            "capture_time": "2026-09-15T10:30:00Z",
            "gps_lat": 10.7895,
            "gps_lon": 79.3250,
            "bind_status": "inside",  # GPS inside the polygon
            "parcel_id": "202/55",
        },
        "145/2": {
            "image_uri": "s3://fai-tce-team03-datasets/images/145_2_field.jpg",
            "capture_time": "2026-09-16T14:00:00Z",
            "gps_lat": 10.7915,
            "gps_lon": 79.3265,
            "bind_status": "inside",
            "parcel_id": "145/2",
        },
        "88/1B": {
            "image_uri": "s3://fai-tce-team03-datasets/images/88_1B_field.jpg",
            "capture_time": "2026-09-17T09:15:00Z",
            "gps_lat": 10.7877,
            "gps_lon": 79.3287,
            "bind_status": "inside",
            "parcel_id": "88/1B",
        },
        "202/54": {
            "image_uri": "s3://fai-tce-team03-datasets/images/202_54_field.jpg",
            "capture_time": "2026-09-15T11:00:00Z",
            "gps_lat": 10.7950,  # Intentionally outside 202/55 polygon
            "gps_lon": 79.3300,
            "bind_status": "unbound",  # PLANTED FAULT
            "parcel_id": "202/54",
        },
    }

    photo = mock_photos.get(normalized)
    if photo:
        return Exhibit(
            kind=ExhibitKind.IMAGE,
            source_id=f"photo-{normalized}",
            payload=photo,
        )
    return None

import os
import sys
import logging
from pathlib import Path
from typing import Optional, Dict, Any

_src_path = str(Path(__file__).resolve().parent.parent.parent / "src")
if _src_path not in sys.path:
    sys.path.insert(0, _src_path)

from app.schemas.enums import ExhibitKind
from app.schemas.models import Exhibit
from bind_data.gis.survey_lookup import find_parcel_by_survey_number as _find_parcel
from bind_data.gis.spatial_checks import check_point_in_parcel as _check_point
from bind_data.gis.geojson_loader import load_geojson

logger = logging.getLogger(__name__)

# Sample cadastral data for Kadambur test village
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

MOCK_PHOTOS = {
    "202/55": {
        "image_uri": "s3://fai-tce-team03-datasets/raw/crop-images/202_55_field.jpg",
        "capture_time": "2026-09-15T10:30:00Z",
        "gps_lat": 10.7895,
        "gps_lon": 79.3250,
        "bind_status": "inside",
        "parcel_id": "202/55",
    },
    "145/2": {
        "image_uri": "s3://fai-tce-team03-datasets/raw/crop-images/145_2_field.jpg",
        "capture_time": "2026-09-16T14:00:00Z",
        "gps_lat": 10.7915,
        "gps_lon": 79.3265,
        "bind_status": "inside",
        "parcel_id": "145/2",
    },
    "88/1B": {
        "image_uri": "s3://fai-tce-team03-datasets/raw/crop-images/88_1B_field.jpg",
        "capture_time": "2026-09-17T09:15:00Z",
        "gps_lat": 10.7877,
        "gps_lon": 79.3287,
        "bind_status": "inside",
        "parcel_id": "88/1B",
    },
    "202/54": {
        "image_uri": "s3://fai-tce-team03-datasets/raw/crop-images/202_54_field.jpg",
        "capture_time": "2026-09-15T11:00:00Z",
        "gps_lat": 10.7950,
        "gps_lon": 79.3300,
        "bind_status": "unbound",
        "parcel_id": "202/54",
    },
}


class GeographyConnector:
    """GIS Connector backed by bind_data.gis and GeoPandas/Shapely."""

    def __init__(self, geojson_source: Optional[str] = None):
        self.geojson_source = geojson_source

    async def resolve_parcel(self, survey_number: Optional[str], village_id: Optional[str] = None) -> Optional[Exhibit]:
        """Resolve parcel from GeoJSON dataset or fallback mock data."""
        if not survey_number:
            return None

        normalized = survey_number.replace("-", "/").strip()

        # 1. Try local fixture or configured GeoJSON source if present
        if self.geojson_source and os.path.exists(self.geojson_source):
            try:
                res = _find_parcel(normalized, self.geojson_source)
                if res.get("found"):
                    logger.info(f"GIS: Resolved parcel {normalized} from {self.geojson_source}")
                    return Exhibit(
                        kind=ExhibitKind.GEOMETRY,
                        source_id=f"cadastral-{normalized}",
                        payload=res["parcel"],
                    )
            except Exception as e:
                logger.warning(f"Error querying GeoJSON source: {e}")

        # 2. Fallback to mock dictionary
        parcel = MOCK_PARCELS.get(normalized)
        if parcel:
            logger.info(f"GIS: Resolved parcel {normalized} in Kadambur (mock).")
            return Exhibit(
                kind=ExhibitKind.GEOMETRY,
                source_id=f"cadastral-kadambur-{normalized}",
                payload=parcel,
            )

        logger.warning(f"GIS: Survey number {normalized} not found.")
        return None

    async def get_photo(self, survey_number: Optional[str]) -> Optional[Exhibit]:
        """Retrieve crop photo metadata with GPS binding check."""
        return await mock_retrieve_photo(survey_number, None)


async def mock_resolve_parcel(survey_number: Optional[str], village_id: Optional[str] = None) -> Optional[Exhibit]:
    """Mock GIS resolution fallback."""
    connector = GeographyConnector()
    return await connector.resolve_parcel(survey_number, village_id)


async def mock_retrieve_photo(survey_number: Optional[str], village_id: Optional[str] = None) -> Optional[Exhibit]:
    """Retrieve photo metadata and verify GPS binding."""
    if not survey_number:
        return None

    normalized = survey_number.replace("-", "/").strip()
    photo = MOCK_PHOTOS.get(normalized)

    if photo:
        # Check point in parcel if parcel is known
        parcel = MOCK_PARCELS.get(normalized)
        if parcel and "gps_lat" in photo and "gps_lon" in photo:
            spatial_res = _check_point(photo["gps_lat"], photo["gps_lon"], parcel)
            photo_copy = dict(photo)
            photo_copy["bind_status"] = "inside" if spatial_res["inside"] else "unbound"
            photo_copy["spatial_check"] = spatial_res
            return Exhibit(
                kind=ExhibitKind.IMAGE,
                source_id=f"photo-{normalized}",
                payload=photo_copy,
            )
        return Exhibit(
            kind=ExhibitKind.IMAGE,
            source_id=f"photo-{normalized}",
            payload=photo,
        )

    return None


# Public functions for Member 1 / Member 2
def find_parcel_by_survey_number(survey_number: str, source: str) -> Dict[str, Any]:
    """Public helper for Member 1/2 to lookup parcel without knowing internal details."""
    return _find_parcel(survey_number, source)


def check_point_in_parcel(latitude: float, longitude: float, parcel: Dict[str, Any]) -> Dict[str, Any]:
    """Public helper for Member 1/2 to check GPS coordinates against a parcel."""
    return _check_point(latitude, longitude, parcel)

"""Deterministic spatial checks: Point-in-polygon with boundary coverage."""

import logging
from typing import Dict, Any, List, Optional, Union
from shapely.geometry import Point, shape
from shapely.validation import make_valid

from bind_data.models.gis_results import PointCoordinates, PointInParcelResult
from bind_data.gis.survey_lookup import extract_survey_number_from_properties

logger = logging.getLogger(__name__)


def validate_coordinates(latitude: float, longitude: float) -> Optional[str]:
    """Validate latitude and longitude ranges."""
    try:
        lat = float(latitude)
        lon = float(longitude)
    except (ValueError, TypeError):
        return f"Invalid coordinates: latitude={latitude}, longitude={longitude} cannot be converted to float."

    if not (-90.0 <= lat <= 90.0):
        return f"Latitude {lat} out of range [-90.0, 90.0]."
    if not (-180.0 <= lon <= 180.0):
        return f"Longitude {lon} out of range [-180.0, 180.0]."
    return None


def check_point_in_parcel(
    latitude: float,
    longitude: float,
    parcel_geometry: Union[Dict[str, Any], Any],
    input_crs: str = "EPSG:4326",
    survey_number: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Check if a GPS coordinate point is covered by a parcel geometry.
    Uses geometry.covers(point) so boundary points are correctly counted as inside.
    NOTE: Shapely Point is constructed as Point(longitude, latitude).
    """
    coord_error = validate_coordinates(latitude, longitude)
    point_obj = PointCoordinates(latitude=latitude, longitude=longitude)
    
    if coord_error:
        res = PointInParcelResult(
            survey_number=survey_number,
            point=point_obj,
            inside=False,
            geometry_type=None,
            crs=input_crs,
            reason="Invalid coordinate values.",
            error=coord_error,
        )
        return res.to_dict()

    # Extract geometry dictionary if a full Feature was passed
    properties = None
    if isinstance(parcel_geometry, dict):
        if parcel_geometry.get("type") == "Feature":
            properties = parcel_geometry.get("properties")
            if not survey_number and properties:
                survey_number = extract_survey_number_from_properties(properties)
            raw_geom = parcel_geometry.get("geometry")
        else:
            raw_geom = parcel_geometry
    else:
        raw_geom = parcel_geometry

    # Convert to Shapely shape
    try:
        if isinstance(raw_geom, dict):
            geom_type = raw_geom.get("type")
            s_geom = shape(raw_geom)
        else:
            s_geom = raw_geom
            geom_type = getattr(s_geom, "geom_type", "Unknown")
    except Exception as e:
        res = PointInParcelResult(
            survey_number=survey_number,
            point=point_obj,
            inside=False,
            geometry_type=None,
            crs=input_crs,
            reason="Failed to parse geometry.",
            error=str(e),
            properties=properties,
        )
        return res.to_dict()

    warning_msg = None
    if not s_geom.is_valid:
        warning_msg = "Geometry was invalid; repaired using make_valid."
        s_geom = make_valid(s_geom)

    # Shapely coordinates order: x=longitude, y=latitude
    point = Point(longitude, latitude)
    
    # Check coverage (covers includes boundary, unlike contains which excludes boundary)
    is_inside = bool(s_geom.covers(point))

    if is_inside:
        reason = "Point is covered by the parcel geometry"
    else:
        reason = "Point falls outside the parcel geometry"

    res = PointInParcelResult(
        survey_number=survey_number,
        point=point_obj,
        inside=is_inside,
        geometry_type=geom_type,
        crs=input_crs,
        reason=reason,
        properties=properties,
        warning=warning_msg,
    )
    return res.to_dict()


def check_point_in_all_parcels(
    latitude: float,
    longitude: float,
    feature_collection: Dict[str, Any],
    input_crs: str = "EPSG:4326"
) -> Dict[str, Any]:
    """
    Check a GPS point against all parcels in a FeatureCollection.
    Returns matched parcel result or all checked parcels.
    """
    features = feature_collection.get("features", [])
    coord_error = validate_coordinates(latitude, longitude)
    
    if coord_error:
        return {
            "matched": False,
            "survey_number": None,
            "point": {"latitude": latitude, "longitude": longitude},
            "error": coord_error,
            "matched_parcel": None,
        }

    for feat in features:
        props = feat.get("properties") or {}
        s_num = extract_survey_number_from_properties(props)
        result = check_point_in_parcel(
            latitude=latitude,
            longitude=longitude,
            parcel_geometry=feat,
            input_crs=input_crs,
            survey_number=s_num,
        )
        if result["inside"]:
            return {
                "matched": True,
                "survey_number": s_num,
                "point": {"latitude": latitude, "longitude": longitude},
                "matched_parcel": feat,
                "check_result": result,
            }

    return {
        "matched": False,
        "survey_number": None,
        "point": {"latitude": latitude, "longitude": longitude},
        "reason": f"Point ({latitude}, {longitude}) does not fall inside any of the {len(features)} parcels.",
        "matched_parcel": None,
    }


def export_selected_parcels(features: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Export a list of parcel features as a valid GeoJSON FeatureCollection."""
    return {
        "type": "FeatureCollection",
        "crs": {
            "type": "name",
            "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"}
        },
        "features": features,
    }

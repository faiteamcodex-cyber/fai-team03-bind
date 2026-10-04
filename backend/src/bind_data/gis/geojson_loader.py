"""GeoJSON loader with CRS normalization and geometry validation."""

import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Union

import shapely.geometry
from shapely.geometry import shape, mapping
try:
    from shapely.validation import make_valid
except ImportError:
    def make_valid(geom):
        return geom.buffer(0) if not geom.is_valid else geom

logger = logging.getLogger(__name__)


def normalize_feature_collection(geojson_data: Dict[str, Any], target_crs: str = "EPSG:4326") -> Dict[str, Any]:
    """
    Validate, repair, and normalize a GeoJSON FeatureCollection structure.
    - Validates FeatureCollection / Feature structure
    - Repairs non-valid geometries using shapely.make_valid
    - Ensures standard EPSG:4326 output
    - Preserves all original properties
    """
    if not isinstance(geojson_data, dict):
        raise ValueError("GeoJSON data must be a dictionary.")

    gtype = geojson_data.get("type")
    if gtype == "Feature":
        features = [geojson_data]
    elif gtype == "FeatureCollection":
        features = geojson_data.get("features", [])
        if not isinstance(features, list):
            raise ValueError("GeoJSON FeatureCollection 'features' must be a list.")
    else:
        raise ValueError(f"Unsupported root GeoJSON type: '{gtype}'. Expected 'FeatureCollection'.")

    normalized_features = []
    for idx, feat in enumerate(features):
        if not isinstance(feat, dict):
            raise ValueError(f"Feature at index {idx} is not a dictionary.")

        properties = feat.get("properties") or {}
        geom_dict = feat.get("geometry")

        if not geom_dict:
            raise ValueError(f"Feature at index {idx} missing geometry.")

        geom_type = geom_dict.get("type")
        if geom_type not in ("Polygon", "MultiPolygon"):
            raise ValueError(f"Feature at index {idx} has unsupported geometry type '{geom_type}'. Only Polygon and MultiPolygon are supported.")

        try:
            s_geom = shape(geom_dict)
        except Exception as e:
            raise ValueError(f"Feature at index {idx} geometry parsing error: {e}")

        if not s_geom.is_valid:
            logger.warning(f"Repairing invalid geometry at index {idx}...")
            s_geom = make_valid(s_geom)

        repaired_geom_dict = mapping(s_geom)

        norm_feat = {
            "type": "Feature",
            "properties": dict(properties),
            "geometry": repaired_geom_dict,
        }
        if "id" in feat:
            norm_feat["id"] = feat["id"]
        normalized_features.append(norm_feat)

    return {
        "type": "FeatureCollection",
        "crs": {
            "type": "name",
            "properties": {"name": f"urn:ogc:def:crs:OGC:1.3:CRS84"}
        },
        "features": normalized_features,
    }


def load_geojson(
    source: Union[str, Path],
    s3_client: Optional[Any] = None,
    target_crs: str = "EPSG:4326"
) -> Dict[str, Any]:
    """
    Load GeoJSON from local file path or S3 URI (s3://bucket/key).
    Returns normalized FeatureCollection.
    """
    source_str = str(source).strip()

    if source_str.startswith("s3://"):
        # S3 URI
        parts = source_str[5:].split("/", 1)
        if len(parts) != 2:
            raise ValueError(f"Malformed S3 URI: {source_str}. Expected format: s3://bucket/key")
        bucket, key = parts
        
        if s3_client is None:
            import boto3
            s3_client = boto3.client("s3")
            
        try:
            response = s3_client.get_object(Bucket=bucket, Key=key)
            raw_content = response["Body"].read().decode("utf-8")
            data = json.loads(raw_content)
        except Exception as e:
            raise RuntimeError(f"Failed to fetch GeoJSON from S3 s3://{bucket}/{key}: {e}")
    else:
        # Local file path
        path = Path(source_str)
        if not path.exists():
            raise FileNotFoundError(f"GeoJSON file not found at path: {path}")
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

    return normalize_feature_collection(data, target_crs=target_crs)

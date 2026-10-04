"""Survey-number lookup and gazetteer resolution."""

import re
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Union

from bind_data.gis.geojson_loader import load_geojson
from bind_data.models.gis_results import ParcelLookupResult

logger = logging.getLogger(__name__)

DEFAULT_SURVEY_ALIASES = [
    "survey_number",
    "survey_no",
    "survey",
    "survey_num",
    "field_number",
    "field_no",
    "survey_key",
    "parcel_id",
]


def normalize_survey_number(val: Any) -> str:
    """
    Safely normalize survey number to string:
    - Strips whitespace
    - Preserves slash structures (e.g. '202/55', '88/1B')
    - Converts hyphens to slashes if standard (e.g. '202-55' -> '202/55')
    - Never casts to float
    """
    if val is None:
        return ""
    s = str(val).strip()
    return s


def extract_survey_number_from_properties(
    properties: Dict[str, Any],
    aliases: Optional[List[str]] = None
) -> Optional[str]:
    """Extract survey number from properties dictionary using alias search."""
    if not isinstance(properties, dict):
        return None
    search_keys = aliases or DEFAULT_SURVEY_ALIASES
    
    # Check exact lowercase matches
    prop_lower = {k.lower(): (k, v) for k, v in properties.items()}
    for alias in search_keys:
        if alias.lower() in prop_lower:
            orig_k, val = prop_lower[alias.lower()]
            norm = normalize_survey_number(val)
            if norm:
                return norm
    return None


class SurveyLookup:
    """Index and lookup parcels from a GeoJSON FeatureCollection."""

    def __init__(
        self,
        features: List[Dict[str, Any]],
        aliases: Optional[List[str]] = None,
    ):
        self.aliases = aliases or DEFAULT_SURVEY_ALIASES
        self.features = features
        self._index: Dict[str, List[Dict[str, Any]]] = {}
        self._build_index()

    def _build_index(self):
        self._index.clear()
        for feat in self.features:
            props = feat.get("properties") or {}
            s_num = extract_survey_number_from_properties(props, self.aliases)
            if s_num:
                norm_key = s_num.replace("-", "/").strip().lower()
                if norm_key not in self._index:
                    self._index[norm_key] = []
                self._index[norm_key].append(feat)

    def lookup(self, survey_number: str) -> ParcelLookupResult:
        """Deterministic lookup for a survey number."""
        norm_input = normalize_survey_number(survey_number)
        if not norm_input:
            return ParcelLookupResult(
                found=False,
                survey_number=str(survey_number),
                error="Empty or null survey number provided."
            )

        search_keys = [
            norm_input.lower(),
            norm_input.replace("-", "/").lower(),
            norm_input.replace("/", "-").lower(),
        ]

        matched_features = []
        for key in search_keys:
            if key in self._index:
                matched_features = self._index[key]
                break

        if not matched_features:
            return ParcelLookupResult(
                found=False,
                survey_number=norm_input,
                error=f"Survey number '{norm_input}' not found in cadastral map."
            )

        # Select the primary matched feature
        primary = matched_features[0]
        canonical_s_num = extract_survey_number_from_properties(primary.get("properties", {}), self.aliases) or norm_input
        gtype = primary.get("geometry", {}).get("type", "Unknown")

        return ParcelLookupResult(
            found=True,
            survey_number=canonical_s_num,
            parcel=primary,
            geometry_type=gtype,
            crs="EPSG:4326",
        )


def find_parcel_by_survey_number(
    survey_number: str,
    source: Union[str, Path, Dict[str, Any]],
    aliases: Optional[List[str]] = None,
    s3_client: Optional[Any] = None,
) -> Dict[str, Any]:
    """
    Public API: Find a parcel by survey number in a GeoJSON dataset.
    Returns JSON-serializable dictionary.
    """
    if isinstance(source, (str, Path)):
        fc = load_geojson(source, s3_client=s3_client)
    elif isinstance(source, dict) and source.get("type") == "FeatureCollection":
        fc = source
    elif isinstance(source, dict) and source.get("type") == "Feature":
        fc = {"type": "FeatureCollection", "features": [source]}
    else:
        raise ValueError("Invalid source format: must be file path, S3 URI, or FeatureCollection dict.")

    features = fc.get("features", [])
    lookup = SurveyLookup(features, aliases=aliases)
    result = lookup.lookup(survey_number)
    return result.to_dict()

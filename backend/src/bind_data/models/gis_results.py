"""GIS result models and schemas."""

from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any, List


@dataclass
class PointCoordinates:
    latitude: float
    longitude: float


@dataclass
class PointInParcelResult:
    survey_number: Optional[str]
    point: PointCoordinates
    inside: bool
    geometry_type: Optional[str]
    crs: str
    reason: str
    properties: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    warning: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to clean JSON-serializable dictionary."""
        d = {
            "survey_number": self.survey_number,
            "point": {
                "latitude": self.point.latitude,
                "longitude": self.point.longitude,
            },
            "inside": self.inside,
            "geometry_type": self.geometry_type,
            "crs": self.crs,
            "reason": self.reason,
        }
        if self.properties is not None:
            d["properties"] = self.properties
        if self.error is not None:
            d["error"] = self.error
        if self.warning is not None:
            d["warning"] = self.warning
        return d


@dataclass
class ParcelLookupResult:
    found: bool
    survey_number: str
    parcel: Optional[Dict[str, Any]] = None
    geometry_type: Optional[str] = None
    crs: str = "EPSG:4326"
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "found": self.found,
            "survey_number": self.survey_number,
            "parcel": self.parcel,
            "geometry_type": self.geometry_type,
            "crs": self.crs,
            "error": self.error,
        }

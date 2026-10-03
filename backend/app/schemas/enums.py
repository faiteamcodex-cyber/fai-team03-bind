from enum import StrEnum


class ClaimType(StrEnum):
    """All claim types in the agriculture catalog."""
    GEO_PARCEL = "GEO.PARCEL"
    REG_OWNER = "REG.OWNER"
    MEDIA_PHOTO = "MEDIA.PHOTO"
    VIS_CROP = "VIS.CROP"
    VIS_STAGE = "VIS.STAGE"
    VIS_CONDITION = "VIS.CONDITION"
    ADV_FERTILIZER = "ADV.FERTILIZER"
    ADV_PRACTICE = "ADV.PRACTICE"
    WX_CONTEXT = "WX.CONTEXT"
    META_CLARIFY = "META.CLARIFY"


class HarmClass(StrEnum):
    """Harm-if-wrong classification for routing decisions."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ClaimStatus(StrEnum):
    """Lifecycle status of a claim within a docket."""
    OPEN = "OPEN"
    BINDING = "BINDING"
    STAMPED = "STAMPED"
    REJECTED = "REJECTED"
    ABSTAINED = "ABSTAINED"
    DISPUTE = "DISPUTE"


class ExhibitKind(StrEnum):
    """Type of evidence attached to a claim."""
    GEOMETRY = "geometry"
    REGISTRY_ROW = "registry_row"
    IMAGE = "image"
    PREDICTION = "prediction"
    CHUNK = "chunk"
    WEATHER = "weather"
    FORM = "form"


class DocketStatus(StrEnum):
    """Overall docket lifecycle status."""
    PLANNING = "PLANNING"
    EXECUTING = "EXECUTING"
    VERIFYING = "VERIFYING"
    CLOSED = "CLOSED"
    FAILED = "FAILED"

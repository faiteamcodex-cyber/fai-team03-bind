"""Dataset validator for images, GeoJSON, and advisory documents."""

import os
import json
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple


def classify_file(file_path: Path) -> str:
    """
    Classify a file based on its extension, directory path, and contents.
    Categories:
    - land_documents
    - crop_images
    - cadastral_maps
    - advisory_documents
    - unknown
    """
    ext = file_path.suffix.lower()
    path_str = str(file_path).lower().replace("\\", "/")
    
    # Check directory path clues
    if "cadastral" in path_str or "map" in path_str or "parcel" in path_str or "village" in path_str:
        if ext in (".geojson", ".json"):
            return "cadastral_maps"
            
    if "crop" in path_str or "photo" in path_str or "image" in path_str or "task 4" in path_str or "task4" in path_str:
        if ext in (".jpg", ".jpeg", ".png"):
            return "crop_images"
            
    if "advisory" in path_str or "circular" in path_str or "crop_practice" in path_str:
        if ext == ".pdf":
            return "advisory_documents"
            
    if "land" in path_str or "chitta" in path_str or "patta" in path_str or "task 2" in path_str or "task2" in path_str or "document" in path_str or "record" in path_str:
        if ext in (".pdf", ".jpg", ".jpeg", ".png", ".tiff", ".json", ".csv"):
            return "land_documents"
            
    # Extension-based fallback classification
    if ext in (".jpg", ".jpeg", ".png"):
        return "crop_images"
    elif ext in (".geojson",):
        return "cadastral_maps"
    elif ext == ".json":
        # Check if it looks like GeoJSON
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                head = f.read(1024)
                if '"type"' in head and ('"FeatureCollection"' in head or '"Feature"' in head or '"Polygon"' in head):
                    return "cadastral_maps"
        except Exception:
            pass
        return "unknown"
    elif ext == ".pdf":
        return "advisory_documents"
        
    return "unknown"


def validate_image_file(file_path: Path, max_size_bytes: int = 4 * 1024 * 1024) -> Tuple[bool, List[str]]:
    """Validate image file format and size constraint (<= 4MB)."""
    errors = []
    ext = file_path.suffix.lower()
    allowed = (".jpg", ".jpeg", ".png")
    
    if ext not in allowed:
        errors.append(f"Invalid image extension '{ext}'. Only {allowed} are accepted.")
        return False, errors
        
    size = file_path.stat().st_size
    if size == 0:
        errors.append("Image file is empty (0 bytes).")
    elif size > max_size_bytes:
        errors.append(f"Image file size {size / (1024*1024):.2f} MB exceeds maximum allowed limit of {max_size_bytes / (1024*1024):.1f} MB.")
        
    return len(errors) == 0, errors


def validate_geojson_file(file_path: Path) -> Tuple[bool, List[str], Dict[str, Any]]:
    """
    Validate that GeoJSON is a valid FeatureCollection with Polygon/MultiPolygon geometries.
    Returns: (is_valid, errors, metadata)
    """
    errors = []
    metadata: Dict[str, Any] = {
        "feature_count": 0,
        "geometry_types": set(),
        "crs": "EPSG:4326 (RFC 7946 default)",
    }
    
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        errors.append(f"Failed to parse JSON: {str(e)}")
        return False, errors, metadata

    if not isinstance(data, dict):
        errors.append("Root GeoJSON object must be a JSON object.")
        return False, errors, metadata

    # Check CRS if explicitly defined
    if "crs" in data:
        crs_obj = data["crs"]
        if isinstance(crs_obj, dict) and "properties" in crs_obj:
            name = crs_obj["properties"].get("name", "")
            metadata["crs"] = name
        else:
            errors.append("GeoJSON CRS property is malformed.")
            
    # Check type
    geojson_type = data.get("type")
    if geojson_type != "FeatureCollection":
        if geojson_type == "Feature":
            features = [data]
        else:
            errors.append(f"GeoJSON root type is '{geojson_type}', expected 'FeatureCollection'.")
            return False, errors, metadata
    else:
        features = data.get("features", [])
        if not isinstance(features, list):
            errors.append("GeoJSON 'features' field must be a list.")
            return False, errors, metadata

    metadata["feature_count"] = len(features)
    if len(features) == 0:
        errors.append("FeatureCollection contains 0 features.")

    allowed_geom_types = {"Polygon", "MultiPolygon"}
    for idx, feat in enumerate(features):
        if not isinstance(feat, dict):
            errors.append(f"Feature at index {idx} is not a valid JSON object.")
            continue
        geom = feat.get("geometry")
        if not geom or not isinstance(geom, dict):
            errors.append(f"Feature at index {idx} has missing or invalid geometry.")
            continue
        gtype = geom.get("type")
        metadata["geometry_types"].add(gtype)
        if gtype not in allowed_geom_types:
            errors.append(f"Feature at index {idx} has unsupported geometry type '{gtype}'. Only Polygon and MultiPolygon are supported.")
            
        coords = geom.get("coordinates")
        if not coords or not isinstance(coords, list):
            errors.append(f"Feature at index {idx} has empty or malformed coordinates.")

    metadata["geometry_types"] = list(metadata["geometry_types"])
    return len(errors) == 0, errors, metadata


def validate_pdf_file(file_path: Path) -> Tuple[bool, List[str], Dict[str, Any]]:
    """
    Validate advisory PDF file and test text readability.
    Returns: (is_valid, errors, metadata)
    """
    errors = []
    metadata = {
        "page_count": 0,
        "total_characters": 0,
        "extractable": False,
    }
    
    size = file_path.stat().st_size
    if size == 0:
        errors.append("PDF file is 0 bytes.")
        return False, errors, metadata

    try:
        from pypdf import PdfReader
        reader = PdfReader(str(file_path))
        num_pages = len(reader.pages)
        metadata["page_count"] = num_pages
        
        if num_pages == 0:
            errors.append("PDF contains 0 pages.")
            return False, errors, metadata

        total_chars = 0
        for i, page in enumerate(reader.pages):
            text = page.extract_text() or ""
            total_chars += len(text.strip())

        metadata["total_characters"] = total_chars
        if total_chars == 0:
            errors.append("PDF contains no extractable text (empty or scanned image without OCR).")
        else:
            metadata["extractable"] = True

    except Exception as e:
        errors.append(f"Failed to read PDF: {str(e)}")

    return len(errors) == 0, errors, metadata


def validate_file(file_path: Path, max_image_size: int = 4 * 1024 * 1024) -> Dict[str, Any]:
    """Validate a single file according to its category and return validation summary."""
    category = classify_file(file_path)
    size_bytes = file_path.stat().st_size
    
    result: Dict[str, Any] = {
        "path": str(file_path),
        "filename": file_path.name,
        "category": category,
        "size_bytes": size_bytes,
        "is_valid": True,
        "errors": [],
        "warnings": [],
        "metadata": {},
    }
    
    if category == "unknown":
        result["is_valid"] = False
        result["errors"].append(f"Unknown or unsupported file format: {file_path.suffix}")
        return result
        
    if category == "crop_images":
        valid, errs = validate_image_file(file_path, max_size_bytes=max_image_size)
        result["is_valid"] = valid
        result["errors"] = errs
    elif category == "cadastral_maps":
        valid, errs, meta = validate_geojson_file(file_path)
        result["is_valid"] = valid
        result["errors"] = errs
        result["metadata"] = meta
    elif category == "advisory_documents":
        valid, errs, meta = validate_pdf_file(file_path)
        result["is_valid"] = valid
        result["errors"] = errs
        result["metadata"] = meta
    elif category == "land_documents":
        # Check size and basic format
        if size_bytes == 0:
            result["is_valid"] = False
            result["errors"].append("Land document is 0 bytes.")
        elif file_path.suffix.lower() == ".pdf":
            valid, errs, meta = validate_pdf_file(file_path)
            result["metadata"] = meta
            if not valid:
                result["warnings"].extend(errs)  # Some land docs may be scanned images
        elif file_path.suffix.lower() in (".jpg", ".jpeg", ".png"):
            valid, errs = validate_image_file(file_path, max_size_bytes=max_image_size)
            result["is_valid"] = valid
            result["errors"] = errs
        elif file_path.suffix.lower() == ".json":
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    json.load(f)
                result["is_valid"] = True
            except Exception as e:
                result["is_valid"] = False
                result["errors"].append(f"Invalid JSON land record: {e}")

    return result

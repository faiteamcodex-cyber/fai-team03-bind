"""Manifest generation and dataset inspection utilities."""

import os
import time
import json
import hashlib
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

from bind_data.ingestion.validator import validate_file, classify_file


def compute_s3_key(category: str, filename: str) -> str:
    """Map a categorized file to its standard S3 key layout."""
    category_to_prefix = {
        "land_documents": "raw/land-documents",
        "crop_images": "raw/crop-images",
        "cadastral_maps": "raw/cadastral-maps",
        "advisory_documents": "raw/advisories",
        "unknown": "raw/unknown",
    }
    prefix = category_to_prefix.get(category, "raw/unknown")
    return f"{prefix}/{filename}"


def compute_sha256(file_path: Path) -> str:
    """Compute sha256 checksum of a file without loading entire file into memory."""
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def generate_manifest(
    input_dir: Path,
    include_checksums: bool = True,
    max_image_size: int = 4 * 1024 * 1024
) -> Dict[str, Any]:
    """
    Recursively inspect input directory and generate comprehensive validation manifest.
    """
    input_dir = Path(input_dir).resolve()
    if not input_dir.exists() or not input_dir.is_dir():
        raise ValueError(f"Input directory does not exist or is not a directory: {input_dir}")

    files_list = []
    total_size = 0
    valid_count = 0
    invalid_count = 0
    category_counts: Dict[str, int] = {}

    for root, _, files in os.walk(input_dir):
        for fname in sorted(files):
            # Ignore hidden files or common temporary files
            if fname.startswith(".") or fname.endswith(".tmp"):
                continue
                
            fpath = Path(root) / fname
            val_res = validate_file(fpath, max_image_size=max_image_size)
            
            category = val_res["category"]
            category_counts[category] = category_counts.get(category, 0) + 1
            
            s3_key = compute_s3_key(category, fname)
            rel_path = str(fpath.relative_to(input_dir)).replace("\\", "/")
            
            file_entry: Dict[str, Any] = {
                "filename": fname,
                "relative_path": rel_path,
                "absolute_path": str(fpath),
                "category": category,
                "s3_target_key": s3_key,
                "size_bytes": val_res["size_bytes"],
                "is_valid": val_res["is_valid"],
                "errors": val_res["errors"],
                "warnings": val_res["warnings"],
                "metadata": val_res.get("metadata", {}),
            }
            
            if include_checksums:
                try:
                    file_entry["sha256"] = compute_sha256(fpath)
                except Exception as e:
                    file_entry["sha256_error"] = str(e)

            total_size += val_res["size_bytes"]
            if val_res["is_valid"]:
                valid_count += 1
            else:
                invalid_count += 1

            files_list.append(file_entry)

    now_iso = datetime.now(timezone.utc).isoformat()
    manifest = {
        "timestamp": now_iso,
        "input_directory": str(input_dir),
        "total_files": len(files_list),
        "valid_files": valid_count,
        "invalid_files": invalid_count,
        "total_size_bytes": total_size,
        "total_size_mb": round(total_size / (1024 * 1024), 2),
        "category_counts": category_counts,
        "all_valid": (invalid_count == 0 and len(files_list) > 0),
        "files": files_list,
    }
    return manifest


def save_manifest(manifest: Dict[str, Any], output_path: Path) -> Path:
    """Save manifest dictionary to JSON file."""
    output_path = Path(output_path).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
    return output_path

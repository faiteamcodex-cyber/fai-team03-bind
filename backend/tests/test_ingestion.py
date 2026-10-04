"""Tests for dataset validation, manifest generation, and S3 uploader."""

import json
from pathlib import Path
import pytest
from moto import mock_aws
import boto3

from bind_data.ingestion.validator import (
    classify_file,
    validate_image_file,
    validate_geojson_file,
    validate_pdf_file,
    validate_file,
)
from bind_data.ingestion.manifest import compute_s3_key, generate_manifest
from bind_data.ingestion.s3_uploader import S3DatasetUploader
from bind_data.config import IngestionConfig


def test_s3_key_generation():
    assert compute_s3_key("land_documents", "doc1.pdf") == "raw/land-documents/doc1.pdf"
    assert compute_s3_key("crop_images", "field1.jpg") == "raw/crop-images/field1.jpg"
    assert compute_s3_key("cadastral_maps", "village.geojson") == "raw/cadastral-maps/village.geojson"
    assert compute_s3_key("advisory_documents", "adv1.pdf") == "raw/advisories/adv1.pdf"
    assert compute_s3_key("unknown", "temp.xyz") == "raw/unknown/temp.xyz"


def test_file_classification(tmp_path):
    img = tmp_path / "crop_field.jpg"
    img.write_bytes(b"dummy")
    assert classify_file(img) == "crop_images"

    geo = tmp_path / "kadambur_cadastral.geojson"
    geo.write_text('{"type": "FeatureCollection", "features": []}', encoding="utf-8")
    assert classify_file(geo) == "cadastral_maps"

    pdf = tmp_path / "tnau_advisory_circular.pdf"
    pdf.write_bytes(b"%PDF-1.4 dummy")
    assert classify_file(pdf) == "advisory_documents"

    unknown = tmp_path / "data.xyz"
    unknown.write_bytes(b"dummy")
    assert classify_file(unknown) == "unknown"


def test_image_size_validation(tmp_path):
    small_img = tmp_path / "valid.jpg"
    small_img.write_bytes(b"\xFF\xD8\xFF" + b"0" * 1000)
    valid, errors = validate_image_file(small_img, max_size_bytes=4 * 1024 * 1024)
    assert valid is True
    assert len(errors) == 0

    large_img = tmp_path / "too_large.png"
    # Create file > 4MB (4.2 MB)
    large_img.write_bytes(b"\x89PNG\r\n\x1a\n" + b"0" * (5 * 1024 * 1024))
    valid, errors = validate_image_file(large_img, max_size_bytes=4 * 1024 * 1024)
    assert valid is False
    assert any("exceeds maximum allowed limit" in e for e in errors)

    invalid_ext = tmp_path / "image.bmp"
    invalid_ext.write_bytes(b"BM" + b"0" * 100)
    valid, errors = validate_image_file(invalid_ext)
    assert valid is False
    assert any("Invalid image extension" in e for e in errors)


def test_geojson_validation(tmp_path, sample_geojson_data):
    valid_path = tmp_path / "valid.geojson"
    with open(valid_path, "w", encoding="utf-8") as f:
        json.dump(sample_geojson_data, f)

    is_valid, errors, meta = validate_geojson_file(valid_path)
    assert is_valid is True
    assert len(errors) == 0
    assert meta["feature_count"] == 2

    # Malformed JSON
    bad_json = tmp_path / "bad.geojson"
    bad_json.write_text("{not-valid-json", encoding="utf-8")
    is_valid, errors, _ = validate_geojson_file(bad_json)
    assert is_valid is False

    # Unsupported geometry (e.g. Point instead of Polygon/MultiPolygon)
    point_geo = tmp_path / "point.geojson"
    point_data = {
        "type": "FeatureCollection",
        "features": [{"type": "Feature", "geometry": {"type": "Point", "coordinates": [79.0, 10.0]}, "properties": {}}]
    }
    with open(point_geo, "w", encoding="utf-8") as f:
        json.dump(point_data, f)

    is_valid, errors, _ = validate_geojson_file(point_geo)
    assert is_valid is False
    assert any("unsupported geometry type 'Point'" in e for e in errors)


def test_manifest_generation(tmp_path, sample_geojson_data, sample_pdf_file):
    # Setup dataset structure
    dataset_dir = tmp_path / "dataset"
    dataset_dir.mkdir()
    
    img = dataset_dir / "crop_field.jpg"
    img.write_bytes(b"\xFF\xD8\xFF" + b"0" * 100)
    
    geo = dataset_dir / "village_cadastral.geojson"
    with open(geo, "w", encoding="utf-8") as f:
        json.dump(sample_geojson_data, f)
        
    manifest = generate_manifest(dataset_dir)
    assert manifest["total_files"] == 2
    assert manifest["valid_files"] == 2
    assert manifest["invalid_files"] == 0
    assert manifest["all_valid"] is True
    assert "crop_images" in manifest["category_counts"]
    assert "cadastral_maps" in manifest["category_counts"]


@mock_aws
def test_s3_uploader_dry_run_and_live(tmp_path, sample_geojson_data):
    dataset_dir = tmp_path / "dataset"
    dataset_dir.mkdir()
    img = dataset_dir / "photo.jpg"
    img.write_bytes(b"test image bytes")
    
    manifest = generate_manifest(dataset_dir)
    
    # 1. Test Dry Run (Zero AWS interaction)
    uploader = S3DatasetUploader()
    dry_report = uploader.upload_dataset(manifest, bucket="test-bucket", dry_run=True)
    assert dry_report["dry_run"] is True
    assert dry_report["uploaded_files"] == 1
    assert dry_report["file_results"][0]["status"] == "SIMULATED_SUCCESS"

    # 2. Test Live Upload with Moto S3
    s3 = boto3.client("s3", region_name="ap-south-1")
    s3.create_bucket(
        Bucket="fai-tce-team03-datasets",
        CreateBucketConfiguration={"LocationConstraint": "ap-south-1"}
    )
    
    live_uploader = S3DatasetUploader(s3_client=s3)
    live_report = live_uploader.upload_dataset(manifest, bucket="fai-tce-team03-datasets", dry_run=False)
    assert live_report["uploaded_files"] == 1
    assert live_report["failed_files"] == 0
    assert live_report["manifest_status"] == "UPLOADED"

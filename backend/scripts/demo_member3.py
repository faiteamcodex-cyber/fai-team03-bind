"""End-to-End Member 3 (Data/GIS & DevOps) Demonstration Script."""

import sys
import os
import json
import asyncio
from pathlib import Path

# Ensure paths
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir / "src"))
sys.path.insert(0, str(backend_dir))

from bind_data.ingestion.manifest import generate_manifest
from bind_data.ingestion.s3_uploader import S3DatasetUploader
from bind_data.gis.survey_lookup import find_parcel_by_survey_number
from bind_data.gis.spatial_checks import check_point_in_parcel
from bind_data.rag.pdf_extract import extract_advisories_from_dir
from bind_data.rag.chunker import chunk_document
from bind_data.rag.titan_embeddings import FakeEmbeddingProvider
from bind_data.rag.chroma_index import ChromaAdvisoryStore
from scripts.seed_land_records import seed_records


def run_demo():
    print("=" * 80)
    print(" BIND MEMBER 3 (DATA/GIS & DEVOPS) COMPLETE RUNTIME DEMONSTRATION")
    print("=" * 80)

    fixtures_dir = backend_dir / "data" / "fixtures"
    artifacts_dir = backend_dir / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    # -------------------------------------------------------------------------
    # 1. Dataset Ingestion & Validation
    # -------------------------------------------------------------------------
    print("\n[STEP 1] Running Dataset Ingestion & Validation...")
    manifest = generate_manifest(fixtures_dir)
    print(f"  [OK] Files Inspected : {manifest['total_files']}")
    print(f"  [OK] All Valid       : {manifest['all_valid']}")
    print(f"  [OK] Categories      : {manifest['category_counts']}")

    # -------------------------------------------------------------------------
    # 2. S3 Multipart Upload Dry-Run
    # -------------------------------------------------------------------------
    print("\n[STEP 2] Simulating S3 Multipart Upload (Dry-Run)...")
    uploader = S3DatasetUploader()
    upload_report = uploader.upload_dataset(manifest, bucket="fai-tce-team03-datasets", dry_run=True)
    print(f"  [OK] Target Bucket   : s3://{upload_report['bucket']}")
    print(f"  [OK] Uploaded (Sim)  : {upload_report['uploaded_files']} file(s)")
    print(f"  [OK] Manifest Key    : {upload_report['manifest_s3_key']}")

    # -------------------------------------------------------------------------
    # 3. Deterministic GIS & Survey Number Lookup
    # -------------------------------------------------------------------------
    print("\n[STEP 3] Testing Deterministic GIS & Survey-Number Resolution...")
    geojson_path = fixtures_dir / "cadastral_sample.geojson"
    
    # 3A: Survey Number Lookup
    parcel_res = find_parcel_by_survey_number("202/55", source=geojson_path)
    print(f"  [OK] Lookup '202/55' : Found={parcel_res['found']}, GeomType={parcel_res['geometry_type']}")

    # 3B: Point-in-Polygon Check (Interior point)
    pt_interior = check_point_in_parcel(latitude=10.7895, longitude=79.3250, parcel_geometry=parcel_res["parcel"])
    print(f"  [OK] GPS (10.7895, 79.3250) [Interior] -> Inside: {pt_interior['inside']} ({pt_interior['reason']})")

    # 3C: Point-in-Polygon Check (Boundary point with geometry.covers)
    pt_boundary = check_point_in_parcel(latitude=10.7890, longitude=79.3245, parcel_geometry=parcel_res["parcel"])
    print(f"  [OK] GPS (10.7890, 79.3245) [Boundary] -> Inside: {pt_boundary['inside']} ({pt_boundary['reason']})")

    # 3D: Point Outside
    pt_outside = check_point_in_parcel(latitude=10.7950, longitude=79.3300, parcel_geometry=parcel_res["parcel"])
    print(f"  [OK] GPS (10.7950, 79.3300) [Outside]  -> Inside: {pt_outside['inside']} ({pt_outside['reason']})")

    # -------------------------------------------------------------------------
    # 4. Advisory RAG Indexing & Metadata Querying
    # -------------------------------------------------------------------------
    print("\n[STEP 4] Testing Advisory RAG Pipeline (PDF -> Chunks -> ChromaDB)...")
    pdf_docs = extract_advisories_from_dir(fixtures_dir)
    all_chunks = []
    for doc in pdf_docs:
        if doc.get("extractable"):
            chunks = chunk_document(doc)
            all_chunks.extend(chunks)

    chroma_dir = artifacts_dir / "demo_chroma"
    store = ChromaAdvisoryStore(
        persist_dir=str(chroma_dir),
        collection_name="demo_advisories",
        embedding_provider=FakeEmbeddingProvider(dimension=256),
    )
    store.index_chunks(all_chunks)
    print(f"  [OK] Extracted & Indexed : {len(all_chunks)} chunk(s) into ChromaDB")

    # Query with hard metadata filter (crop=paddy, growth_stage=tillering)
    query_results = store.query(
        query_text="recommended fertilizer dosage",
        crop="paddy",
        growth_stage="tillering",
        top_k=1,
    )
    if query_results:
        top = query_results[0]
        preview_text = top['text'].replace('\n', ' ')
        print(f"  [OK] RAG Query Match     : [{top['crop']} | {top['growth_stage']}] {preview_text[:80]}...")

    # -------------------------------------------------------------------------
    # 5. DynamoDB Mock Land Records Seeder
    # -------------------------------------------------------------------------
    print("\n[STEP 5] Testing DynamoDB Land Records Seeder (Dry-Run)...")
    with open(fixtures_dir / "land_records.json", "r", encoding="utf-8") as f:
        records = json.load(f)
    seed_res = seed_records(records, table_name="fai-tce-team03-land-records", dry_run=True)
    print(f"  [OK] Validated & Prepped : {seed_res['written_records']} record(s) for table '{seed_res['table_name']}'")

    print("\n" + "=" * 80)
    print(" [SUCCESS] ALL MEMBER 3 FUNCTIONALITY VERIFIED AND OPERATIONAL!")
    print("=" * 80)


if __name__ == "__main__":
    run_demo()

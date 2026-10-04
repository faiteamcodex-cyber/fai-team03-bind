"""Unit tests for Advisory RAG pipeline, ChromaDB vector store, and S3 state."""

import pytest
from pathlib import Path
from moto import mock_aws
import boto3

from bind_data.rag.pdf_extract import extract_text_from_pdf
from bind_data.rag.chunker import chunk_document, chunk_text_by_paragraphs, infer_metadata_from_path
from bind_data.rag.titan_embeddings import FakeEmbeddingProvider
from bind_data.rag.chroma_index import ChromaAdvisoryStore, query_advisories
from bind_data.rag.s3_state import export_chroma_state_to_s3, restore_chroma_state_from_s3
from bind_data.models.rag_models import DocumentChunk


def test_fake_embedding_provider():
    provider = FakeEmbeddingProvider(dimension=128)
    vec1 = provider.embed_text("Paddy fertilizer dose")
    vec2 = provider.embed_text("Paddy fertilizer dose")
    vec3 = provider.embed_text("Sugarcane grand growth irrigation")

    assert len(vec1) == 128
    assert vec1 == vec2  # Deterministic
    assert vec1 != vec3  # Distinct texts produce distinct vectors


def test_infer_metadata_from_filename():
    meta1 = infer_metadata_from_path("data/advisories/paddy_cauvery_delta_tillering.pdf")
    assert meta1["crop"] == "paddy"
    assert meta1["zone"] == "cauvery_delta"
    assert meta1["growth_stage"] == "tillering"

    meta2 = infer_metadata_from_path("data/advisories/sugarcane_grand_growth.pdf")
    assert meta2["crop"] == "sugarcane"
    assert meta2["growth_stage"] == "grand_growth"
    assert meta2["zone"] == "unknown"


def test_chunking_paragraphs_and_stable_ids():
    text = (
        "Paragraph 1: Apply DAP at 25 kg per acre during tillering stage.\n\n"
        "Paragraph 2: Maintain 2-3 cm standing water in paddy fields.\n\n"
        "Paragraph 3: Monitor for stem borer infestation."
    )
    chunks = chunk_text_by_paragraphs(text, chunk_size=100, chunk_overlap=20)
    assert len(chunks) >= 2

    doc_data = {
        "source": "paddy_advisory.pdf",
        "path": "data/advisories/paddy_advisory.pdf",
        "pages": [{"page_number": 1, "text": text}],
    }
    doc_chunks = chunk_document(doc_data, chunk_size=100, chunk_overlap=20)
    assert len(doc_chunks) >= 2
    assert all(c.crop == "paddy" for c in doc_chunks)
    assert all(c.chunk_id.startswith("paddy_advisory_pdf") for c in doc_chunks)


def test_pdf_extraction_empty_and_valid(tmp_path, sample_pdf_file):
    # Test valid PDF
    res = extract_text_from_pdf(sample_pdf_file)
    assert res["source"] == sample_pdf_file.name
    assert res["page_count"] >= 1

    # Test empty PDF
    empty_pdf = tmp_path / "empty.pdf"
    empty_pdf.write_bytes(b"")
    empty_res = extract_text_from_pdf(empty_pdf)
    assert empty_res["extractable"] is False
    assert "error" in empty_res


def test_chromadb_indexing_and_metadata_query(tmp_path, fake_embedding_provider):
    persist_dir = tmp_path / "chroma_db"
    store = ChromaAdvisoryStore(
        persist_dir=str(persist_dir),
        collection_name="test_advisories",
        embedding_provider=fake_embedding_provider,
    )

    chunks = [
        DocumentChunk(
            chunk_id="chunk_paddy_1",
            text="Apply 25 kg/acre DAP for Paddy at tillering stage.",
            source="tnau_paddy.pdf",
            page=1,
            paragraph_index=0,
            crop="paddy",
            growth_stage="tillering",
            zone="cauvery_delta",
        ),
        DocumentChunk(
            chunk_id="chunk_paddy_2",
            text="Apply 35 kg/acre Urea for Paddy at panicle initiation.",
            source="tnau_paddy.pdf",
            page=2,
            paragraph_index=0,
            crop="paddy",
            growth_stage="panicle_initiation",
            zone="cauvery_delta",
        ),
        DocumentChunk(
            chunk_id="chunk_sugarcane_1",
            text="Apply 65 kg/acre Urea for Sugarcane at grand growth phase.",
            source="tnau_sugar.pdf",
            page=1,
            paragraph_index=0,
            crop="sugarcane",
            growth_stage="grand_growth",
            zone="cauvery_delta",
        ),
    ]

    # Index chunks
    indexed = store.index_chunks(chunks)
    assert indexed == 3
    assert store.count() == 3

    # Re-indexing same chunks should not duplicate (upsert idempotency)
    re_indexed = store.index_chunks(chunks)
    assert store.count() == 3

    # Query with hard metadata filter: crop=paddy, growth_stage=tillering
    results = store.query(
        query_text="fertilizer dosage",
        crop="paddy",
        growth_stage="tillering",
        top_k=2,
    )
    assert len(results) > 0
    top = results[0]
    assert top["crop"] == "paddy"
    assert top["growth_stage"] == "tillering"
    assert "DAP" in top["text"]

    # Missing mandatory filter check
    with pytest.raises(ValueError):
        store.query(query_text="fertilizer", crop="", growth_stage="tillering")


@mock_aws
def test_s3_chroma_state_export_and_restore(tmp_path, fake_embedding_provider):
    # Setup Chroma directory with data
    chroma_dir = tmp_path / "chroma"
    store = ChromaAdvisoryStore(
        persist_dir=str(chroma_dir),
        collection_name="state_test",
        embedding_provider=fake_embedding_provider,
    )
    store.index_chunks([
        DocumentChunk(
            chunk_id="c1",
            text="Test chunk content",
            source="doc1.pdf",
            page=1,
            paragraph_index=0,
            crop="paddy",
            growth_stage="tillering",
        )
    ])

    # S3 setup via moto
    s3 = boto3.client("s3", region_name="ap-south-1")
    s3.create_bucket(
        Bucket="fai-tce-team03-app-state",
        CreateBucketConfiguration={"LocationConstraint": "ap-south-1"}
    )

    # 1. Export Chroma state to S3
    export_res = export_chroma_state_to_s3(
        local_chroma_dir=chroma_dir,
        state_bucket="fai-tce-team03-app-state",
        version_tag="v1",
        s3_client=s3,
        dry_run=False,
    )
    assert export_res["status"] == "UPLOADED"

    # 2. Restore Chroma state into a new directory
    restore_target = tmp_path / "restored" / "chroma"
    restore_chroma_state_from_s3(
        target_chroma_dir=restore_target,
        state_bucket="fai-tce-team03-app-state",
        version_tag="v1",
        s3_client=s3,
    )

    # Verify restored database
    restored_store = ChromaAdvisoryStore(
        persist_dir=str(restore_target),
        collection_name="state_test",
        embedding_provider=fake_embedding_provider,
    )
    assert restored_store.count() == 1

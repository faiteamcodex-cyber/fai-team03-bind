"""Advisory RAG index builder CLI script."""

import sys
import os
import argparse
import logging
from pathlib import Path

# Ensure backend/src and backend are in sys.path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir / "src"))
sys.path.insert(0, str(backend_dir))

from bind_data.config import RAGConfig
from bind_data.rag.pdf_extract import extract_advisories_from_dir, extract_text_from_pdf
from bind_data.rag.chunker import chunk_document
from bind_data.rag.titan_embeddings import TitanEmbeddingProvider, FakeEmbeddingProvider
from bind_data.rag.chroma_index import ChromaAdvisoryStore
from bind_data.rag.s3_state import export_chroma_state_to_s3

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("build_rag_index")


def main():
    parser = argparse.ArgumentParser(description="Build persistent ChromaDB RAG index from advisory PDFs using Titan Embeddings.")
    parser.add_argument(
        "--input", "-i",
        type=str,
        required=True,
        help="Input directory containing advisory PDFs or path to single PDF."
    )
    parser.add_argument(
        "--persist-dir", "-d",
        type=str,
        default="./artifacts/chroma",
        help="Local directory to persist ChromaDB index (default: ./artifacts/chroma)."
    )
    parser.add_argument(
        "--collection", "-c",
        type=str,
        default="advisory_store",
        help="ChromaDB collection name (default: advisory_store)."
    )
    parser.add_argument(
        "--model-id", "-m",
        type=str,
        default="amazon.titan-embed-text-v2:0",
        help="Bedrock Titan Embedding Model ID (default: amazon.titan-embed-text-v2:0)."
    )
    parser.add_argument(
        "--profile", "-p",
        type=str,
        default=None,
        help="AWS CLI profile name (e.g. fai-team03)."
    )
    parser.add_argument(
        "--region", "-r",
        type=str,
        default="ap-south-1",
        help="AWS region (default: ap-south-1)."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate extraction and chunking without invoking AWS Bedrock or updating ChromaDB."
    )
    parser.add_argument(
        "--fake-embeddings",
        action="store_true",
        help="Use deterministic offline fake embedding provider (zero AWS calls)."
    )
    parser.add_argument(
        "--upload-state",
        action="store_true",
        help="Export and upload built Chroma index package to S3 state bucket."
    )
    parser.add_argument(
        "--state-bucket",
        type=str,
        default="fai-tce-team03-app-state",
        help="Application state bucket for Chroma index backup (default: fai-tce-team03-app-state)."
    )
    parser.add_argument(
        "--version-tag",
        type=str,
        default="v1",
        help="Version tag for Chroma state backup (default: v1)."
    )
    parser.add_argument(
        "--confirm",
        action="store_true",
        help="Explicit confirmation to execute live AWS Bedrock calls and/or S3 uploads."
    )

    args = parser.parse_args()
    input_path = Path(args.input).resolve()
    persist_dir = Path(args.persist_dir).resolve()

    if not input_path.exists():
        logger.error(f"Input path does not exist: {input_path}")
        sys.exit(1)

    print("=" * 70)
    print(" BIND ADVISORY RAG INDEX BUILDER")
    print(f" Input Path     : {input_path}")
    print(f" Persist Dir    : {persist_dir}")
    print(f" Collection     : {args.collection}")
    print(f" Embedding Model: {args.model_id}")
    print(f" Mode           : {'DRY-RUN' if args.dry_run else ('OFFLINE FAKE EMBEDDINGS' if args.fake_embeddings else 'LIVE AWS BEDROCK')}")
    print("=" * 70)

    # Safety check
    if not args.dry_run and not args.fake_embeddings and not args.confirm:
        logger.error(
            "SAFETY CHECK: Real Bedrock embedding generation requested without --confirm flag! "
            "Pass --dry-run, --fake-embeddings, or --confirm explicitly."
        )
        sys.exit(1)

    # 1. Extract PDFs
    if input_path.is_file() and input_path.suffix.lower() == ".pdf":
        pdf_docs = [extract_text_from_pdf(input_path)]
    elif input_path.is_dir():
        pdf_docs = extract_advisories_from_dir(input_path)
    else:
        logger.error(f"Unsupported input: {input_path}")
        sys.exit(1)

    logger.info(f"Extracted {len(pdf_docs)} PDF document(s).")

    # 2. Chunk Documents
    all_chunks = []
    for doc in pdf_docs:
        if not doc.get("extractable", False):
            logger.warning(f"Skipping unextractable PDF: {doc['source']} ({doc.get('error')})")
            continue
        chunks = chunk_document(doc)
        all_chunks.extend(chunks)

    logger.info(f"Generated {len(all_chunks)} chunk(s) across all documents.")

    if args.dry_run:
        print("\n--- DRY-RUN SUMMARY ---")
        print(f"Documents Analyzed : {len(pdf_docs)}")
        print(f"Chunks Generated   : {len(all_chunks)}")
        if all_chunks:
            print("\nSample Chunk Metadata:")
            sample = all_chunks[0]
            print(f"  - Chunk ID     : {sample.chunk_id}")
            print(f"  - Crop         : {sample.crop}")
            print(f"  - Zone         : {sample.zone}")
            print(f"  - Growth Stage : {sample.growth_stage}")
            print(f"  - Text Preview : {sample.text[:100]}...")
        print("\n[OK] Dry-run completed successfully.")
        sys.exit(0)

    # 3. Setup Embedding Provider
    if args.fake_embeddings:
        provider = FakeEmbeddingProvider()
    else:
        provider = TitanEmbeddingProvider(
            model_id=args.model_id,
            aws_profile=args.profile,
            aws_region=args.region,
        )

    # 4. Index Chunks in ChromaDB
    store = ChromaAdvisoryStore(
        persist_dir=str(persist_dir),
        collection_name=args.collection,
        embedding_provider=provider,
    )
    indexed_count = store.index_chunks(all_chunks)
    print(f"\n[OK] Indexed {indexed_count} chunks into ChromaDB at '{persist_dir}'. Total in collection: {store.count()}")

    # 5. Optionally Export State to S3
    if args.upload_state:
        logger.info("Exporting Chroma index package to S3 state bucket...")
        export_res = export_chroma_state_to_s3(
            local_chroma_dir=persist_dir,
            state_bucket=args.state_bucket,
            version_tag=args.version_tag,
            aws_profile=args.profile,
            aws_region=args.region,
            dry_run=args.dry_run,
        )
        print(f"[OK] Chroma state exported: {export_res['s3_uri']}")


if __name__ == "__main__":
    main()

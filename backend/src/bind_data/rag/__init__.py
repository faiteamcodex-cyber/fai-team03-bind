"""Advisory RAG pipeline: PDF extraction, chunking, Titan embeddings, ChromaDB, and S3 state."""

from bind_data.rag.pdf_extract import extract_text_from_pdf, extract_advisories_from_dir
from bind_data.rag.chunker import chunk_document, chunk_text_by_paragraphs
from bind_data.rag.titan_embeddings import EmbeddingProvider, TitanEmbeddingProvider, FakeEmbeddingProvider
from bind_data.rag.chroma_index import ChromaAdvisoryStore, query_advisories
from bind_data.rag.s3_state import export_chroma_state_to_s3, restore_chroma_state_from_s3

__all__ = [
    "extract_text_from_pdf",
    "extract_advisories_from_dir",
    "chunk_document",
    "chunk_text_by_paragraphs",
    "EmbeddingProvider",
    "TitanEmbeddingProvider",
    "FakeEmbeddingProvider",
    "ChromaAdvisoryStore",
    "query_advisories",
    "export_chroma_state_to_s3",
    "restore_chroma_state_from_s3",
]

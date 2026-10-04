"""ChromaDB vector store for agricultural advisory circulars with metadata filtering."""

import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

from bind_data.models.rag_models import DocumentChunk, AdvisoryQueryResult
from bind_data.rag.titan_embeddings import EmbeddingProvider, TitanEmbeddingProvider

logger = logging.getLogger(__name__)


class ChromaAdvisoryStore:
    """Manages persistent ChromaDB vector store for agricultural advisories."""

    def __init__(
        self,
        persist_dir: str = "./artifacts/chroma",
        collection_name: str = "advisory_store",
        embedding_provider: Optional[EmbeddingProvider] = None,
    ):
        self.persist_dir = Path(persist_dir).resolve()
        self.collection_name = collection_name
        self.embedding_provider = embedding_provider or TitanEmbeddingProvider()
        self._client = None
        self._collection = None

    def _get_collection(self):
        if self._collection is not None:
            return self._collection

        import chromadb
        from chromadb.config import Settings

        self.persist_dir.mkdir(parents=True, exist_ok=True)
        self._client = chromadb.PersistentClient(
            path=str(self.persist_dir),
            settings=Settings(anonymized_telemetry=False)
        )
        self._collection = self._client.get_or_create_collection(
            name=self.collection_name,
            metadata={"description": "BIND Agricultural Advisory Circular Store"}
        )
        return self._collection

    def index_chunks(self, chunks: List[DocumentChunk], batch_size: int = 64) -> int:
        """
        Embed and upsert DocumentChunks into the ChromaDB collection.
        Uses stable chunk IDs to prevent duplicate entries.
        """
        if not chunks:
            return 0

        col = self._get_collection()
        total_indexed = 0

        for i in range(0, len(chunks), batch_size):
            batch = chunks[i:i + batch_size]
            
            ids = [c.chunk_id for c in batch]
            documents = [c.text for c in batch]
            metadatas = [c.to_metadata() for c in batch]
            
            # Generate embeddings
            embeddings = self.embedding_provider.embed_batch(documents)

            col.upsert(
                ids=ids,
                documents=documents,
                embeddings=embeddings,
                metadatas=metadatas,
            )
            total_indexed += len(batch)
            logger.info(f"Indexed batch of {len(batch)} chunks (Total: {total_indexed}/{len(chunks)})")

        return total_indexed

    def query(
        self,
        query_text: str,
        crop: str,
        growth_stage: str,
        zone: Optional[str] = None,
        top_k: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Query advisory store with mandatory vision output metadata filters:
        - crop (mandatory)
        - growth_stage (mandatory)
        - zone (optional)
        """
        if not crop or not crop.strip():
            raise ValueError("Query error: 'crop' is a mandatory filter and must be supplied from vision outputs.")
        if not growth_stage or not growth_stage.strip():
            raise ValueError("Query error: 'growth_stage' is a mandatory filter and must be supplied from vision outputs.")

        norm_crop = crop.strip().lower()
        norm_stage = growth_stage.strip().lower()
        norm_zone = zone.strip().lower() if zone else None

        # Build hard WHERE filter dictionary for Chroma
        conditions = [
            {"crop": {"$eq": norm_crop}},
            {"growth_stage": {"$eq": norm_stage}},
        ]
        if norm_zone:
            conditions.append({"zone": {"$eq": norm_zone}})

        if len(conditions) > 1:
            where_clause = {"$and": conditions}
        else:
            where_clause = conditions[0]

        query_embedding = self.embedding_provider.embed_text(query_text)
        col = self._get_collection()

        try:
            results = col.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                where=where_clause,
                include=["documents", "metadatas", "distances"],
            )
        except Exception as e:
            # If no matches found or filter exception, attempt fallback on crop only
            logger.warning(f"Filtered query failed ({e}), attempting fallback with crop-only filter...")
            fallback_where = {"crop": {"$eq": norm_crop}}
            results = col.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                where=fallback_where,
                include=["documents", "metadatas", "distances"],
            )

        output: List[Dict[str, Any]] = []
        if not results or not results.get("ids") or len(results["ids"][0]) == 0:
            return output

        ids = results["ids"][0]
        docs = results.get("documents", [[]])[0]
        metas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]

        for idx in range(len(ids)):
            meta = metas[idx] if idx < len(metas) else {}
            dist = distances[idx] if idx < len(distances) else 0.0
            # Score: cosine similarity estimate from distance
            score = round(max(0.0, 1.0 - dist), 4)

            item = AdvisoryQueryResult(
                chunk_id=ids[idx],
                text=docs[idx] if idx < len(docs) else "",
                score=score,
                source=meta.get("source", "unknown"),
                page=int(meta.get("page", 1)),
                crop=meta.get("crop", norm_crop),
                growth_stage=meta.get("growth_stage", norm_stage),
                zone=meta.get("zone", "unknown"),
                metadata=meta,
            )
            output.append(item.to_dict())

        return output

    def count(self) -> int:
        """Return total chunks count in collection."""
        col = self._get_collection()
        return col.count()


def query_advisories(
    query_text: str,
    crop: str,
    growth_stage: str,
    zone: Optional[str] = None,
    top_k: int = 5,
    persist_dir: str = "./artifacts/chroma",
    collection_name: str = "advisory_store",
    embedding_provider: Optional[EmbeddingProvider] = None,
) -> List[Dict[str, Any]]:
    """
    Public function for Member 1 / Member 2 integration.
    Queries the advisory RAG vector store with hard metadata filters.
    """
    store = ChromaAdvisoryStore(
        persist_dir=persist_dir,
        collection_name=collection_name,
        embedding_provider=embedding_provider,
    )
    return store.query(
        query_text=query_text,
        crop=crop,
        growth_stage=growth_stage,
        zone=zone,
        top_k=top_k,
    )

"""RAG data models and chunk representations."""

from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any, List


@dataclass
class DocumentChunk:
    chunk_id: str
    text: str
    source: str
    page: int
    paragraph_index: int
    crop: str = "unknown"
    zone: str = "unknown"
    growth_stage: str = "unknown"
    extra_metadata: Optional[Dict[str, Any]] = None

    def to_metadata(self) -> Dict[str, Any]:
        """Convert chunk metadata to flat scalar dictionary for ChromaDB."""
        meta = {
            "chunk_id": str(self.chunk_id),
            "source": str(self.source),
            "page": int(self.page),
            "paragraph_index": int(self.paragraph_index),
            "crop": str(self.crop).lower(),
            "zone": str(self.zone).lower(),
            "growth_stage": str(self.growth_stage).lower(),
        }
        if self.extra_metadata:
            for k, v in self.extra_metadata.items():
                if isinstance(v, (str, int, float, bool)):
                    meta[k] = v
                else:
                    meta[k] = str(v)
        return meta


@dataclass
class AdvisoryQueryResult:
    chunk_id: str
    text: str
    score: float
    source: str
    page: int
    crop: str
    growth_stage: str
    zone: str
    metadata: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "chunk_id": self.chunk_id,
            "text": self.text,
            "score": self.score,
            "source": self.source,
            "page": self.page,
            "crop": self.crop,
            "growth_stage": self.growth_stage,
            "zone": self.zone,
            "metadata": self.metadata,
        }

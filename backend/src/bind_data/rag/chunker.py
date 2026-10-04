import re
import hashlib
from pathlib import Path
from typing import Dict, Any, List, Optional, Union

from bind_data.models.rag_models import DocumentChunk

KNOWN_CROPS = [
    "paddy", "rice", "sugarcane", "cotton", "groundnut", "maize", "banana",
    "pulses", "blackgram", "greengram", "chilli", "turmeric", "coconut",
    "sorghum", "ragi", "millets", "wheat", "soybean"
]

KNOWN_STAGES = [
    "panicle_initiation", "tillering", "flowering", "vegetative",
    "nursery", "transplanting", "grand_growth", "maturity", "harvest",
    "grain_filling", "seedling", "ripening", "sowing", "pod_formation"
]

KNOWN_ZONES = [
    "cauvery_delta", "cauvery", "north_zone", "south_zone", "western_zone",
    "high_rainfall", "coastal", "delta", "dryland", "irrigated"
]


def infer_metadata_from_path(
    file_path: Union[str, Path],
    explicit_metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, str]:
    """
    Infer crop, zone, and growth_stage from:
    1. Explicit metadata if provided.
    2. File name and directory path patterns.
    3. Fallback to 'unknown' (never invent values).
    """
    meta = {
        "crop": "unknown",
        "zone": "unknown",
        "growth_stage": "unknown",
    }
    
    if explicit_metadata:
        for k in ("crop", "zone", "growth_stage"):
            if k in explicit_metadata and explicit_metadata[k]:
                meta[k] = str(explicit_metadata[k]).lower().strip()

    clean_path = str(file_path).lower().replace("\\", "/")
    path_tokens = set(re.split(r'[^a-zA-Z0-9]+', clean_path))
    normalized_path = re.sub(r'[^a-zA-Z0-9]+', '_', clean_path)

    # If crop is still unknown, search filename & path tokens
    if meta["crop"] == "unknown":
        for c in KNOWN_CROPS:
            if c in path_tokens or c in normalized_path:
                meta["crop"] = "paddy" if c == "rice" else c
                break

    # If stage is still unknown, search filename & path
    if meta["growth_stage"] == "unknown":
        for s in KNOWN_STAGES:
            clean_s = s.replace("_", "")
            if s in normalized_path or clean_s in normalized_path or s in path_tokens:
                meta["growth_stage"] = s
                break

    # If zone is still unknown, search filename & path
    if meta["zone"] == "unknown":
        for z in KNOWN_ZONES:
            clean_z = z.replace("_", "")
            if z in normalized_path or clean_z in normalized_path or z in path_tokens:
                meta["zone"] = z
                break

    return meta


def generate_stable_chunk_id(source_name: str, page: int, chunk_index: int, text: str) -> str:
    """Generate a deterministic, stable chunk ID based on source, page, chunk index, and content hash."""
    clean_src = re.sub(r'[^a-zA-Z0-9_-]', '_', source_name)
    content_hash = hashlib.md5(text.encode("utf-8")).hexdigest()[:8]
    return f"{clean_src}_p{page}_c{chunk_index}_{content_hash}"


def chunk_text_by_paragraphs(
    text: str,
    chunk_size: int = 500,
    chunk_overlap: int = 100
) -> List[str]:
    """
    Split text into chunks respecting paragraph and sentence boundaries.
    """
    if not text or not text.strip():
        return []

    # Split by double newlines into paragraphs
    raw_paragraphs = [p.strip() for p in re.split(r'\n\s*\n', text) if p.strip()]
    if not raw_paragraphs:
        raw_paragraphs = [text.strip()]

    chunks = []
    current_chunk = ""

    for para in raw_paragraphs:
        if len(current_chunk) + len(para) + 1 <= chunk_size:
            if current_chunk:
                current_chunk += "\n\n" + para
            else:
                current_chunk = para
        else:
            if current_chunk:
                chunks.append(current_chunk)
                # Keep overlap from the end of current_chunk if possible
                overlap_text = current_chunk[-chunk_overlap:] if len(current_chunk) > chunk_overlap else ""
                current_chunk = (overlap_text + "\n\n" + para).strip()
            else:
                # Paragraph itself is larger than chunk_size, split by sentences
                sentences = re.split(r'(?<=[.?!])\s+', para)
                sub_chunk = ""
                for s in sentences:
                    if len(sub_chunk) + len(s) + 1 <= chunk_size:
                        sub_chunk = f"{sub_chunk} {s}".strip()
                    else:
                        if sub_chunk:
                            chunks.append(sub_chunk)
                            sub_chunk = s
                        else:
                            # Hard split very long words/sentences
                            for i in range(0, len(s), chunk_size - chunk_overlap):
                                chunks.append(s[i:i + chunk_size])
                            sub_chunk = ""
                if sub_chunk:
                    current_chunk = sub_chunk

    if current_chunk:
        chunks.append(current_chunk)

    return chunks


def chunk_document(
    extracted_pdf_data: Dict[str, Any],
    chunk_size: int = 500,
    chunk_overlap: int = 100,
    explicit_metadata: Optional[Dict[str, Any]] = None,
) -> List[DocumentChunk]:
    """
    Convert extracted PDF pages into a list of tagged DocumentChunk objects.
    """
    source = extracted_pdf_data.get("source", "unknown_document")
    doc_path = extracted_pdf_data.get("path", source)
    inferred_meta = infer_metadata_from_path(doc_path, explicit_metadata=explicit_metadata)

    chunks: List[DocumentChunk] = []
    chunk_counter = 0

    for page_info in extracted_pdf_data.get("pages", []):
        page_num = page_info.get("page_number", 1)
        page_text = page_info.get("text", "")
        
        raw_chunks = chunk_text_by_paragraphs(
            page_text,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )

        for p_idx, c_text in enumerate(raw_chunks):
            chunk_counter += 1
            chunk_id = generate_stable_chunk_id(source, page_num, p_idx, c_text)
            
            chunk_obj = DocumentChunk(
                chunk_id=chunk_id,
                text=c_text,
                source=source,
                page=page_num,
                paragraph_index=p_idx,
                crop=inferred_meta["crop"],
                zone=inferred_meta["zone"],
                growth_stage=inferred_meta["growth_stage"],
            )
            chunks.append(chunk_obj)

    return chunks

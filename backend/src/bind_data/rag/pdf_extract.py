"""PDF text extraction with page metadata preservation."""

import os
import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

logger = logging.getLogger(__name__)


def extract_text_from_pdf(
    pdf_path: Path,
    output_text_dir: Optional[Path] = None,
) -> Dict[str, Any]:
    """
    Extract text from an advisory PDF page-by-page using pypdf.
    Preserves page number metadata.
    Reports PDFs with no extractable text.
    Optionally stores extracted text under output_text_dir.
    """
    pdf_path = Path(pdf_path).resolve()
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")

    from pypdf import PdfReader

    try:
        reader = PdfReader(str(pdf_path))
    except Exception as e:
        logger.error(f"Failed to open PDF {pdf_path.name}: {e}")
        return {
            "source": pdf_path.name,
            "path": str(pdf_path),
            "page_count": 0,
            "extractable": False,
            "error": str(e),
            "pages": [],
        }

    pages_data = []
    total_text_length = 0

    for idx, page in enumerate(reader.pages):
        page_num = idx + 1
        try:
            page_text = page.extract_text() or ""
        except Exception as e:
            logger.warning(f"Error extracting text from {pdf_path.name} page {page_num}: {e}")
            page_text = ""

        cleaned_text = page_text.strip()
        total_text_length += len(cleaned_text)

        pages_data.append({
            "page_number": page_num,
            "text": cleaned_text,
            "char_count": len(cleaned_text),
        })

    is_extractable = total_text_length > 0
    result = {
        "source": pdf_path.name,
        "path": str(pdf_path),
        "page_count": len(reader.pages),
        "extractable": is_extractable,
        "total_characters": total_text_length,
        "pages": pages_data,
    }

    if not is_extractable:
        result["error"] = "PDF contains 0 extractable text characters (may be empty or scanned image)."

    if output_text_dir is not None:
        out_dir = Path(output_text_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        txt_file = out_dir / f"{pdf_path.stem}.txt"
        with open(txt_file, "w", encoding="utf-8") as f:
            for p in pages_data:
                f.write(f"--- PAGE {p['page_number']} ---\n")
                f.write(p["text"] + "\n\n")
        result["extracted_text_path"] = str(txt_file)

    return result


def extract_advisories_from_dir(
    advisories_dir: Path,
    output_text_dir: Optional[Path] = None,
) -> List[Dict[str, Any]]:
    """Recursively extract all advisory PDFs from a directory."""
    advisories_dir = Path(advisories_dir).resolve()
    results = []
    
    for root, _, files in os.walk(advisories_dir):
        for fname in sorted(files):
            if fname.lower().endswith(".pdf") and not fname.startswith("."):
                pdf_path = Path(root) / fname
                res = extract_text_from_pdf(pdf_path, output_text_dir=output_text_dir)
                results.append(res)

    return results

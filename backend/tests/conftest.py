"""Pytest configuration and reusable fixtures for offline testing."""

import sys
import os
import json
import pytest
from pathlib import Path

# Ensure backend and backend/src are available on python path
test_dir = Path(__file__).resolve().parent
backend_dir = test_dir.parent
src_dir = backend_dir / "src"

if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from bind_data.rag.titan_embeddings import FakeEmbeddingProvider


@pytest.fixture
def fake_embedding_provider():
    """Deterministic offline embedding provider fixture."""
    return FakeEmbeddingProvider(dimension=256)


@pytest.fixture
def sample_geojson_data():
    """Valid GeoJSON FeatureCollection fixture with Polygon and MultiPolygon."""
    return {
        "type": "FeatureCollection",
        "crs": {
            "type": "name",
            "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"}
        },
        "features": [
            {
                "type": "Feature",
                "properties": {
                    "survey_number": "202/55",
                    "village": "Kadambur",
                    "extent_acres": 2.5
                },
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[
                        [79.3245, 10.7890],
                        [79.3255, 10.7890],
                        [79.3255, 10.7900],
                        [79.3245, 10.7900],
                        [79.3245, 10.7890]
                    ]]
                }
            },
            {
                "type": "Feature",
                "properties": {
                    "field_no": "145/2",
                    "village": "Kadambur",
                    "extent_acres": 1.8
                },
                "geometry": {
                    "type": "MultiPolygon",
                    "coordinates": [
                        [[
                            [79.3260, 10.7910],
                            [79.3270, 10.7910],
                            [79.3270, 10.7920],
                            [79.3260, 10.7920],
                            [79.3260, 10.7910]
                        ]],
                        [[
                            [79.3275, 10.7910],
                            [79.3285, 10.7910],
                            [79.3285, 10.7920],
                            [79.3275, 10.7920],
                            [79.3275, 10.7910]
                        ]]
                    ]
                }
            }
        ]
    }


@pytest.fixture
def sample_geojson_file(tmp_path, sample_geojson_data):
    """Path to temporary GeoJSON file."""
    fpath = tmp_path / "cadastral.geojson"
    with open(fpath, "w", encoding="utf-8") as f:
        json.dump(sample_geojson_data, f)
    return fpath


@pytest.fixture
def sample_pdf_file(tmp_path):
    """Create a minimal valid test PDF with extractable text using reportlab or pypdf writer."""
    from pypdf import PdfWriter
    from io import BytesIO
    
    # We can create a simple PDF with pypdf or text stream
    pdf_path = tmp_path / "paddy_cauvery_tillering_advisory.pdf"
    
    # Simple PDF stream generator using ReportLab if installed or pure PDF format
    try:
        from reportlab.pdfgen import canvas
        c = canvas.Canvas(str(pdf_path))
        c.drawString(100, 750, "TNAU Advisory Circular 2026: Paddy Kharif Season")
        c.drawString(100, 700, "Crop: Paddy, Zone: Cauvery Delta, Growth Stage: Tillering")
        c.drawString(100, 650, "Recommended Fertilizer: DAP 25 kg/acre and Zinc Sulphate 5 kg/acre.")
        c.drawString(100, 600, "Apply 21 days after transplanting with active water management.")
        c.showPage()
        c.save()
    except Exception:
        # Fallback raw minimal PDF if reportlab is unavailable
        writer = PdfWriter()
        writer.add_blank_page(width=612, height=792)
        with open(pdf_path, "wb") as f:
            writer.write(f)
            
    return pdf_path

# BIND - Cross-Modal Claim Runtime (Team 03)

## Member 3 Scope: Data/GIS & DevOps Infrastructure

BIND is an event-driven AWS serverless runtime for processing land-survey requests and agricultural advisory generation. This repository contains the complete **Member 3 (Data/GIS and DevOps Engineer)** implementation for cloud data ingestion, deterministic GIS spatial validation, vector RAG indexing with Bedrock Titan Embeddings & ChromaDB, DynamoDB land records seeding, and AWS SAM serverless infrastructure.

---

## 1. AWS SSO Setup & Authentication

Authentication is managed via AWS SSO profile (`fai-team03`) in region `ap-south-1`.

> [!IMPORTANT]
> **Safety Rule**: Never hardcode AWS access keys or tokens in source code or `.env` files committed to version control.

To authenticate locally:
```bash
aws configure sso --profile fai-team03
aws sso login --profile fai-team03
```
Export your profile into the shell session:
```bash
# On Linux/macOS
export AWS_PROFILE=fai-team03
export AWS_REGION=ap-south-1

# On Windows PowerShell
$env:AWS_PROFILE="fai-team03"
$env:AWS_REGION="ap-south-1"
```

---

## 2. Local Setup & Dependencies

### Requirements
- **Python**: 3.11
- **GIS Libraries**: GeoPandas 1.0.1, Shapely 2.0.6
- **Vector DB**: ChromaDB 0.6.3
- **PDF Extraction**: PyPDF 6.19.0
- **AWS SDK**: Boto3 1.38.0
- **Docker**: Required for local SAM container image builds (due to GDAL/GEOS C-extensions)

### Installation
```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: .\venv\Scripts\Activate.ps1

# Install package dependencies and development tools
pip install -r backend/requirements.txt pypdf pytest moto
pip install -e .
```

---

## 3. Dataset Ingestion & Validation

The ingestion pipeline inspects, validates, classifies, and manifests local datasets before uploading to S3.

### Directory Classification & Constraints
| Category | Supported Extensions | Validation Rules |
| :--- | :--- | :--- |
| `crop_images` | `.jpg`, `.jpeg`, `.png` | Maximum size $\le$ 4 MB. Empty files rejected. |
| `cadastral_maps` | `.geojson`, `.json` | Valid `FeatureCollection` with `Polygon` or `MultiPolygon` geometries. |
| `advisory_documents` | `.pdf` | Must contain extractable text characters. |
| `land_documents` | `.pdf`, `.png`, `.jpg`, `.json` | Valid size and parsing structure. |

### Validation Command
```bash
# Validate dataset and generate manifest
python -m scripts.validate_dataset \
  --input ./data \
  --manifest ./artifacts/manifest.json
```

---

## 4. S3 Multipart Upload

Uploads are executed using `boto3.s3.transfer.TransferConfig` with multipart chunking and concurrency.

### Key Layout
```text
s3://fai-tce-team03-datasets/
├── raw/land-documents/<filename>
├── raw/crop-images/<filename>
├── raw/cadastral-maps/<filename>
├── raw/advisories/<filename>
└── manifests/<timestamp>-manifest.json
```

### Commands
```bash
# 1. Dry-Run simulation (always run first)
python -m scripts.upload_dataset \
  --input ./data \
  --bucket fai-tce-team03-datasets \
  --profile fai-team03 \
  --region ap-south-1 \
  --manifest ./artifacts/manifest.json \
  --dry-run

# 2. Live Upload (requires explicit confirmation flag)
python -m scripts.upload_dataset \
  --input ./data \
  --bucket fai-tce-team03-datasets \
  --profile fai-team03 \
  --region ap-south-1 \
  --manifest ./artifacts/manifest.json \
  --confirm
```

---

## 5. Deterministic GIS & Survey Lookup

GIS utilities operate deterministically without LLM dependencies.

### Capabilities
- **Survey Number Matching**: Preserves exact strings (e.g., `"202/55"`), trims whitespace, supports aliases (`survey_number`, `field_no`, `survey_no`, `survey_key`), and avoids float conversion.
- **Point-in-Polygon (`covers`)**: Uses `geometry.covers(Point(longitude, latitude))` to correctly accept points situated exactly on parcel boundaries.
- **Coordinate Order**: Explicitly orders Shapely points as `Point(longitude, latitude)`.

### Example Output
```json
{
  "survey_number": "202/55",
  "point": {
    "latitude": 10.7895,
    "longitude": 79.3250
  },
  "inside": true,
  "geometry_type": "Polygon",
  "crs": "EPSG:4326",
  "reason": "Point is covered by the parcel geometry"
}
```

---

## 6. Advisory RAG Pipeline (Bedrock Titan + ChromaDB)

### Pipeline Flow
$$\text{PDF} \xrightarrow{\text{pypdf}} \text{Page Text} \xrightarrow{\text{Paragraph Chunker}} \text{DocumentChunk (Stable ID)} \xrightarrow{\text{Bedrock Titan V2}} \text{ChromaDB}$$

### Commands
```bash
# 1. Dry-run chunking and metadata inspection
python -m scripts.build_rag_index \
  --input ./data/advisories \
  --persist-dir ./artifacts/chroma \
  --profile fai-team03 \
  --region ap-south-1 \
  --dry-run

# 2. Offline indexing using deterministic fake embeddings (for unit tests / dev)
python -m scripts.build_rag_index \
  --input ./data/advisories \
  --persist-dir ./artifacts/chroma \
  --collection advisory_store \
  --fake-embeddings

# 3. Live Bedrock Titan embedding generation & S3 state backup
python -m scripts.build_rag_index \
  --input ./data/advisories \
  --persist-dir ./artifacts/chroma \
  --collection advisory_store \
  --model-id amazon.titan-embed-text-v2:0 \
  --profile fai-team03 \
  --region ap-south-1 \
  --upload-state \
  --confirm
```

### Mandatory Metadata Filters
Advisory retrieval requires explicit vision outputs before querying:
```python
from bind_data.rag.chroma_index import query_advisories

results = query_advisories(
    query_text="fertilizer schedule for tillering stage",
    crop="paddy",           # Mandatory
    growth_stage="tillering",# Mandatory
    zone="cauvery_delta",   # Optional
    top_k=5,
)
```

---

## 7. DynamoDB Mock Land Records

### Schema
- **Table Name**: `fai-tce-team03-land-records`
- **Partition Key**: `survey_number` (String)
- **Billing**: `PAY_PER_REQUEST` (On-Demand)

### Seeding Command
```bash
# Dry-run
python -m scripts.seed_land_records \
  --fixtures ./data/fixtures/land_records.json \
  --table-name fai-tce-team03-land-records \
  --dry-run

# Live write (with confirmation)
python -m scripts.seed_land_records \
  --fixtures ./data/fixtures/land_records.json \
  --table-name fai-tce-team03-land-records \
  --profile fai-team03 \
  --region ap-south-1 \
  --confirm
```

---

## 8. AWS SAM Serverless Infrastructure

### Packaging Evaluation
GeoPandas and GDAL depend on native compiled libraries (`libgeos`, `libproj`, `libgdal`) that exceed AWS Lambda standard zip package limits and can introduce binary incompatibility. The SAM template (`template.yaml`) defines a **Container Image** Lambda function packaged via `Dockerfile`.

### Verification Commands
```bash
# Validate SAM template
sam validate --lint

# Build container image
sam build --use-container

# (Documentation only - Deploy requires explicit approval)
# sam deploy --config-file samconfig.toml.example
```

---

## 9. Integration Contract for Members 1 & 2

Member 1 (Kernel Architect) and Member 2 (ML/Bedrock Engineer) can consume Member 3's modules directly through standard public interfaces:

```python
# GIS Resolution
from bind_data.gis.survey_lookup import find_parcel_by_survey_number
parcel_result = find_parcel_by_survey_number("202/55", source="./data/fixtures/cadastral_sample.geojson")

# Point-in-Polygon Check
from bind_data.gis.spatial_checks import check_point_in_parcel
spatial_result = check_point_in_parcel(latitude=10.7895, longitude=79.3250, parcel_geometry=parcel_result["parcel"])

# Advisory RAG Query
from bind_data.rag.chroma_index import query_advisories
advisories = query_advisories(
    query_text="fertilizer dosage",
    crop="paddy",
    growth_stage="tillering"
)
```

---

## 10. Running Tests

The test suite runs 100% offline without AWS credentials using pytest and Moto mocks:
```bash
pytest backend/tests -v
```

"""Configuration management for bind_data."""

import os
from pathlib import Path
from typing import Optional, Dict, Any
from dataclasses import dataclass, field


@dataclass
class IngestionConfig:
    """Configuration for dataset ingestion and S3 uploads."""
    data_bucket: str = "fai-tce-team03-datasets"
    state_bucket: str = "fai-tce-team03-app-state"
    aws_region: str = "ap-south-1"
    aws_profile: Optional[str] = None
    
    # File limits
    max_image_size_bytes: int = 4 * 1024 * 1024  # 4 MB
    allowed_image_extensions: tuple = (".jpg", ".jpeg", ".png")
    allowed_geojson_extensions: tuple = (".geojson", ".json")
    allowed_advisory_extensions: tuple = (".pdf",)
    
    # S3 Multipart upload configuration
    multipart_threshold_bytes: int = 8 * 1024 * 1024  # 8 MB
    multipart_chunksize_bytes: int = 8 * 1024 * 1024  # 8 MB
    max_concurrency: int = 5


@dataclass
class RAGConfig:
    """Configuration for RAG vector index and embedding models."""
    state_bucket: str = "fai-tce-team03-app-state"
    aws_region: str = "ap-south-1"
    aws_profile: Optional[str] = None
    embedding_model_id: str = "amazon.titan-embed-text-v2:0"
    chroma_collection: str = "advisory_store"
    chroma_persist_dir: str = "./artifacts/chroma"
    chunk_size: int = 500
    chunk_overlap: int = 100
    max_retries: int = 5
    backoff_factor: float = 1.5


@dataclass
class GISConfig:
    """Configuration for GIS and survey number operations."""
    target_crs: str = "EPSG:4326"
    survey_number_aliases: list = field(default_factory=lambda: [
        "survey_number",
        "survey_no",
        "survey",
        "survey_num",
        "field_number",
        "field_no",
        "survey_key",
    ])


@dataclass
class DynamoDBConfig:
    """Configuration for Land Records DynamoDB mock table."""
    table_name: str = "fai-tce-team03-land-records"
    aws_region: str = "ap-south-1"
    aws_profile: Optional[str] = None


def get_env_or_default(key: str, default: str) -> str:
    """Retrieve environment variable or fallback to default."""
    return os.getenv(key, default)


def load_ingestion_config() -> IngestionConfig:
    """Load IngestionConfig from environment."""
    return IngestionConfig(
        data_bucket=get_env_or_default("DATA_BUCKET", "fai-tce-team03-datasets"),
        state_bucket=get_env_or_default("STATE_BUCKET", "fai-tce-team03-app-state"),
        aws_region=get_env_or_default("AWS_REGION", os.getenv("AWS_DEFAULT_REGION", "ap-south-1")),
        aws_profile=os.getenv("AWS_PROFILE"),
    )


def load_rag_config() -> RAGConfig:
    """Load RAGConfig from environment."""
    return RAGConfig(
        state_bucket=get_env_or_default("STATE_BUCKET", "fai-tce-team03-app-state"),
        aws_region=get_env_or_default("AWS_REGION", os.getenv("AWS_DEFAULT_REGION", "ap-south-1")),
        aws_profile=os.getenv("AWS_PROFILE"),
        embedding_model_id=get_env_or_default("TITAN_EMBEDDING_MODEL_ID", "amazon.titan-embed-text-v2:0"),
        chroma_collection=get_env_or_default("CHROMA_COLLECTION", "advisory_store"),
        chroma_persist_dir=get_env_or_default("CHROMA_PERSIST_DIR", "./artifacts/chroma"),
    )


def load_dynamodb_config() -> DynamoDBConfig:
    """Load DynamoDBConfig from environment."""
    return DynamoDBConfig(
        table_name=get_env_or_default("LAND_RECORDS_TABLE", "fai-tce-team03-land-records"),
        aws_region=get_env_or_default("AWS_REGION", os.getenv("AWS_DEFAULT_REGION", "ap-south-1")),
        aws_profile=os.getenv("AWS_PROFILE"),
    )

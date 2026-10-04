"""Tests for configuration loading and defaults."""

import os
from bind_data.config import (
    load_ingestion_config,
    load_rag_config,
    load_dynamodb_config,
    IngestionConfig,
    RAGConfig,
    DynamoDBConfig,
)


def test_default_ingestion_config():
    cfg = IngestionConfig()
    assert cfg.data_bucket == "fai-tce-team03-datasets"
    assert cfg.state_bucket == "fai-tce-team03-app-state"
    assert cfg.aws_region == "ap-south-1"
    assert cfg.max_image_size_bytes == 4 * 1024 * 1024


def test_load_ingestion_config_env_overrides(monkeypatch):
    monkeypatch.setenv("DATA_BUCKET", "custom-bucket")
    monkeypatch.setenv("AWS_REGION", "us-east-1")
    monkeypatch.setenv("AWS_PROFILE", "custom-profile")
    
    cfg = load_ingestion_config()
    assert cfg.data_bucket == "custom-bucket"
    assert cfg.aws_region == "us-east-1"
    assert cfg.aws_profile == "custom-profile"


def test_load_rag_config_defaults():
    cfg = load_rag_config()
    assert cfg.embedding_model_id == "amazon.titan-embed-text-v2:0"
    assert cfg.chroma_collection == "advisory_store"


def test_load_dynamodb_config_defaults():
    cfg = load_dynamodb_config()
    assert cfg.table_name == "fai-tce-team03-land-records"
    assert cfg.aws_region == "ap-south-1"

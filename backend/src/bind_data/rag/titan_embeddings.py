"""Bedrock Titan Text Embeddings adapter with retries and test fake provider."""

import json
import time
import hashlib
import logging
from abc import ABC, abstractmethod
from typing import List, Optional, Any

logger = logging.getLogger(__name__)


class EmbeddingProvider(ABC):
    """Abstract interface for text embedding models."""

    @abstractmethod
    def embed_text(self, text: str) -> List[float]:
        """Generate embedding vector for a single text."""
        pass

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embedding vectors for a batch of texts."""
        return [self.embed_text(t) for t in texts]


class FakeEmbeddingProvider(EmbeddingProvider):
    """Deterministic offline embedding provider for unit tests (zero AWS calls)."""

    def __init__(self, dimension: int = 1024):
        self.dimension = dimension

    def embed_text(self, text: str) -> List[float]:
        """Compute deterministic normalized embedding vector based on text hash."""
        # Use SHA-256 hash of text to seed deterministic vector
        h = hashlib.sha256(text.encode("utf-8")).digest()
        vec = []
        for i in range(self.dimension):
            byte_val = h[i % len(h)]
            # Normalize to roughly [-1.0, 1.0]
            val = ((byte_val / 255.0) * 2.0) - 1.0 + (0.001 * (i % 17))
            vec.append(round(val, 6))
        # Normalize vector magnitude
        norm = sum(x * x for x in vec) ** 0.5
        if norm > 0:
            vec = [round(x / norm, 6) for x in vec]
        return vec


class TitanEmbeddingProvider(EmbeddingProvider):
    """AWS Bedrock Titan Text Embeddings V2 client adapter with retry logic."""

    def __init__(
        self,
        model_id: str = "amazon.titan-embed-text-v2:0",
        bedrock_runtime_client: Optional[Any] = None,
        aws_profile: Optional[str] = None,
        aws_region: str = "ap-south-1",
        max_retries: int = 5,
        backoff_factor: float = 1.5,
    ):
        self.model_id = model_id
        self._client = bedrock_runtime_client
        self.aws_profile = aws_profile
        self.aws_region = aws_region
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor

    def _get_client(self):
        if self._client is not None:
            return self._client
        import boto3
        kwargs = {"region_name": self.aws_region}
        if self.aws_profile:
            kwargs["profile_name"] = self.aws_profile
        session = boto3.Session(**kwargs)
        self._client = session.client("bedrock-runtime")
        return self._client

    def embed_text(self, text: str) -> List[float]:
        """
        Call Bedrock InvokeModel to generate Titan Text Embedding.
        Implements exponential backoff for rate limits and transient errors.
        Does NOT log document content or embedding values.
        """
        if not text or not text.strip():
            # Return zero vector if empty
            return [0.0] * 1024

        client = self._get_client()
        payload = json.dumps({"inputText": text})
        
        attempt = 0
        last_exception = None

        while attempt < self.max_retries:
            attempt += 1
            try:
                start_t = time.time()
                response = client.invoke_model(
                    modelId=self.model_id,
                    body=payload,
                    contentType="application/json",
                    accept="application/json",
                )
                elapsed_ms = round((time.time() - start_t) * 1000, 2)
                response_body = json.loads(response["body"].read())
                embedding = response_body.get("embedding", [])
                
                logger.debug(f"Titan embedding generated in {elapsed_ms}ms (dim={len(embedding)})")
                return embedding

            except Exception as e:
                last_exception = e
                err_str = str(e)
                # Check for throttling or connection errors
                is_throttling = "ThrottlingException" in err_str or "TooManyRequests" in err_str
                is_retryable = is_throttling or "ServiceUnavailable" in err_str or "InternalServerException" in err_str
                
                if is_retryable and attempt < self.max_retries:
                    sleep_sec = self.backoff_factor ** attempt
                    logger.warning(
                        f"Bedrock invocation failed on attempt {attempt}/{self.max_retries} "
                        f"({type(e).__name__}). Retrying in {sleep_sec:.2f}s..."
                    )
                    time.sleep(sleep_sec)
                else:
                    logger.error(f"Bedrock Titan embedding invocation failed: {type(e).__name__}")
                    raise

        raise RuntimeError(f"Failed to generate embedding after {self.max_retries} attempts: {last_exception}")

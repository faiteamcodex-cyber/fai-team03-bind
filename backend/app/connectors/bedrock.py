"""AWS Bedrock client wrapper supporting Text, Multimodal (Vision), and Embeddings.

Part of Dinesh Kumar's (Member 2) deliverables:
- Wraps AWS Bedrock InvokeModel and Converse APIs.
- Dedicated methods for Planner/Binder (luna), Student Vision (nova-lite),
  Teacher Vision (terra), and Titan Embeddings.
- Token usage tracking, latency profiling, and cost estimation.
- Automatic mock fallback when credentials are unavailable or BIND_USE_MOCKS=true.
"""

from __future__ import annotations

import base64
import json
import logging
import time
from typing import Any, Dict, List, Optional, Tuple

from app.config import settings

logger = logging.getLogger(__name__)


# Standard pricing table per 1,000 tokens (USD)
BEDROCK_PRICING: dict[str, dict[str, float]] = {
    # Nova Micro (Fast text / planner)
    "apac.amazon.nova-micro-v1:0": {"input": 0.000035 / 1000, "output": 0.00014 / 1000},
    "amazon.nova-micro-v1:0": {"input": 0.000035 / 1000, "output": 0.00014 / 1000},
    # Nova Lite (Student Vision / Multimodal)
    "apac.amazon.nova-lite-v1:0": {"input": 0.00006 / 1000, "output": 0.00024 / 1000},
    "amazon.nova-lite-v1:0": {"input": 0.00006 / 1000, "output": 0.00024 / 1000},
    # Nova Pro / Teacher Vision
    "apac.amazon.nova-pro-v1:0": {"input": 0.0008 / 1000, "output": 0.0032 / 1000},
    "amazon.nova-pro-v1:0": {"input": 0.0008 / 1000, "output": 0.0032 / 1000},
    # Gpt-5.6-luna / terra aliases
    "gpt-5.6-luna": {"input": 0.001 / 1000, "output": 0.003 / 1000},
    "gpt-5.6-terra": {"input": 0.003 / 1000, "output": 0.012 / 1000},
    # Titan Text Embeddings V2
    "amazon.titan-embed-text-v2:0": {"input": 0.00002 / 1000, "output": 0.0},
}


class BedrockResponse(str):
    """Standardized response from Bedrock model invocations.
    
    Subclasses `str` so legacy calls expecting raw string (e.g. `response.strip()`)
    work seamlessly, while also providing token usage, cost, and latency metadata.
    """

    model_id: str
    input_tokens: int
    output_tokens: int
    latency_ms: int
    cost_usd: float
    raw_response: dict
    is_mock: bool

    def __new__(
        cls,
        text: str,
        model_id: str = "",
        input_tokens: int = 0,
        output_tokens: int = 0,
        latency_ms: int = 0,
        cost_usd: float = 0.0,
        raw_response: Optional[dict] = None,
        is_mock: bool = False,
    ):
        obj = super().__new__(cls, text)
        obj.model_id = model_id
        obj.input_tokens = input_tokens
        obj.output_tokens = output_tokens
        obj.latency_ms = latency_ms
        obj.cost_usd = cost_usd
        obj.raw_response = raw_response or {}
        obj.is_mock = is_mock
        return obj

    @property
    def text(self) -> str:
        """Alias for string content."""
        return str(self)

    def json_content(self) -> Any:
        """Parse response text as JSON if possible."""
        raw = str(self).strip()
        # Handle markdown fences
        if raw.startswith("```json"):
            raw = raw[7:]
        elif raw.startswith("```"):
            raw = raw[3:]
        if raw.endswith("```"):
            raw = raw[:-3]
        return json.loads(raw.strip())


class BedrockClient:
    """High-level client wrapping AWS Bedrock for text, multimodal vision, and embeddings."""

    def __init__(self, use_mocks: Optional[bool] = None):
        self.use_mocks = use_mocks if use_mocks is not None else settings.use_mocks
        self._client = None
        self._init_client()

    def _init_client(self) -> None:
        """Initialize boto3 bedrock-runtime client if not in mock mode."""
        if self.use_mocks:
            logger.info("BedrockClient initialized in MOCK mode.")
            return

        try:
            import boto3
            creds = settings.get_aws_credentials()
            kwargs: dict[str, Any] = {k: v for k, v in creds.items() if v is not None}
            if settings.aws_profile and not creds.get("aws_access_key_id"):
                kwargs["profile_name"] = settings.aws_profile

            session = boto3.Session(**kwargs)
            self._client = session.client("bedrock-runtime")
            logger.info("Bedrock runtime client initialized successfully.")
        except Exception as e:
            logger.warning(
                f"Failed to initialize live Bedrock client ({e}). Operating in automatic fallback mode."
            )
            self._client = None

    @property
    def is_live(self) -> bool:
        """Return True if live client is available and mock mode is off."""
        return not self.use_mocks and self._client is not None

    def calculate_cost(self, model_id: str, input_tokens: int, output_tokens: int) -> float:
        """Estimate invocation cost in USD based on model pricing."""
        rates = BEDROCK_PRICING.get(
            model_id,
            {"input": 0.0001 / 1000, "output": 0.0004 / 1000}
        )
        return (input_tokens * rates["input"]) + (output_tokens * rates["output"])

    async def invoke(
        self,
        model_id: str,
        system_prompt: str = "",
        user_message: str = "",
        max_tokens: int = 2048,
        temperature: float = 0.1,
        image_bytes: Optional[bytes] = None,
        image_format: str = "jpeg",
    ) -> BedrockResponse:
        """Invoke a Bedrock model (Text or Vision) with metrics and fallback."""
        start_time = time.time()

        if not self.is_live:
            return self._mock_response(model_id, user_message, start_time)

        try:
            content_blocks: list[dict[str, Any]] = []
            if image_bytes:
                content_blocks.append({
                    "image": {
                        "format": image_format.lower().replace("jpg", "jpeg"),
                        "source": {"bytes": image_bytes},
                    }
                })
            content_blocks.append({"text": user_message})

            messages = [{"role": "user", "content": content_blocks}]
            system_list = [{"text": system_prompt}] if system_prompt else []

            try:
                # 1. Standard Converse API
                response = self._client.converse(
                    modelId=model_id,
                    messages=messages,
                    system=system_list,
                    inferenceConfig={
                        "maxTokens": max_tokens,
                        "temperature": temperature,
                    },
                )
                latency_ms = int((time.time() - start_time) * 1000)
                output_text = response["output"]["message"]["content"][0]["text"]
                usage = response.get("usage", {})
                in_tokens = usage.get("inputTokens", max(1, len(user_message) // 4))
                out_tokens = usage.get("outputTokens", max(1, len(output_text) // 4))
                cost = self.calculate_cost(model_id, in_tokens, out_tokens)

                return BedrockResponse(
                    text=output_text,
                    model_id=model_id,
                    input_tokens=in_tokens,
                    output_tokens=out_tokens,
                    latency_ms=latency_ms,
                    cost_usd=cost,
                    raw_response=response,
                    is_mock=False,
                )

            except Exception as conv_err:
                logger.warning(
                    f"Converse API call failed for {model_id} ({conv_err}); falling back to invoke_model."
                )
                return await self._invoke_model_fallback(
                    model_id=model_id,
                    system_prompt=system_prompt,
                    user_message=user_message,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    image_bytes=image_bytes,
                    image_format=image_format,
                    start_time=start_time,
                )

        except Exception as e:
            logger.error(f"Live Bedrock invocation failed ({e}). Returning fallback response.")
            return self._mock_response(model_id, user_message, start_time)

    async def _invoke_model_fallback(
        self,
        model_id: str,
        system_prompt: str,
        user_message: str,
        max_tokens: int,
        temperature: float,
        image_bytes: Optional[bytes],
        image_format: str,
        start_time: float,
    ) -> BedrockResponse:
        """Raw InvokeModel fallback for models or configurations without Converse API support."""
        if "titan" in model_id.lower():
            payload = {
                "inputText": f"{system_prompt}\n\n{user_message}".strip(),
                "textGenerationConfig": {
                    "maxTokenCount": max_tokens,
                    "temperature": temperature,
                },
            }
        else:
            payload = {
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
                "max_tokens": max_tokens,
                "temperature": temperature,
            }

        response = self._client.invoke_model(
            modelId=model_id,
            body=json.dumps(payload),
            contentType="application/json",
            accept="application/json",
        )
        latency_ms = int((time.time() - start_time) * 1000)
        body = json.loads(response["body"].read())

        if "content" in body:
            output_text = body["content"][0]["text"]
        elif "output" in body:
            output_text = body["output"]["message"]["content"][0]["text"]
        elif "results" in body:
            output_text = body["results"][0]["outputText"]
        else:
            output_text = json.dumps(body)

        in_tokens = max(1, (len(system_prompt) + len(user_message)) // 4)
        out_tokens = max(1, len(output_text) // 4)
        cost = self.calculate_cost(model_id, in_tokens, out_tokens)

        return BedrockResponse(
            text=output_text,
            model_id=model_id,
            input_tokens=in_tokens,
            output_tokens=out_tokens,
            latency_ms=latency_ms,
            cost_usd=cost,
            raw_response=body,
            is_mock=False,
        )

    async def invoke_planner(
        self,
        user_prompt: str,
        system_prompt: str = "",
        model_id: Optional[str] = None,
    ) -> BedrockResponse:
        """Invoke Planner LLM (gpt-5.6-luna / nova-micro)."""
        mid = model_id or settings.planner_model_id
        return await self.invoke(
            model_id=mid,
            system_prompt=system_prompt,
            user_message=user_prompt,
            temperature=0.0,
        )

    async def invoke_student_vision(
        self,
        prompt: str,
        image_bytes: Optional[bytes] = None,
        image_format: str = "jpeg",
        model_id: Optional[str] = None,
    ) -> BedrockResponse:
        """Invoke Student Vision model (amazon.nova-lite)."""
        mid = model_id or settings.student_vision_model_id
        return await self.invoke(
            model_id=mid,
            system_prompt=(
                "You are an agricultural vision specialist. Analyze the crop image carefully and "
                "return precise JSON."
            ),
            user_message=prompt,
            image_bytes=image_bytes,
            image_format=image_format,
            temperature=0.1,
        )

    async def invoke_teacher_vision(
        self,
        prompt: str,
        image_bytes: Optional[bytes] = None,
        image_format: str = "jpeg",
        model_id: Optional[str] = None,
    ) -> BedrockResponse:
        """Invoke Teacher Vision model (gpt-5.6-terra / high-capacity vision model)."""
        mid = model_id or settings.teacher_vision_model_id
        return await self.invoke(
            model_id=mid,
            system_prompt=(
                "You are an expert senior agronomist and verifier. Provide definitive crop identification, "
                "growth stage evaluation, and health diagnosis in strict JSON format."
            ),
            user_message=prompt,
            image_bytes=image_bytes,
            image_format=image_format,
            temperature=0.0,
        )

    async def get_embedding(
        self,
        text: str,
        model_id: Optional[str] = None,
    ) -> List[float]:
        """Generate text embedding vector using Bedrock Titan Embeddings."""
        mid = model_id or settings.embedding_model_id

        if not self.is_live:
            # Deterministic mock embedding (1024-dim)
            seed = sum(ord(c) for c in text) % 100
            return [float((i + seed) % 50) / 100.0 for i in range(1024)]

        try:
            body = json.dumps({"inputText": text})
            response = self._client.invoke_model(
                modelId=mid,
                body=body,
                contentType="application/json",
                accept="application/json",
            )
            response_body = json.loads(response["body"].read())
            return response_body.get("embedding", [])
        except Exception as e:
            logger.warning(f"Titan embedding failed ({e}); returning fallback mock vector.")
            seed = sum(ord(c) for c in text) % 100
            return [float((i + seed) % 50) / 100.0 for i in range(1024)]

    def _mock_response(self, model_id: str, user_message: str, start_time: float) -> BedrockResponse:
        """Produce structured, deterministic mock responses for testing and zero-cost dev."""
        msg_lower = user_message.lower()

        # Planner mock
        if "plan" in msg_lower or "claim" in msg_lower:
            mock_data = [
                {"claim_id": "c1", "claim_type": "GEO.PARCEL", "harm": "high", "depends_on": []},
                {"claim_id": "c2", "claim_type": "REG.OWNER", "harm": "high", "depends_on": ["c1"]},
                {"claim_id": "c3", "claim_type": "MEDIA.PHOTO", "harm": "high", "depends_on": ["c1"]},
                {"claim_id": "c4", "claim_type": "VIS.CROP", "harm": "medium", "depends_on": ["c3"]},
                {"claim_id": "c5", "claim_type": "ADV.FERTILIZER", "harm": "critical", "depends_on": ["c4"]},
            ]
            text = json.dumps(mock_data)

        # Vision mock
        elif "crop" in msg_lower or "stage" in msg_lower or "condition" in msg_lower:
            mock_data = {
                "label": "paddy",
                "confidence": 0.78,
                "growth_stage": "tillering",
                "condition": "healthy",
                "rationale": "Distinct emerald green narrow leaf blades characteristic of Oryza sativa in vegetative stage.",
                "model": model_id,
            }
            text = json.dumps(mock_data)

        # Binder verification mock
        elif "bind" in msg_lower or "verify" in msg_lower:
            mock_data = {
                "decision": "STAMP",
                "confidence": 0.95,
                "reason": "All cross-modal predicates satisfied: GIS parcel matches GPS, and advisory matches identified crop.",
            }
            text = json.dumps(mock_data)

        else:
            text = json.dumps({"status": "acknowledged", "model": model_id})

        latency_ms = int((time.time() - start_time) * 1000) or 50
        in_tokens = max(1, len(user_message) // 4)
        out_tokens = max(1, len(text) // 4)
        cost = self.calculate_cost(model_id, in_tokens, out_tokens)

        return BedrockResponse(
            text=text,
            model_id=model_id,
            input_tokens=in_tokens,
            output_tokens=out_tokens,
            latency_ms=latency_ms,
            cost_usd=cost,
            raw_response={"mock": True},
            is_mock=True,
        )


# Singleton instance
bedrock_client = BedrockClient()

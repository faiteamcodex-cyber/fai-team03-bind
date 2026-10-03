"""AWS Bedrock client wrapper supporting Text, Multimodal (Vision), and Embeddings.

Supports both MOCK mode (for zero-cost local dev) and LIVE mode via AWS Bedrock boto3 SDK.
"""

import base64
import json
import logging
from typing import Dict, Any, List, Optional

from app.config import settings

logger = logging.getLogger(__name__)


class BedrockClient:
    """Wrapper around AWS Bedrock Runtime APIs (Converse & InvokeModel).
    
    Supports:
    - Text Generation (Planner / Binder / Reasoning)
    - Multimodal Vision (VLM B / Student V image analysis)
    - Text Embeddings (Titan Text V2)
    """

    def __init__(self):
        self._client = None
        if not settings.use_mocks:
            try:
                import boto3
                creds = settings.get_aws_credentials()
                # Filter out None values
                kwargs = {k: v for k, v in creds.items() if v is not None}
                if settings.aws_profile:
                    kwargs["profile_name"] = settings.aws_profile
                session = boto3.Session(**kwargs)
                self._client = session.client("bedrock-runtime")
                logger.info(f"Bedrock client initialized in region {kwargs.get('region_name', settings.aws_region)}")
            except Exception as e:
                logger.error(f"Failed to initialize Bedrock client: {e}")
                self._client = None

    async def invoke(
        self,
        model_id: str,
        system_prompt: str,
        user_message: str,
        max_tokens: int = 2048,
        temperature: float = 0.1,
        image_bytes: Optional[bytes] = None,
        image_format: str = "jpeg",
    ) -> str:
        """Invoke a Bedrock model (Text or Vision) and return text output."""
        if settings.use_mocks or self._client is None:
            logger.info(f"[MOCK] Bedrock invoke model={model_id}")
            return self._mock_response(model_id, user_message)

        try:
            # 1. Try standardized Converse API
            content_blocks = []
            if image_bytes:
                content_blocks.append({
                    "image": {
                        "format": image_format.lower(),
                        "source": {"bytes": image_bytes}
                    }
                })
            content_blocks.append({"text": user_message})

            messages = [{"role": "user", "content": content_blocks}]
            system_list = [{"text": system_prompt}] if system_prompt else []

            try:
                response = self._client.converse(
                    modelId=model_id,
                    messages=messages,
                    system=system_list,
                    inferenceConfig={
                        "maxTokens": max_tokens,
                        "temperature": temperature
                    }
                )
                output_text = response["output"]["message"]["content"][0]["text"]
                return output_text

            except Exception as conv_err:
                logger.warning(f"Converse API failed for {model_id}, trying invoke_model: {conv_err}")
                return await self._fallback_invoke_model(
                    model_id, system_prompt, user_message, max_tokens, temperature, image_bytes, image_format
                )

        except Exception as e:
            logger.error(f"Bedrock invocation failed for {model_id}: {e}")
            raise

    async def _fallback_invoke_model(
        self,
        model_id: str,
        system_prompt: str,
        user_message: str,
        max_tokens: int,
        temperature: float,
        image_bytes: Optional[bytes] = None,
        image_format: str = "jpeg",
    ) -> str:
        """Fallback raw invoke_model call for custom payload formats."""
        if "titan" in model_id.lower():
            payload = {
                "inputText": f"{system_prompt}\n\n{user_message}",
                "textGenerationConfig": {"maxTokenCount": max_tokens, "temperature": temperature}
            }
        else:
            payload = {
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                "max_tokens": max_tokens,
                "temperature": temperature
            }

        response = self._client.invoke_model(
            modelId=model_id,
            body=json.dumps(payload),
            contentType="application/json",
            accept="application/json"
        )
        body = json.loads(response["body"].read())
        
        if "content" in body:
            return body["content"][0]["text"]
        elif "output" in body:
            return body["output"]["message"]["content"][0]["text"]
        elif "results" in body:
            return body["results"][0]["outputText"]
        return json.dumps(body)

    async def get_embedding(self, text: str, model_id: str = "amazon.titan-text-v2") -> List[float]:
        """Generate text embedding vector using Bedrock Titan Embeddings."""
        if settings.use_mocks or self._client is None:
            # Return dummy 1024-dim vector in mock mode
            return [0.01 * (i % 50) for i in range(1024)]

        try:
            body = json.dumps({"inputText": text})
            response = self._client.invoke_model(
                modelId=model_id,
                body=body,
                contentType="application/json",
                accept="application/json"
            )
            response_body = json.loads(response["body"].read())
            return response_body.get("embedding", [])
        except Exception as e:
            logger.error(f"Failed to generate embedding with {model_id}: {e}")
            raise

    def _mock_response(self, model_id: str, user_message: str) -> str:
        """Return structured mock responses for BIND pipeline."""
        if "planner" in user_message.lower() or "claims" in user_message.lower():
            return json.dumps([
                {"claim_id": "c1", "claim_type": "GEO.BOUNDARY_MATCH", "required_exhibits": ["ex_gis"]},
                {"claim_id": "c2", "claim_type": "REG.OWNER_TITLE", "required_exhibits": ["ex_chitta"]},
            ])
        return "[]"

"""Verification script to test AWS Bedrock connectivity and credentials.
Part of Dinesh Kumar's Phase 1 deliverable.
"""

import os
import sys
import boto3
from dotenv import load_dotenv

load_dotenv()

def test_connectivity():
    print("=" * 60)
    print("AWS Bedrock & STS Connectivity Verification")
    print("=" * 60)

    region = os.getenv("AWS_DEFAULT_REGION", "ap-south-1")
    session = boto3.Session(
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
        aws_session_token=os.getenv("AWS_SESSION_TOKEN"),
        region_name=region
    )

    # 1. Test STS Caller Identity
    try:
        sts = session.client("sts")
        identity = sts.get_caller_identity()
        print(f"[OK] STS Authentication Successful!")
        print(f"     Account: {identity.get('Account')}")
        print(f"     Arn:     {identity.get('Arn')}")
        print(f"     UserId:  {identity.get('UserId')}")
    except Exception as e:
        print(f"[FAIL] STS Caller Identity failed: {e}")
        return

    # 2. Test Bedrock Control Plane (List Foundation Models)
    try:
        bedrock = session.client("bedrock", region_name=region)
        models = bedrock.list_foundation_models()
        model_summaries = models.get("modelSummaries", [])
        print(f"\n[OK] Bedrock list_foundation_models() successful! Found {len(model_summaries)} models.")
        
        # Check for Titan, Nova, etc.
        relevant_models = [
            m["modelId"] for m in model_summaries
            if any(k in m["modelId"].lower() for k in ["nova", "titan", "claude", "llama"])
        ]
        print(f"     Relevant models available (sample):")
        for m_id in relevant_models[:10]:
            print(f"       - {m_id}")
    except Exception as e:
        print(f"[NOTE] Bedrock list_foundation_models: {e}")

    # 3. Test Bedrock Runtime (Converse / Embeddings)
    try:
        runtime = session.client("bedrock-runtime", region_name=region)
        print("\n[INFO] Testing Bedrock Runtime invocation...")
        
        # Test Titan text embedding
        embed_model_id = os.getenv("TITAN_EMBEDDING_MODEL_ID", "amazon.titan-embed-text-v2:0")
        try:
            import json
            response = runtime.invoke_model(
                modelId=embed_model_id,
                body=json.dumps({"inputText": "Testing Bedrock connectivity for BIND project."}),
                contentType="application/json",
                accept="application/json"
            )
            resp_body = json.loads(response["body"].read())
            embedding = resp_body.get("embedding", [])
            print(f"[OK] Titan Embeddings ({embed_model_id}) succeeded! Dimension: {len(embedding)}")
        except Exception as embed_err:
            print(f"[NOTE] Titan embedding invocation returned: {embed_err}")

        # Test Text / Vision Model
        test_model = os.getenv("BIND_STUDENT_VISION_MODEL_ID", "apac.amazon.nova-lite-v1:0")
        try:
            conv_resp = runtime.converse(
                modelId=test_model,
                messages=[{"role": "user", "content": [{"text": "Reply with 'OK'."}]}],
                inferenceConfig={"maxTokens": 10, "temperature": 0.0}
            )
            output = conv_resp["output"]["message"]["content"][0]["text"]
            print(f"[OK] Converse with {test_model} succeeded! Output: {output.strip()}")
        except Exception as conv_err:
            print(f"[NOTE] Converse with {test_model} returned: {conv_err}")

    except Exception as e:
        print(f"[FAIL] Bedrock Runtime test failed: {e}")

    print("\n" + "=" * 60)
    print("Connectivity test finished.")
    print("=" * 60)

if __name__ == "__main__":
    test_connectivity()

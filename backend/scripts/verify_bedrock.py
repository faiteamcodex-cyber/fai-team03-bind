"""AWS Bedrock Model Access & Verification Script for BIND (Team 03).

This script:
1. Loads AWS Credentials directly from .env file.
2. Checks AWS STS Identity (Account & Role ARN).
3. Lists Foundation Models & Inference Profiles in AWS Bedrock.
4. Performs live test invocations on:
   - APAC Nova Micro (Fast LLM)
   - APAC Nova Lite (Multimodal Student V)
   - Titan Text Embeddings V2 (RAG Embeddings)
   - GPT-5.6 Luna & Terra (Planner & Teacher)
"""

import sys
import os
import json
import time
from typing import Dict, Any

# Ensure backend directory is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.config import settings


def verify_aws_credentials(session) -> bool:
    print("\n" + "=" * 60)
    print(" 1. AWS CREDENTIALS & ACCOUNT VERIFICATION")
    print("=" * 60)
    try:
        sts = session.client("sts")
        identity = sts.get_caller_identity()
        print(f"  [SUCCESS] Connected to AWS Account:")
        print(f"    - Account ID : {identity.get('Account')}")
        print(f"    - User / Role: {identity.get('Arn')}")
        print(f"    - Region    : {session.region_name}")
        return True
    except Exception as e:
        print(f"  [FAILED] Could not verify AWS credentials!")
        print(f"    Error: {e}")
        return False


def test_model_invocation(runtime_client, name: str, model_id: str, prompt: str = "Hello, system health check.") -> Dict[str, Any]:
    print(f"\n  [TESTING] {name} ({model_id}) ...")
    start_time = time.time()
    
    # Handle Embeddings separately
    if "embed" in model_id.lower():
        try:
            body = json.dumps({"inputText": prompt})
            res = runtime_client.invoke_model(
                modelId=model_id,
                body=body,
                contentType="application/json",
                accept="application/json"
            )
            elapsed = round((time.time() - start_time) * 1000, 2)
            data = json.loads(res["body"].read())
            vec_dim = len(data.get("embedding", []))
            print(f"    -> SUCCESS via invoke_model ({elapsed} ms)")
            print(f"    -> Vector Dimension: {vec_dim}")
            return {"status": "SUCCESS", "method": "invoke_model", "latency_ms": elapsed, "output": f"Vector dim: {vec_dim}"}
        except Exception as e:
            elapsed = round((time.time() - start_time) * 1000, 2)
            print(f"    -> FAILED ({elapsed} ms): {e}")
            return {"status": "FAILED", "error": str(e), "latency_ms": elapsed}

    # Try Converse API for text/vision models
    try:
        response = runtime_client.converse(
            modelId=model_id,
            messages=[{"role": "user", "content": [{"text": prompt}]}],
            inferenceConfig={"maxTokens": 60, "temperature": 0.1}
        )
        elapsed = round((time.time() - start_time) * 1000, 2)
        text_out = response["output"]["message"]["content"][0]["text"].strip()
        print(f"    -> SUCCESS via converse API ({elapsed} ms)")
        print(f"    -> Response: {text_out[:100]}")
        return {"status": "SUCCESS", "method": "converse", "latency_ms": elapsed, "output": text_out}
    except Exception as e:
        elapsed = round((time.time() - start_time) * 1000, 2)
        print(f"    -> FAILED ({elapsed} ms): {e}")
        return {"status": "FAILED", "error": str(e), "latency_ms": elapsed}


def main():
    import boto3
    
    print("=" * 60)
    print(" BIND CROSS-MODAL RUNTIME - AWS BEDROCK VERIFICATION TOOL")
    print("=" * 60)

    # Initialize Boto3 session with credentials loaded from .env
    creds = settings.get_aws_credentials()
    kwargs = {k: v for k, v in creds.items() if v is not None}
    if settings.aws_profile:
        kwargs["profile_name"] = settings.aws_profile
    session = boto3.Session(**kwargs)

    # Step 1: Verify Credentials
    if not verify_aws_credentials(session):
        print("\n Aborting model tests due to missing/invalid AWS credentials.")
        return

    # Step 2: Test Live Model Invocations
    print("\n" + "=" * 60)
    print(" 2. LIVE MODEL INVOCATION TESTS")
    print("=" * 60)

    bedrock_runtime = session.client("bedrock-runtime")
    
    models_to_test = [
        ("APAC Nova Micro", "apac.amazon.nova-micro-v1:0"),
        ("APAC Nova Lite (Student V)", "apac.amazon.nova-lite-v1:0"),
        ("Titan Text Embeddings V2", "amazon.titan-embed-text-v2:0"),
        ("GPT-5.6 Luna (Planner - IN)", "in.openai.gpt-5.6-luna"),
        ("GPT-5.6 Terra (Teacher - IN)", "in.openai.gpt-5.6-terra"),
    ]

    results = {}
    for name, mid in models_to_test:
        res = test_model_invocation(bedrock_runtime, name, mid)
        results[name] = res

    # Step 3: Summary Report
    print("\n" + "=" * 60)
    print(" 3. VERIFICATION SUMMARY")
    print("=" * 60)
    
    working_count = 0
    for name, res in results.items():
        status = res["status"]
        if status == "SUCCESS":
            working_count += 1
            print(f"  [OK]   {name:<30}: SUCCESS ({res['latency_ms']} ms)")
        else:
            err_msg = res.get('error', '')
            if 'AccessDeniedException' in err_msg:
                short_err = "AccessDenied (IAM Permission pending)"
            else:
                short_err = err_msg[:50]
            print(f"  [WARN] {name:<30}: {short_err}")

    print(f"\nSummary: {working_count}/{len(models_to_test)} models active and responding.")


if __name__ == "__main__":
    main()

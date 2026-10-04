import os
import sys
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv
from pydantic_settings import BaseSettings

# Ensure backend/src is in sys.path for bind_data package resolution
_src_path = str(Path(__file__).resolve().parent.parent / "src")
if _src_path not in sys.path:
    sys.path.insert(0, _src_path)

# Find and load .env file with override=True so .env takes precedence over OS environment variables
possible_env_paths = [
    Path.cwd() / ".env",
    Path.cwd() / "scripts" / ".env",
    Path(__file__).resolve().parent.parent / ".env",
    Path(__file__).resolve().parent.parent / "scripts" / ".env",
    Path(__file__).resolve().parent.parent.parent / ".env",
]

for env_path in possible_env_paths:
    if env_path.exists():
        # Force load into os.environ with override=True
        load_dotenv(dotenv_path=env_path, override=True)
        break


class Settings(BaseSettings):
    """Application configuration loaded from .env file or environment variables."""
    # AWS Credentials & Settings
    aws_access_key_id: Optional[str] = None
    aws_secret_access_key: Optional[str] = None
    aws_session_token: Optional[str] = None
    aws_region: str = "ap-south-1"
    aws_profile: Optional[str] = None
    
    # Bedrock Model IDs (Inference Profiles)
    planner_model_id: str = "apac.amazon.nova-micro-v1:0"  # Fast LLM Planner (or in.openai.gpt-5.6-luna when IAM granted)
    teacher_vision_model_id: str = "apac.amazon.nova-lite-v1:0"  # Vision Teacher (or in.openai.gpt-5.6-terra when IAM granted)
    student_vision_model_id: str = "apac.amazon.nova-lite-v1:0"  # Student V Multimodal
    embedding_model_id: str = "amazon.titan-embed-text-v2:0"  # RAG embeddings
    
    # Budget
    max_docket_cost_usd: float = 0.08
    max_docket_latency_ms: int = 12000
    student_confidence_threshold: float = 0.65
    
    # S3
    dataset_bucket: str = "fai-tce-team03-datasets"
    results_bucket: str = "fai-tce-team03-results"
    
    # Application
    debug: bool = True
    use_mocks: bool = False  # Default to live when credentials present, or controlled by .env
    
    def get_aws_credentials(self) -> dict:
        """Retrieve AWS credentials loaded directly from .env file into os.environ."""
        key_id = os.getenv("AWS_ACCESS_KEY_ID") or self.aws_access_key_id
        secret_key = os.getenv("AWS_SECRET_ACCESS_KEY") or self.aws_secret_access_key
        session_token = os.getenv("AWS_SESSION_TOKEN") or self.aws_session_token
        region = os.getenv("AWS_DEFAULT_REGION") or os.getenv("AWS_REGION") or self.aws_region
        
        return {
            "aws_access_key_id": key_id,
            "aws_secret_access_key": secret_key,
            "aws_session_token": session_token,
            "region_name": region,
        }

    model_config = {
        "env_prefix": "BIND_",
        "env_file": ".env",
        "extra": "ignore"
    }


settings = Settings()

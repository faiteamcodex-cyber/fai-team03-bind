"""Safe export and restore of ChromaDB state to and from Amazon S3."""

import os
import tarfile
import shutil
import logging
from pathlib import Path
from typing import Optional, Dict, Any

from bind_data.ingestion.s3_uploader import create_boto3_session

logger = logging.getLogger(__name__)


def export_chroma_state_to_s3(
    local_chroma_dir: Path,
    state_bucket: str = "fai-tce-team03-app-state",
    version_tag: str = "v1",
    s3_client: Optional[Any] = None,
    dry_run: bool = False,
    aws_profile: Optional[str] = None,
    aws_region: str = "ap-south-1",
) -> Dict[str, Any]:
    """
    Package local persistent ChromaDB directory into a tarball and upload to S3 application-state bucket.
    Target key format: chroma-state/{version_tag}/chroma_db_{version_tag}.tar.gz
    """
    local_dir = Path(local_chroma_dir).resolve()
    if not local_dir.exists() or not local_dir.is_dir():
        raise FileNotFoundError(f"Chroma directory does not exist: {local_dir}")

    s3_key = f"chroma-state/{version_tag}/chroma_db_{version_tag}.tar.gz"
    tarball_path = local_dir.parent / f"chroma_db_{version_tag}.tar.gz"

    logger.info(f"Packaging {local_dir} into {tarball_path}...")
    with tarfile.open(tarball_path, "w:gz") as tar:
        tar.add(local_dir, arcname=local_dir.name)

    tar_size = tarball_path.stat().st_size

    result = {
        "status": "SIMULATED_SUCCESS" if dry_run else "PENDING",
        "dry_run": dry_run,
        "local_tarball": str(tarball_path),
        "tarball_size_bytes": tar_size,
        "state_bucket": state_bucket,
        "s3_key": s3_key,
        "s3_uri": f"s3://{state_bucket}/{s3_key}",
        "version_tag": version_tag,
    }

    if dry_run:
        logger.info(f"[DRY-RUN] Would upload {tarball_path} ({tar_size} bytes) -> s3://{state_bucket}/{s3_key}")
        # Clean up local tarball in dry-run
        if tarball_path.exists():
            tarball_path.unlink()
        return result

    try:
        if s3_client is None:
            session = create_boto3_session(profile=aws_profile, region=aws_region)
            s3_client = session.client("s3")

        logger.info(f"Uploading Chroma state package to s3://{state_bucket}/{s3_key}...")
        s3_client.upload_file(
            Filename=str(tarball_path),
            Bucket=state_bucket,
            Key=s3_key,
        )
        result["status"] = "UPLOADED"
        logger.info(f"Successfully uploaded Chroma state to s3://{state_bucket}/{s3_key}")
    except Exception as e:
        result["status"] = "FAILED"
        result["error"] = str(e)
        logger.error(f"Failed to upload Chroma state to S3: {e}")
        raise
    finally:
        # Clean up local temporary tarball
        if tarball_path.exists():
            tarball_path.unlink()

    return result


def restore_chroma_state_from_s3(
    target_chroma_dir: Path,
    state_bucket: str = "fai-tce-team03-app-state",
    version_tag: str = "v1",
    s3_client: Optional[Any] = None,
    aws_profile: Optional[str] = None,
    aws_region: str = "ap-south-1",
) -> Path:
    """
    Download ChromaDB package from S3 state bucket and extract into target local directory.
    """
    target_dir = Path(target_chroma_dir).resolve()
    target_dir.parent.mkdir(parents=True, exist_ok=True)
    
    s3_key = f"chroma-state/{version_tag}/chroma_db_{version_tag}.tar.gz"
    temp_tarball = target_dir.parent / f"download_{version_tag}.tar.gz"

    if s3_client is None:
        session = create_boto3_session(profile=aws_profile, region=aws_region)
        s3_client = session.client("s3")

    logger.info(f"Downloading Chroma state from s3://{state_bucket}/{s3_key} to {temp_tarball}...")
    s3_client.download_file(
        Bucket=state_bucket,
        Key=s3_key,
        Filename=str(temp_tarball),
    )

    logger.info(f"Extracting Chroma archive into {target_dir.parent}...")
    with tarfile.open(temp_tarball, "r:gz") as tar:
        tar.extractall(path=str(target_dir.parent))

    if temp_tarball.exists():
        temp_tarball.unlink()

    logger.info(f"Chroma state restored successfully to {target_dir}")
    return target_dir

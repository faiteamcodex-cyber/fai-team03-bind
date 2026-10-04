"""S3 multipart uploader using boto3 TransferConfig."""

import os
import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional

from bind_data.config import IngestionConfig, load_ingestion_config
from bind_data.ingestion.manifest import generate_manifest

logger = logging.getLogger(__name__)


def create_boto3_session(profile: Optional[str] = None, region: Optional[str] = None):
    """Create a Boto3 Session using local CLI profile or environment credentials."""
    import boto3
    kwargs = {}
    if profile:
        kwargs["profile_name"] = profile
    if region:
        kwargs["region_name"] = region
    return boto3.Session(**kwargs)


class S3DatasetUploader:
    """Manages validation and multipart upload of datasets to Amazon S3."""

    def __init__(
        self,
        config: Optional[IngestionConfig] = None,
        s3_client: Optional[Any] = None,
    ):
        self.config = config or load_ingestion_config()
        self._s3_client = s3_client

    def _get_s3_client(self):
        if self._s3_client is not None:
            return self._s3_client
            
        import boto3
        session = create_boto3_session(
            profile=self.config.aws_profile,
            region=self.config.aws_region
        )
        self._s3_client = session.client("s3")
        return self._s3_client

    def _get_transfer_config(self):
        from boto3.s3.transfer import TransferConfig
        return TransferConfig(
            multipart_threshold=self.config.multipart_threshold_bytes,
            multipart_chunksize=self.config.multipart_chunksize_bytes,
            max_concurrency=self.config.max_concurrency,
            use_threads=True,
        )

    def upload_file(
        self,
        local_path: Path,
        bucket: str,
        s3_key: str,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """Upload a single file to S3 with TransferConfig or simulate if dry_run=True."""
        local_path = Path(local_path).resolve()
        size_bytes = local_path.stat().st_size
        
        result: Dict[str, Any] = {
            "local_path": str(local_path),
            "bucket": bucket,
            "s3_key": s3_key,
            "size_bytes": size_bytes,
            "dry_run": dry_run,
            "status": "PENDING",
            "etag": None,
            "error": None,
        }

        if dry_run:
            result["status"] = "SIMULATED_SUCCESS"
            logger.info(f"[DRY-RUN] Would upload {local_path.name} ({size_bytes} bytes) -> s3://{bucket}/{s3_key}")
            return result

        try:
            s3 = self._get_s3_client()
            transfer_config = self._get_transfer_config()
            
            logger.info(f"Uploading {local_path.name} ({size_bytes} bytes) -> s3://{bucket}/{s3_key}...")
            s3.upload_file(
                Filename=str(local_path),
                Bucket=bucket,
                Key=s3_key,
                Config=transfer_config,
            )
            
            # Fetch head object to retrieve ETag
            try:
                head = s3.head_object(Bucket=bucket, Key=s3_key)
                result["etag"] = head.get("ETag", "").strip('"')
            except Exception:
                pass
                
            result["status"] = "UPLOADED"
            logger.info(f"Successfully uploaded s3://{bucket}/{s3_key} (ETag: {result['etag']})")
        except Exception as e:
            result["status"] = "FAILED"
            result["error"] = str(e)
            logger.error(f"Failed to upload {local_path} to s3://{bucket}/{s3_key}: {e}")

        return result

    def upload_dataset(
        self,
        manifest: Dict[str, Any],
        bucket: Optional[str] = None,
        dry_run: bool = True,
    ) -> Dict[str, Any]:
        """
        Upload all valid files from a manifest and upload the manifest itself.
        Refuses to upload if any invalid files exist unless all_valid is true.
        """
        target_bucket = bucket or self.config.data_bucket
        
        if not manifest.get("all_valid", False):
            raise ValueError(
                f"Cannot upload dataset: Manifest contains {manifest.get('invalid_files', 0)} invalid files. "
                f"Please fix validation errors before uploading."
            )

        upload_results = []
        uploaded_count = 0
        failed_count = 0
        total_bytes = 0

        for file_info in manifest.get("files", []):
            if not file_info.get("is_valid", False):
                continue
                
            local_path = Path(file_info["absolute_path"])
            s3_key = file_info["s3_target_key"]
            
            res = self.upload_file(
                local_path=local_path,
                bucket=target_bucket,
                s3_key=s3_key,
                dry_run=dry_run,
            )
            upload_results.append(res)
            
            if res["status"] in ("UPLOADED", "SIMULATED_SUCCESS"):
                uploaded_count += 1
                total_bytes += res["size_bytes"]
            else:
                failed_count += 1

        # Also upload the manifest
        timestamp_str = manifest.get("timestamp", "").replace(":", "-").replace(".", "-")
        manifest_key = f"manifests/{timestamp_str}-manifest.json"
        
        manifest_upload = {
            "bucket": target_bucket,
            "s3_key": manifest_key,
            "dry_run": dry_run,
            "status": "SIMULATED_SUCCESS" if dry_run else "PENDING",
        }
        
        if not dry_run and failed_count == 0:
            try:
                s3 = self._get_s3_client()
                manifest_json = json.dumps(manifest, indent=2)
                s3.put_object(
                    Bucket=target_bucket,
                    Key=manifest_key,
                    Body=manifest_json.encode("utf-8"),
                    ContentType="application/json",
                )
                manifest_upload["status"] = "UPLOADED"
            except Exception as e:
                manifest_upload["status"] = "FAILED"
                manifest_upload["error"] = str(e)
                failed_count += 1

        return {
            "bucket": target_bucket,
            "dry_run": dry_run,
            "total_files": len(upload_results),
            "uploaded_files": uploaded_count,
            "failed_files": failed_count,
            "total_bytes": total_bytes,
            "manifest_s3_key": manifest_key,
            "manifest_status": manifest_upload["status"],
            "file_results": upload_results,
        }

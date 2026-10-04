"""Dataset S3 multipart upload CLI script."""

import sys
import os
import json
import argparse
import logging
from pathlib import Path

# Ensure backend/src and backend are in sys.path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir / "src"))
sys.path.insert(0, str(backend_dir))

from bind_data.config import IngestionConfig
from bind_data.ingestion.manifest import generate_manifest, save_manifest
from bind_data.ingestion.s3_uploader import S3DatasetUploader

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("upload_dataset")


def main():
    parser = argparse.ArgumentParser(description="Upload validated dataset to AWS S3 using multipart TransferConfig.")
    parser.add_argument(
        "--input", "-i",
        type=str,
        required=True,
        help="Input dataset directory path."
    )
    parser.add_argument(
        "--bucket", "-b",
        type=str,
        default="fai-tce-team03-datasets",
        help="Target S3 bucket name (default: fai-tce-team03-datasets)."
    )
    parser.add_argument(
        "--manifest", "-m",
        type=str,
        default=None,
        help="Path to pre-generated manifest JSON file (optional)."
    )
    parser.add_argument(
        "--profile", "-p",
        type=str,
        default=None,
        help="AWS CLI profile name (e.g. fai-team03)."
    )
    parser.add_argument(
        "--region", "-r",
        type=str,
        default="ap-south-1",
        help="AWS region (default: ap-south-1)."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate upload without transferring real data to AWS."
    )
    parser.add_argument(
        "--confirm",
        action="store_true",
        help="Acknowledge and confirm real S3 transfer (required for non-dry-run)."
    )

    args = parser.parse_args()
    input_dir = Path(args.input).resolve()

    if not input_dir.exists() or not input_dir.is_dir():
        logger.error(f"Input directory does not exist: {input_dir}")
        sys.exit(1)

    print("=" * 70)
    print(" BIND S3 DATASET UPLOADER")
    print(f" Target Bucket : s3://{args.bucket}")
    print(f" AWS Region    : {args.region}")
    print(f" AWS Profile   : {args.profile or 'default/environment'}")
    print(f" Mode          : {'DRY-RUN (Simulation)' if args.dry_run else 'LIVE UPLOAD'}")
    print("=" * 70)

    # 1. Load or Generate Manifest
    if args.manifest and Path(args.manifest).exists():
        logger.info(f"Loading existing manifest: {args.manifest}")
        with open(args.manifest, "r", encoding="utf-8") as f:
            manifest = json.load(f)
    else:
        logger.info(f"Generating manifest for directory: {input_dir}...")
        manifest = generate_manifest(input_dir)
        if args.manifest:
            save_manifest(manifest, Path(args.manifest))

    # 2. Check Validation Status
    if not manifest.get("all_valid", False):
        logger.error(
            f"Validation check failed! Manifest contains {manifest.get('invalid_files', 0)} invalid files. "
            f"Cannot proceed with S3 upload."
        )
        sys.exit(1)

    # 3. Safety Confirmation Check for Real Uploads
    if not args.dry_run and not args.confirm:
        logger.error(
            "SAFETY CHECK: Real upload requested without --confirm flag! "
            "To prevent accidental data transfer, please pass --dry-run or --confirm explicitly."
        )
        sys.exit(1)

    # 4. Perform Upload
    config = IngestionConfig(
        data_bucket=args.bucket,
        aws_region=args.region,
        aws_profile=args.profile,
    )
    uploader = S3DatasetUploader(config=config)

    try:
        report = uploader.upload_dataset(
            manifest=manifest,
            bucket=args.bucket,
            dry_run=args.dry_run,
        )
    except Exception as e:
        logger.error(f"Dataset upload process failed: {e}")
        sys.exit(1)

    print("\n--- UPLOAD SUMMARY ---")
    print(f"Total Files Processed : {report['total_files']}")
    print(f"Successfully Handled  : {report['uploaded_files']}")
    print(f"Failed Transfers      : {report['failed_files']}")
    print(f"Total Bytes Uploaded  : {round(report['total_bytes'] / (1024*1024), 2)} MB")
    print(f"Manifest S3 Key       : {report['manifest_s3_key']} ({report['manifest_status']})")

    if report["failed_files"] > 0:
        print("\n[!] Errors encountered during upload:")
        for res in report["file_results"]:
            if res.get("error"):
                print(f"  * {res['s3_key']}: {res['error']}")
        sys.exit(1)
    else:
        print("\n[OK] Upload completed successfully.")
        sys.exit(0)


if __name__ == "__main__":
    main()

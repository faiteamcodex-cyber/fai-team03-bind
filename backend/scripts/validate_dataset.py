"""Dataset validation CLI script."""

import sys
import os
import argparse
import logging
from pathlib import Path

# Ensure backend/src and backend are in sys.path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir / "src"))
sys.path.insert(0, str(backend_dir))

from bind_data.ingestion.manifest import generate_manifest, save_manifest

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("validate_dataset")


def main():
    parser = argparse.ArgumentParser(description="Validate BIND agricultural dataset and generate manifest.")
    parser.add_argument(
        "--input", "-i",
        type=str,
        required=True,
        help="Input dataset root directory to inspect."
    )
    parser.add_argument(
        "--manifest", "-m",
        type=str,
        default="./artifacts/manifest.json",
        help="Output JSON manifest file path (default: ./artifacts/manifest.json)."
    )
    parser.add_argument(
        "--max-image-size-mb",
        type=float,
        default=4.0,
        help="Maximum allowed image size in MB (default: 4.0 MB)."
    )
    parser.add_argument(
        "--no-checksums",
        action="store_true",
        help="Skip computing SHA256 checksums."
    )

    args = parser.parse_args()
    input_dir = Path(args.input).resolve()
    manifest_path = Path(args.manifest).resolve()
    max_image_bytes = int(args.max_image_size_mb * 1024 * 1024)

    if not input_dir.exists() or not input_dir.is_dir():
        logger.error(f"Input directory does not exist: {input_dir}")
        sys.exit(1)

    print("=" * 70)
    print(" BIND DATASET VALIDATION PIPELINE")
    print(f" Target Directory: {input_dir}")
    print("=" * 70)

    try:
        manifest = generate_manifest(
            input_dir=input_dir,
            include_checksums=not args.no_checksums,
            max_image_size=max_image_bytes,
        )
        saved_file = save_manifest(manifest, manifest_path)
    except Exception as e:
        logger.error(f"Validation failed with exception: {e}")
        sys.exit(1)

    # Print summary report
    print("\n--- VALIDATION SUMMARY ---")
    print(f"Total Files Inspected : {manifest['total_files']}")
    print(f"Valid Files           : {manifest['valid_files']}")
    print(f"Invalid Files         : {manifest['invalid_files']}")
    print(f"Total Size            : {manifest['total_size_mb']} MB")
    print("\nCategory Breakdown:")
    for cat, count in manifest["category_counts"].items():
        print(f"  - {cat:<22}: {count}")

    if manifest["invalid_files"] > 0:
        print("\n[!] VALIDATION FAILURES DETECTED:")
        for f in manifest["files"]:
            if not f["is_valid"]:
                print(f"  * {f['relative_path']}: {', '.join(f['errors'])}")
        print(f"\nManifest saved to: {saved_file}")
        print("[FAILED] Dataset validation failed. Non-zero exit code returned.")
        sys.exit(1)
    else:
        print(f"\n[OK] All {manifest['total_files']} files validated successfully.")
        print(f"Manifest saved to: {saved_file}")
        sys.exit(0)


if __name__ == "__main__":
    main()

"""DynamoDB Land Records mock table seed script."""

import sys
import os
import json
import argparse
import logging
from pathlib import Path
from typing import Dict, Any, List

# Ensure backend/src and backend are in sys.path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir / "src"))
sys.path.insert(0, str(backend_dir))

from bind_data.ingestion.s3_uploader import create_boto3_session

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("seed_land_records")


def validate_record(record: Dict[str, Any], idx: int) -> List[str]:
    """Validate land record dictionary fields."""
    errors = []
    if not isinstance(record, dict):
        errors.append(f"Record at index {idx} is not a valid JSON object.")
        return errors
        
    survey_number = record.get("survey_number")
    if not survey_number or not str(survey_number).strip():
        errors.append(f"Record at index {idx} is missing mandatory partition key 'survey_number'.")
    return errors


def seed_records(
    records: List[Dict[str, Any]],
    table_name: str = "fai-tce-team03-land-records",
    profile: str = None,
    region: str = "ap-south-1",
    dry_run: bool = False,
    dynamodb_resource: Any = None,
) -> Dict[str, Any]:
    """
    Idempotently write land records into DynamoDB table using batch_writer.
    """
    total = len(records)
    valid_records = []
    validation_errors = []

    for idx, rec in enumerate(records):
        errs = validate_record(rec, idx)
        if errs:
            validation_errors.extend(errs)
        else:
            # Ensure survey_number is string
            cleaned = dict(rec)
            cleaned["survey_number"] = str(cleaned["survey_number"]).strip()
            # Convert float area to string or Decimal if necessary for DynamoDB
            valid_records.append(cleaned)

    if validation_errors:
        raise ValueError(f"Validation failed for seed records:\n" + "\n".join(validation_errors))

    result = {
        "table_name": table_name,
        "region": region,
        "dry_run": dry_run,
        "total_records": total,
        "written_records": 0,
        "errors": [],
    }

    if dry_run:
        logger.info(f"[DRY-RUN] Validated {len(valid_records)} records. Would write to DynamoDB table '{table_name}'.")
        for r in valid_records:
            logger.info(f"  [DRY-RUN] Record survey_number={r['survey_number']} owner={r.get('owner_name')}")
        result["written_records"] = len(valid_records)
        return result

    try:
        if dynamodb_resource is None:
            session = create_boto3_session(profile=profile, region=region)
            dynamodb_resource = session.resource("dynamodb")

        table = dynamodb_resource.Table(table_name)
        
        # Batch write items idempotently
        with table.batch_writer() as batch:
            for rec in valid_records:
                # Decimal conversions for floats in boto3 dynamo
                from decimal import Decimal
                dynamo_rec = json.loads(json.dumps(rec), parse_float=Decimal)
                batch.put_item(Item=dynamo_rec)
                result["written_records"] += 1
                logger.info(f"Written survey_number: {rec['survey_number']} ({rec.get('owner_name')})")

    except Exception as e:
        logger.error(f"Failed writing records to DynamoDB table '{table_name}': {e}")
        result["errors"].append(str(e))
        raise

    return result


def main():
    parser = argparse.ArgumentParser(description="Seed mock land records into DynamoDB table.")
    parser.add_argument(
        "--fixtures", "-f",
        type=str,
        default="./data/fixtures/land_records.json",
        help="Path to land records JSON fixture file (default: ./data/fixtures/land_records.json)."
    )
    parser.add_argument(
        "--table-name", "-t",
        type=str,
        default="fai-tce-team03-land-records",
        help="DynamoDB table name (default: fai-tce-team03-land-records)."
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
        help="Simulate seeding without modifying DynamoDB."
    )
    parser.add_argument(
        "--confirm",
        action="store_true",
        help="Explicit confirmation to write to live AWS DynamoDB."
    )

    args = parser.parse_args()
    fixture_path = Path(args.fixtures).resolve()

    if not fixture_path.exists():
        logger.error(f"Fixture file not found: {fixture_path}")
        sys.exit(1)

    with open(fixture_path, "r", encoding="utf-8") as f:
        records = json.load(f)

    print("=" * 70)
    print(" BIND DYNAMODB LAND RECORDS SEEDER")
    print(f" Fixture File  : {fixture_path}")
    print(f" Table Name    : {args.table_name}")
    print(f" Region        : {args.region}")
    print(f" Profile       : {args.profile or 'default/environment'}")
    print(f" Mode          : {'DRY-RUN (Simulation)' if args.dry_run else 'LIVE SEED'}")
    print("=" * 70)

    if not args.dry_run and not args.confirm:
        logger.error("SAFETY CHECK: Real DynamoDB write requested without --confirm flag! Pass --dry-run or --confirm explicitly.")
        sys.exit(1)

    try:
        res = seed_records(
            records=records,
            table_name=args.table_name,
            profile=args.profile,
            region=args.region,
            dry_run=args.dry_run,
        )
        print(f"\n[OK] Successfully processed {res['written_records']} records for table '{args.table_name}'.")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Seeding failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

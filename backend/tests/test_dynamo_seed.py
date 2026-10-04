"""Unit tests for DynamoDB Land Records seed script."""

import json
from pathlib import Path
import pytest
from moto import mock_aws
import boto3

from scripts.seed_land_records import validate_record, seed_records


def test_validate_record():
    valid = {
        "survey_number": "202/55",
        "owner_name": "Ramasamy S.",
        "village": "Kadambur"
    }
    assert len(validate_record(valid, 0)) == 0

    invalid_missing_key = {
        "owner_name": "Lakshmi K."
    }
    errs = validate_record(invalid_missing_key, 1)
    assert len(errs) > 0
    assert "missing mandatory partition key" in errs[0]


def test_fixture_file_integrity():
    fixture_path = Path(__file__).resolve().parent.parent / "data" / "fixtures" / "land_records.json"
    assert fixture_path.exists()
    
    with open(fixture_path, "r", encoding="utf-8") as f:
        records = json.load(f)
        
    assert isinstance(records, list)
    assert len(records) >= 4
    for idx, rec in enumerate(records):
        errs = validate_record(rec, idx)
        assert len(errs) == 0


@mock_aws
def test_seed_records_dry_run_and_live():
    records = [
        {"survey_number": "202/55", "owner_name": "Ramasamy S.", "extent_acres": 2.5},
        {"survey_number": "202/54", "owner_name": "Lakshmi K.", "extent_acres": 3.1},
    ]

    # 1. Test Dry-Run
    dry_res = seed_records(records, table_name="test-table", dry_run=True)
    assert dry_res["dry_run"] is True
    assert dry_res["written_records"] == 2

    # 2. Test Live DynamoDB write via moto
    dynamodb = boto3.resource("dynamodb", region_name="ap-south-1")
    dynamodb.create_table(
        TableName="fai-tce-team03-land-records",
        KeySchema=[{"AttributeName": "survey_number", "KeyType": "HASH"}],
        AttributeDefinitions=[{"AttributeName": "survey_number", "AttributeType": "S"}],
        BillingMode="PAY_PER_REQUEST",
    )

    live_res = seed_records(
        records=records,
        table_name="fai-tce-team03-land-records",
        dynamodb_resource=dynamodb,
        dry_run=False,
    )
    assert live_res["written_records"] == 2

    # Verify item in table
    tbl = dynamodb.Table("fai-tce-team03-land-records")
    item = tbl.get_item(Key={"survey_number": "202/55"})
    assert item["Item"]["owner_name"] == "Ramasamy S."

"""Unit tests for GIS spatial logic and survey lookup."""

import pytest
from bind_data.gis.geojson_loader import load_geojson, normalize_feature_collection
from bind_data.gis.survey_lookup import (
    find_parcel_by_survey_number,
    SurveyLookup,
    normalize_survey_number,
    extract_survey_number_from_properties,
)
from bind_data.gis.spatial_checks import (
    check_point_in_parcel,
    check_point_in_all_parcels,
    export_selected_parcels,
    validate_coordinates,
)


def test_normalize_survey_number():
    assert normalize_survey_number(" 202/55 ") == "202/55"
    assert normalize_survey_number("145/2") == "145/2"
    assert normalize_survey_number("88/1B") == "88/1B"
    assert normalize_survey_number(None) == ""


def test_extract_survey_number_aliases():
    assert extract_survey_number_from_properties({"survey_number": "202/55"}) == "202/55"
    assert extract_survey_number_from_properties({"survey_no": "145/2"}) == "145/2"
    assert extract_survey_number_from_properties({"field_no": "88/1B"}) == "88/1B"
    assert extract_survey_number_from_properties({"survey_key": "99/3"}) == "99/3"
    assert extract_survey_number_from_properties({"unrelated_field": "123"}) is None


def test_survey_lookup_exact_and_alias(sample_geojson_data):
    features = sample_geojson_data["features"]
    lookup = SurveyLookup(features)

    # 1. Exact survey_number lookup
    res1 = lookup.lookup("202/55")
    assert res1.found is True
    assert res1.survey_number == "202/55"
    assert res1.geometry_type == "Polygon"

    # 2. Alias field_no lookup
    res2 = lookup.lookup("145/2")
    assert res2.found is True
    assert res2.survey_number == "145/2"
    assert res2.geometry_type == "MultiPolygon"

    # 3. Hyphen variant
    res3 = lookup.lookup("202-55")
    assert res3.found is True
    assert res3.survey_number == "202/55"

    # 4. Not found clean response
    res_nf = lookup.lookup("999/99")
    assert res_nf.found is False
    assert "not found" in res_nf.error.lower()


def test_point_in_polygon_interior_and_outside(sample_geojson_data):
    parcel_202_55 = sample_geojson_data["features"][0]
    # Parcel bounds: lon [79.3245, 79.3255], lat [10.7890, 10.7900]

    # Interior point
    res_in = check_point_in_parcel(
        latitude=10.7895,
        longitude=79.3250,
        parcel_geometry=parcel_202_55,
    )
    assert res_in["inside"] is True
    assert res_in["survey_number"] == "202/55"
    assert res_in["geometry_type"] == "Polygon"
    assert "Point is covered" in res_in["reason"]

    # Outside point
    res_out = check_point_in_parcel(
        latitude=10.7950,
        longitude=79.3300,
        parcel_geometry=parcel_202_55,
    )
    assert res_out["inside"] is False
    assert "outside" in res_out["reason"]


def test_point_in_polygon_boundary_coverage(sample_geojson_data):
    """Boundary points must return inside=True because we use covers()."""
    parcel_202_55 = sample_geojson_data["features"][0]
    
    # Exact corner vertex
    res_boundary = check_point_in_parcel(
        latitude=10.7890,
        longitude=79.3245,
        parcel_geometry=parcel_202_55,
    )
    assert res_boundary["inside"] is True
    assert "covered" in res_boundary["reason"]


def test_point_in_multipolygon(sample_geojson_data):
    parcel_multi = sample_geojson_data["features"][1]  # 145/2 MultiPolygon

    # Inside second polygon of MultiPolygon
    res = check_point_in_parcel(
        latitude=10.7915,
        longitude=79.3280,
        parcel_geometry=parcel_multi,
    )
    assert res["inside"] is True
    assert res["geometry_type"] == "MultiPolygon"


def test_coordinate_validation_and_ordering():
    # Valid
    assert validate_coordinates(10.789, 79.325) is None

    # Out of range latitude
    assert "Latitude 95.0 out of range" in validate_coordinates(95.0, 79.325)

    # Out of range longitude
    assert "Longitude 200.0 out of range" in validate_coordinates(10.0, 200.0)

    # Inverted lat/lon check error handling
    res_err = check_point_in_parcel(
        latitude=120.0,
        longitude=79.0,
        parcel_geometry={"type": "Polygon", "coordinates": []}
    )
    assert res_err["inside"] is False
    assert res_err["error"] is not None


def test_malformed_geometry_repair():
    """Bowtie self-intersecting polygon must be repaired by make_valid."""
    bowtie_geom = {
        "type": "Polygon",
        "coordinates": [[
            [0, 0], [0, 2], [2, 0], [2, 2], [0, 0]
        ]]
    }
    res = check_point_in_parcel(
        latitude=0.5,
        longitude=0.5,
        parcel_geometry=bowtie_geom,
    )
    assert res["inside"] is True
    assert res["warning"] is not None


def test_check_point_in_all_parcels(sample_geojson_data):
    # Point inside 202/55
    res = check_point_in_all_parcels(
        latitude=10.7895,
        longitude=79.3250,
        feature_collection=sample_geojson_data,
    )
    assert res["matched"] is True
    assert res["survey_number"] == "202/55"

    # Point not in any parcel
    res_none = check_point_in_all_parcels(
        latitude=1.0,
        longitude=1.0,
        feature_collection=sample_geojson_data,
    )
    assert res_none["matched"] is False
    assert res_none["survey_number"] is None


def test_export_selected_parcels(sample_geojson_data):
    feats = [sample_geojson_data["features"][0]]
    fc = export_selected_parcels(feats)
    assert fc["type"] == "FeatureCollection"
    assert len(fc["features"]) == 1

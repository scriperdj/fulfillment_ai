"""Tests for src/features — feature extraction and transformation."""

from __future__ import annotations

import pytest

from src.features.transform import (
    MODEL_FEATURE_NAMES,
    _FIELD_MAP,
    build_feature_dataframe,
    extract_features,
    preserve_raw_fields,
)


# ---------------------------------------------------------------------------
# Sample data
# ---------------------------------------------------------------------------

SAMPLE_ENRICHED_ORDER = {
    "order_id": "ORD-001",
    "warehouse_block": "B",
    "mode_of_shipment": "Flight",
    "customer_care_calls": 4,
    "customer_rating": 2,
    "cost_of_the_product": 250,
    "prior_purchases": 3,
    "product_importance": "High",
    "gender": "F",
    "discount_offered": 10,
    "weight_in_gms": 4200,
    "order_status": "shipped",
    "ship_date": "2025-01-10",
    "delivery_date": None,
    "customer_id": "CUST-42",
    "order_date": "2025-01-08",
}


# ---------------------------------------------------------------------------
# extract_features tests
# ---------------------------------------------------------------------------


class TestExtractFeatures:
    def test_returns_10_features(self):
        result = extract_features(SAMPLE_ENRICHED_ORDER)
        assert len(result) == 10

    def test_all_model_feature_names_present(self):
        result = extract_features(SAMPLE_ENRICHED_ORDER)
        for name in MODEL_FEATURE_NAMES:
            assert name in result, f"Missing feature: {name}"

    def test_warehouse_block_mapped(self):
        result = extract_features(SAMPLE_ENRICHED_ORDER)
        assert result["Warehouse_block"] == "B"

    def test_mode_of_shipment_mapped(self):
        result = extract_features(SAMPLE_ENRICHED_ORDER)
        assert result["Mode_of_Shipment"] == "Flight"

    def test_customer_care_calls_mapped(self):
        result = extract_features(SAMPLE_ENRICHED_ORDER)
        assert result["Customer_care_calls"] == 4

    def test_customer_rating_mapped(self):
        result = extract_features(SAMPLE_ENRICHED_ORDER)
        assert result["Customer_rating"] == 2

    def test_cost_of_product_mapped(self):
        result = extract_features(SAMPLE_ENRICHED_ORDER)
        assert result["Cost_of_the_Product"] == 250

    def test_prior_purchases_mapped(self):
        result = extract_features(SAMPLE_ENRICHED_ORDER)
        assert result["Prior_purchases"] == 3

    def test_product_importance_mapped(self):
        result = extract_features(SAMPLE_ENRICHED_ORDER)
        assert result["Product_importance"] == "High"

    def test_gender_mapped(self):
        result = extract_features(SAMPLE_ENRICHED_ORDER)
        assert result["Gender"] == "F"

    def test_discount_offered_mapped(self):
        result = extract_features(SAMPLE_ENRICHED_ORDER)
        assert result["Discount_offered"] == 10

    def test_weight_in_gms_mapped(self):
        result = extract_features(SAMPLE_ENRICHED_ORDER)
        assert result["Weight_in_gms"] == 4200

    def test_missing_field_gets_default(self):
        sparse = {"order_id": "ORD-SPARSE"}
        result = extract_features(sparse)
        assert len(result) == 10
        assert result["Warehouse_block"] == "A"  # default
        assert result["Mode_of_Shipment"] == "Ship"  # default
        assert result["Customer_care_calls"] == 0  # default

    def test_no_extra_fields_in_output(self):
        result = extract_features(SAMPLE_ENRICHED_ORDER)
        assert "order_id" not in result
        assert "order_status" not in result

    def test_field_map_covers_all_model_features(self):
        mapped_targets = set(_FIELD_MAP.values())
        assert mapped_targets == set(MODEL_FEATURE_NAMES)


# ---------------------------------------------------------------------------
# build_feature_dataframe tests
# ---------------------------------------------------------------------------


class TestBuildFeatureDataframe:
    def test_correct_shape_single_row(self):
        features = extract_features(SAMPLE_ENRICHED_ORDER)
        df = build_feature_dataframe([features])
        assert df.shape == (1, 10)

    def test_correct_shape_multiple_rows(self):
        rows = [extract_features(SAMPLE_ENRICHED_ORDER) for _ in range(5)]
        df = build_feature_dataframe(rows)
        assert df.shape == (5, 10)

    def test_column_names_match_model(self):
        features = extract_features(SAMPLE_ENRICHED_ORDER)
        df = build_feature_dataframe([features])
        assert list(df.columns) == MODEL_FEATURE_NAMES

    def test_empty_list_returns_empty_dataframe(self):
        df = build_feature_dataframe([])
        assert len(df) == 0
        assert list(df.columns) == MODEL_FEATURE_NAMES

    def test_numeric_columns_are_int(self):
        features = extract_features(SAMPLE_ENRICHED_ORDER)
        df = build_feature_dataframe([features])
        assert df["Customer_care_calls"].dtype == int
        assert df["Weight_in_gms"].dtype == int

    def test_string_values_preserved(self):
        features = extract_features(SAMPLE_ENRICHED_ORDER)
        df = build_feature_dataframe([features])
        assert df["Warehouse_block"].iloc[0] == "B"
        assert df["Gender"].iloc[0] == "F"


# ---------------------------------------------------------------------------
# preserve_raw_fields tests
# ---------------------------------------------------------------------------


class TestPreserveRawFields:
    def test_order_id_preserved(self):
        result = preserve_raw_fields(SAMPLE_ENRICHED_ORDER)
        assert result["order_id"] == "ORD-001"

    def test_order_status_preserved(self):
        result = preserve_raw_fields(SAMPLE_ENRICHED_ORDER)
        assert result["order_status"] == "shipped"

    def test_warehouse_block_preserved(self):
        result = preserve_raw_fields(SAMPLE_ENRICHED_ORDER)
        assert result["warehouse_block"] == "B"

    def test_mode_of_shipment_preserved(self):
        result = preserve_raw_fields(SAMPLE_ENRICHED_ORDER)
        assert result["mode_of_shipment"] == "Flight"

    def test_missing_fields_excluded(self):
        sparse = {"order_id": "ORD-SPARSE"}
        result = preserve_raw_fields(sparse)
        assert "order_id" in result
        assert "order_status" not in result

    def test_does_not_include_non_raw_fields(self):
        row = {**SAMPLE_ENRICHED_ORDER, "reached_on_time": 1}
        result = preserve_raw_fields(row)
        # reached_on_time is not in _RAW_FIELDS
        assert "reached_on_time" not in result

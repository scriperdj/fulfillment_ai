"""Tests for src/ml — model loading and inference with real artifacts."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.ml.model_loader import load_metadata, load_model, load_preprocessor
from src.ml.inference import predict_batch, predict_single


# ---------------------------------------------------------------------------
# Sample enriched order for inference tests
# ---------------------------------------------------------------------------

SAMPLE_ORDER = {
    "order_id": "ORD-TEST-001",
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
}

SAMPLE_ORDER_2 = {
    "order_id": "ORD-TEST-002",
    "warehouse_block": "A",
    "mode_of_shipment": "Road",
    "customer_care_calls": 1,
    "customer_rating": 5,
    "cost_of_the_product": 100,
    "prior_purchases": 8,
    "product_importance": "Low",
    "gender": "M",
    "discount_offered": 55,
    "weight_in_gms": 1000,
    "order_status": "processing",
}


# ---------------------------------------------------------------------------
# Fixtures — clear lru_cache between tests
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _clear_caches():
    """Ensure lru_cache doesn't leak between tests."""
    load_model.cache_clear()
    load_preprocessor.cache_clear()
    load_metadata.cache_clear()
    yield
    load_model.cache_clear()
    load_preprocessor.cache_clear()
    load_metadata.cache_clear()


# ---------------------------------------------------------------------------
# load_model tests
# ---------------------------------------------------------------------------


class TestLoadModel:
    def test_returns_classifier(self):
        model = load_model()
        assert hasattr(model, "predict_proba")
        assert hasattr(model, "predict")

    def test_invalid_path_raises(self):
        with pytest.raises(FileNotFoundError):
            load_model(path="/nonexistent/model.joblib")

    def test_caching(self):
        m1 = load_model()
        m2 = load_model()
        assert m1 is m2


# ---------------------------------------------------------------------------
# load_preprocessor tests
# ---------------------------------------------------------------------------


class TestLoadPreprocessor:
    def test_returns_transformer(self):
        preprocessor = load_preprocessor()
        assert hasattr(preprocessor, "transform")

    def test_invalid_path_raises(self):
        with pytest.raises(FileNotFoundError):
            load_preprocessor(path="/nonexistent/preprocessor.joblib")

    def test_caching(self):
        p1 = load_preprocessor()
        p2 = load_preprocessor()
        assert p1 is p2


# ---------------------------------------------------------------------------
# load_metadata tests
# ---------------------------------------------------------------------------


class TestLoadMetadata:
    def test_returns_dict(self):
        meta = load_metadata()
        assert isinstance(meta, dict)

    def test_has_expected_keys(self):
        meta = load_metadata()
        assert "model_type" in meta
        assert "roc_auc" in meta
        assert "feature_names" in meta
        assert "transformed_feature_count" in meta

    def test_feature_count_is_10(self):
        meta = load_metadata()
        assert len(meta["feature_names"]) == 10

    def test_transformed_feature_count_is_19(self):
        meta = load_metadata()
        assert meta["transformed_feature_count"] == 19

    def test_invalid_path_raises(self):
        with pytest.raises(FileNotFoundError):
            load_metadata(path="/nonexistent/metadata.json")


# ---------------------------------------------------------------------------
# predict_single tests
# ---------------------------------------------------------------------------


class TestPredictSingle:
    def test_returns_dict(self):
        result = predict_single(SAMPLE_ORDER)
        assert isinstance(result, dict)

    def test_has_required_keys(self):
        result = predict_single(SAMPLE_ORDER)
        assert "order_id" in result
        assert "delay_probability" in result
        assert "severity" in result
        assert "features_used" in result

    def test_order_id_passthrough(self):
        result = predict_single(SAMPLE_ORDER)
        assert result["order_id"] == "ORD-TEST-001"

    def test_delay_probability_in_range(self):
        result = predict_single(SAMPLE_ORDER)
        assert 0.0 <= result["delay_probability"] <= 1.0

    def test_severity_is_valid(self):
        result = predict_single(SAMPLE_ORDER)
        assert result["severity"] in {"critical", "warning", "info", "low"}

    def test_severity_matches_probability(self):
        result = predict_single(SAMPLE_ORDER)
        p = result["delay_probability"]
        sev = result["severity"]
        if p >= 0.7:
            assert sev == "critical"
        elif p >= 0.5:
            assert sev == "warning"
        elif p >= 0.3:
            assert sev == "info"
        else:
            assert sev == "low"

    def test_features_used_has_10_keys(self):
        result = predict_single(SAMPLE_ORDER)
        assert len(result["features_used"]) == 10

    def test_different_inputs_may_give_different_probabilities(self):
        r1 = predict_single(SAMPLE_ORDER)
        r2 = predict_single(SAMPLE_ORDER_2)
        # Not guaranteed to differ, but at least both should be valid
        assert 0.0 <= r1["delay_probability"] <= 1.0
        assert 0.0 <= r2["delay_probability"] <= 1.0

    def test_missing_order_id_defaults_empty(self):
        order = {k: v for k, v in SAMPLE_ORDER.items() if k != "order_id"}
        result = predict_single(order)
        assert result["order_id"] == ""


# ---------------------------------------------------------------------------
# predict_batch tests
# ---------------------------------------------------------------------------


class TestPredictBatch:
    def test_empty_list(self):
        result = predict_batch([])
        assert result == []

    def test_single_order(self):
        result = predict_batch([SAMPLE_ORDER])
        assert len(result) == 1
        assert result[0]["order_id"] == "ORD-TEST-001"

    def test_multiple_orders(self):
        result = predict_batch([SAMPLE_ORDER, SAMPLE_ORDER_2])
        assert len(result) == 2
        assert result[0]["order_id"] == "ORD-TEST-001"
        assert result[1]["order_id"] == "ORD-TEST-002"

    def test_all_probabilities_in_range(self):
        result = predict_batch([SAMPLE_ORDER, SAMPLE_ORDER_2])
        for r in result:
            assert 0.0 <= r["delay_probability"] <= 1.0

    def test_all_severities_valid(self):
        result = predict_batch([SAMPLE_ORDER, SAMPLE_ORDER_2])
        for r in result:
            assert r["severity"] in {"critical", "warning", "info", "low"}

    def test_batch_matches_single(self):
        """Batch results should match individual predict_single calls."""
        single_1 = predict_single(SAMPLE_ORDER)
        single_2 = predict_single(SAMPLE_ORDER_2)
        batch = predict_batch([SAMPLE_ORDER, SAMPLE_ORDER_2])

        assert batch[0]["delay_probability"] == pytest.approx(
            single_1["delay_probability"], abs=1e-10
        )
        assert batch[1]["delay_probability"] == pytest.approx(
            single_2["delay_probability"], abs=1e-10
        )

    def test_batch_result_structure(self):
        result = predict_batch([SAMPLE_ORDER])
        r = result[0]
        assert "order_id" in r
        assert "delay_probability" in r
        assert "severity" in r
        assert "features_used" in r
        assert len(r["features_used"]) == 10


# ---------------------------------------------------------------------------
# End-to-end integration test
# ---------------------------------------------------------------------------


class TestEndToEnd:
    def test_enriched_order_to_prediction(self):
        """Full pipeline: enriched order dict → predict_single → valid prediction."""
        enriched = {
            "order_id": "ORD-E2E",
            "warehouse_block": "C",
            "mode_of_shipment": "Ship",
            "customer_care_calls": 3,
            "customer_rating": 3,
            "cost_of_the_product": 180,
            "prior_purchases": 5,
            "product_importance": "Medium",
            "gender": "M",
            "discount_offered": 20,
            "weight_in_gms": 3000,
            "order_status": "processing",
            "ship_date": None,
            "delivery_date": None,
        }
        result = predict_single(enriched)
        assert result["order_id"] == "ORD-E2E"
        assert 0.0 <= result["delay_probability"] <= 1.0
        assert result["severity"] in {"critical", "warning", "info", "low"}
        assert len(result["features_used"]) == 10

    def test_sparse_order_still_works(self):
        """Minimal order dict with defaults for missing fields."""
        sparse = {
            "order_id": "ORD-SPARSE",
            "warehouse_block": "D",
            "mode_of_shipment": "Road",
        }
        result = predict_single(sparse)
        assert result["order_id"] == "ORD-SPARSE"
        assert 0.0 <= result["delay_probability"] <= 1.0

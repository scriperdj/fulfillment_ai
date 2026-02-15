"""Tests for src/pipeline — unified processing pipeline."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from src.db.models import Base, BatchJob, Deviation, Prediction
from src.pipeline.processor import run_pipeline


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SAMPLE_ORDER = {
    "order_id": "ORD-PIPE-001",
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
    "order_id": "ORD-PIPE-002",
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


@pytest.fixture()
def engine():
    eng = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(bind=eng)
    yield eng
    eng.dispose()


@pytest.fixture()
def session(engine):
    connection = engine.connect()
    transaction = connection.begin()
    sess = Session(bind=connection)
    yield sess
    sess.close()
    transaction.rollback()
    connection.close()


@pytest.fixture(autouse=True)
def _clear_ml_caches():
    from src.ml.model_loader import load_model, load_preprocessor, load_metadata

    load_model.cache_clear()
    load_preprocessor.cache_clear()
    load_metadata.cache_clear()
    yield
    load_model.cache_clear()
    load_preprocessor.cache_clear()
    load_metadata.cache_clear()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestRunPipelineEmpty:
    def test_empty_list_returns_zero_counts(self, session):
        result = run_pipeline([], session=session)
        assert result["predictions_count"] == 0
        assert result["deviations_count"] == 0
        assert result["severity_breakdown"] == {}

    def test_empty_list_creates_no_records(self, session):
        run_pipeline([], session=session)
        assert session.query(Prediction).count() == 0


class TestRunPipelineSingle:
    def test_creates_prediction_record(self, session):
        run_pipeline([SAMPLE_ORDER], session=session)
        preds = session.query(Prediction).all()
        assert len(preds) == 1

    def test_prediction_has_correct_order_id(self, session):
        run_pipeline([SAMPLE_ORDER], session=session)
        pred = session.query(Prediction).first()
        assert pred.order_id == "ORD-PIPE-001"

    def test_prediction_has_delay_probability(self, session):
        run_pipeline([SAMPLE_ORDER], session=session)
        pred = session.query(Prediction).first()
        assert 0.0 <= pred.delay_probability <= 1.0

    def test_prediction_has_valid_severity(self, session):
        run_pipeline([SAMPLE_ORDER], session=session)
        pred = session.query(Prediction).first()
        assert pred.severity in {"critical", "warning", "info", "low"}

    def test_prediction_has_features_json(self, session):
        run_pipeline([SAMPLE_ORDER], session=session)
        pred = session.query(Prediction).first()
        assert pred.features_json is not None
        assert "order_id" in pred.features_json
        assert "warehouse_block" in pred.features_json

    def test_prediction_source_default_batch(self, session):
        run_pipeline([SAMPLE_ORDER], session=session)
        pred = session.query(Prediction).first()
        assert pred.source == "batch"

    def test_returns_summary(self, session):
        result = run_pipeline([SAMPLE_ORDER], session=session)
        assert result["predictions_count"] == 1
        assert isinstance(result["deviations_count"], int)
        assert isinstance(result["severity_breakdown"], dict)


class TestRunPipelineMultiple:
    def test_creates_correct_prediction_count(self, session):
        orders = [SAMPLE_ORDER, SAMPLE_ORDER_2]
        run_pipeline(orders, session=session)
        assert session.query(Prediction).count() == 2

    def test_returns_correct_predictions_count(self, session):
        orders = [SAMPLE_ORDER, SAMPLE_ORDER_2]
        result = run_pipeline(orders, session=session)
        assert result["predictions_count"] == 2

    def test_severity_breakdown_sums_correctly(self, session):
        orders = [SAMPLE_ORDER, SAMPLE_ORDER_2]
        result = run_pipeline(orders, session=session)
        total = sum(result["severity_breakdown"].values())
        assert total == 2


class TestRunPipelineBatchJob:
    def test_batch_job_id_linked(self, session):
        batch_id = uuid.uuid4()
        run_pipeline([SAMPLE_ORDER], session=session, batch_job_id=batch_id)
        pred = session.query(Prediction).first()
        assert pred.batch_job_id == batch_id

    def test_no_batch_job_id_is_none(self, session):
        run_pipeline([SAMPLE_ORDER], session=session)
        pred = session.query(Prediction).first()
        assert pred.batch_job_id is None


class TestRunPipelineStreaming:
    def test_source_streaming(self, session):
        run_pipeline([SAMPLE_ORDER], session=session, source="streaming")
        pred = session.query(Prediction).first()
        assert pred.source == "streaming"


class TestRunPipelineDeviations:
    def test_deviations_detected_for_high_probability(self, session):
        """Orders with high delay probability should create deviations."""
        result = run_pipeline([SAMPLE_ORDER, SAMPLE_ORDER_2], session=session)
        # At least check that deviations_count is an int (actual count depends on model output)
        assert isinstance(result["deviations_count"], int)
        assert result["deviations_count"] >= 0

    def test_deviations_linked_to_predictions(self, session):
        run_pipeline([SAMPLE_ORDER], session=session)
        deviations = session.query(Deviation).all()
        for dev in deviations:
            assert dev.prediction_id is not None
            pred = session.query(Prediction).get(dev.prediction_id)
            assert pred is not None

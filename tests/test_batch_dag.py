"""Tests for dags/batch_processing_dag.py — task functions tested directly."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from dags.batch_processing_dag import (
    load_csv,
    on_failure_callback,
    run_pipeline_task,
    update_status_success,
    validate_schema,
)
from src.db.models import Base, BatchJob, Prediction


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


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


VALID_ORDERS = [
    {
        "order_id": "ORD-DAG-001",
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
    }
]

INVALID_ORDERS = [
    {
        "order_id": "ORD-BAD",
        # Missing many required fields
    }
]


# ---------------------------------------------------------------------------
# load_csv tests
# ---------------------------------------------------------------------------


class TestLoadCSV:
    def test_loads_csv_data(self, session, tmp_path):
        # Create CSV file
        csv_path = tmp_path / "test.csv"
        df = pd.DataFrame(VALID_ORDERS)
        df.to_csv(csv_path, index=False)

        # Create BatchJob pointing to the file
        job = BatchJob(filename="test.csv", status="processing", row_count=1)
        session.add(job)
        session.flush()

        # Patch settings to use tmp_path as upload dir
        from unittest.mock import patch, MagicMock

        mock_settings = MagicMock()
        mock_settings.UPLOAD_DIR = tmp_path

        with patch("src.config.settings.get_settings", return_value=mock_settings):
            result = load_csv(str(job.id), session=session)

        assert len(result) == 1
        assert result[0]["order_id"] == "ORD-DAG-001"

    def test_missing_batch_job_raises(self, session):
        fake_id = str(uuid.uuid4())
        with pytest.raises(ValueError, match="not found"):
            load_csv(fake_id, session=session)

    def test_missing_csv_file_raises(self, session, tmp_path):
        job = BatchJob(filename="nonexistent.csv", status="processing", row_count=0)
        session.add(job)
        session.flush()

        from unittest.mock import patch, MagicMock

        mock_settings = MagicMock()
        mock_settings.UPLOAD_DIR = tmp_path

        with patch("src.config.settings.get_settings", return_value=mock_settings):
            with pytest.raises(FileNotFoundError):
                load_csv(str(job.id), session=session)


# ---------------------------------------------------------------------------
# validate_schema tests
# ---------------------------------------------------------------------------


class TestValidateSchema:
    def test_valid_data_passes(self):
        result = validate_schema(VALID_ORDERS)
        assert result == VALID_ORDERS

    def test_invalid_data_raises(self):
        with pytest.raises(ValueError, match="Schema validation failed"):
            validate_schema(INVALID_ORDERS)


# ---------------------------------------------------------------------------
# run_pipeline_task tests
# ---------------------------------------------------------------------------


class TestRunPipelineTask:
    def test_stores_predictions(self, session):
        batch_id = uuid.uuid4()
        job = BatchJob(id=batch_id, filename="test.csv", status="processing", row_count=1)
        session.add(job)
        session.flush()

        summary = run_pipeline_task(VALID_ORDERS, str(batch_id), session=session)
        assert summary["predictions_count"] == 1
        assert session.query(Prediction).count() == 1

    def test_returns_summary(self, session):
        batch_id = uuid.uuid4()
        job = BatchJob(id=batch_id, filename="test.csv", status="processing", row_count=1)
        session.add(job)
        session.flush()

        summary = run_pipeline_task(VALID_ORDERS, str(batch_id), session=session)
        assert "predictions_count" in summary
        assert "deviations_count" in summary
        assert "severity_breakdown" in summary


# ---------------------------------------------------------------------------
# update_status_success tests
# ---------------------------------------------------------------------------


class TestUpdateStatusSuccess:
    def test_sets_status_completed(self, session):
        job = BatchJob(filename="test.csv", status="processing", row_count=1)
        session.add(job)
        session.flush()

        update_status_success(str(job.id), {"predictions_count": 1}, session=session)
        session.refresh(job)
        assert job.status == "completed"
        assert job.completed_at is not None


# ---------------------------------------------------------------------------
# on_failure_callback tests
# ---------------------------------------------------------------------------


class TestOnFailureCallback:
    def test_sets_status_failed(self, session):
        job = BatchJob(filename="test.csv", status="processing", row_count=1)
        session.add(job)
        session.flush()

        on_failure_callback(str(job.id), "Something went wrong", session=session)
        session.refresh(job)
        assert job.status == "failed"
        assert job.error_message == "Something went wrong"
        assert job.completed_at is not None

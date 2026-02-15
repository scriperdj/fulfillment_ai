"""Tests for src/ingestion — CSV handler and schema validator."""

import uuid

import pandas as pd
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from src.db.models import Base, BatchJob
from src.ingestion.csv_handler import upload_csv
from src.ingestion.schema_validator import ENRICHED_SCHEMA, validate_csv, validate_row


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


def _valid_row() -> dict:
    """Return a single valid enriched-schema row as a dict."""
    return {
        "order_id": "ORD-001",
        "customer_id": "CUST-100",
        "order_date": "2024-01-15",
        "warehouse_block": "A",
        "mode_of_shipment": "Ship",
        "customer_care_calls": 3,
        "customer_rating": 4,
        "cost_of_the_product": 250,
        "prior_purchases": 5,
        "product_importance": "High",
        "gender": "M",
        "discount_offered": 10,
        "weight_in_gms": 4000,
        "ship_date": "2024-01-16",
        "delivery_date": "2024-01-20",
        "reached_on_time": 1,
        "product_category": "Electronics",
        "order_status": "shipped",
    }


def _make_csv(tmp_path, rows: list[dict] | None = None, filename: str = "test.csv") -> str:
    """Write a CSV to *tmp_path* and return the file path."""
    if rows is None:
        rows = [_valid_row()]
    df = pd.DataFrame(rows)
    path = tmp_path / filename
    df.to_csv(path, index=False)
    return str(path)


# ---------------------------------------------------------------------------
# ENRICHED_SCHEMA tests
# ---------------------------------------------------------------------------


class TestEnrichedSchema:
    def test_schema_has_18_fields(self):
        assert len(ENRICHED_SCHEMA) == 18

    def test_required_fields(self):
        required = {k for k, v in ENRICHED_SCHEMA.items() if v["required"]}
        expected = {
            "order_id",
            "warehouse_block",
            "mode_of_shipment",
            "customer_care_calls",
            "customer_rating",
            "cost_of_the_product",
            "prior_purchases",
            "product_importance",
            "gender",
            "discount_offered",
            "weight_in_gms",
        }
        assert required == expected

    def test_nullable_fields(self):
        nullable = {k for k, v in ENRICHED_SCHEMA.items() if not v["required"]}
        assert "ship_date" in nullable
        assert "delivery_date" in nullable
        assert "customer_id" in nullable
        assert "order_date" in nullable
        assert "reached_on_time" in nullable
        assert "product_category" in nullable
        assert "order_status" in nullable


# ---------------------------------------------------------------------------
# validate_row tests
# ---------------------------------------------------------------------------


class TestValidateRow:
    def test_valid_row_no_errors(self):
        errors = validate_row(_valid_row(), row_index=0)
        assert errors == []

    def test_missing_required_field(self):
        row = _valid_row()
        del row["order_id"]
        errors = validate_row(row, row_index=0)
        assert len(errors) == 1
        assert errors[0]["field"] == "order_id"
        assert "Missing required" in errors[0]["message"]

    def test_empty_required_string_field(self):
        row = _valid_row()
        row["order_id"] = "  "
        errors = validate_row(row, row_index=0)
        assert any(e["field"] == "order_id" for e in errors)

    def test_wrong_type_for_int_field(self):
        row = _valid_row()
        row["customer_care_calls"] = "not-a-number"
        errors = validate_row(row, row_index=0)
        assert any(e["field"] == "customer_care_calls" for e in errors)

    def test_nullable_field_can_be_none(self):
        row = _valid_row()
        row["ship_date"] = None
        errors = validate_row(row, row_index=0)
        assert errors == []

    def test_missing_optional_field(self):
        row = _valid_row()
        del row["ship_date"]
        errors = validate_row(row, row_index=0)
        assert errors == []

    def test_multiple_errors_in_one_row(self):
        row = _valid_row()
        del row["order_id"]
        del row["warehouse_block"]
        errors = validate_row(row, row_index=5)
        assert len(errors) == 2
        assert all(e["row"] == 5 for e in errors)

    def test_numeric_string_accepted_for_int_field(self):
        row = _valid_row()
        row["customer_care_calls"] = "3"
        errors = validate_row(row, row_index=0)
        assert errors == []

    def test_float_accepted_for_int_field(self):
        row = _valid_row()
        row["customer_care_calls"] = 3.0
        errors = validate_row(row, row_index=0)
        assert errors == []


# ---------------------------------------------------------------------------
# validate_csv tests
# ---------------------------------------------------------------------------


class TestValidateCsv:
    def test_valid_dataframe(self):
        df = pd.DataFrame([_valid_row()])
        report = validate_csv(df)
        assert report["valid"] is True
        assert report["error_count"] == 0
        assert report["errors"] == []

    def test_invalid_rows_mixed(self):
        good = _valid_row()
        bad = _valid_row()
        del bad["order_id"]
        df = pd.DataFrame([good, bad])
        report = validate_csv(df)
        assert report["valid"] is False
        assert report["error_count"] >= 1
        assert any(e["field"] == "order_id" for e in report["errors"])

    def test_missing_column_entirely(self):
        row = _valid_row()
        del row["warehouse_block"]
        df = pd.DataFrame([row])
        report = validate_csv(df)
        assert report["valid"] is False
        assert any(e["field"] == "warehouse_block" for e in report["errors"])

    def test_empty_dataframe(self):
        df = pd.DataFrame(columns=list(ENRICHED_SCHEMA.keys()))
        report = validate_csv(df)
        assert report["valid"] is True
        assert report["error_count"] == 0

    def test_report_structure(self):
        df = pd.DataFrame([_valid_row()])
        report = validate_csv(df)
        assert "valid" in report
        assert "error_count" in report
        assert "errors" in report
        assert isinstance(report["errors"], list)


# ---------------------------------------------------------------------------
# upload_csv tests
# ---------------------------------------------------------------------------


class TestUploadCsv:
    def test_upload_creates_file_and_record(self, tmp_path, session):
        csv_path = _make_csv(tmp_path, [_valid_row()])
        upload_dir = tmp_path / "uploads"

        job = upload_csv(csv_path, session=session, upload_dir=upload_dir)

        assert job.id is not None
        assert isinstance(job.id, uuid.UUID)
        assert job.status == "processing"
        assert job.row_count == 1
        assert job.filename.endswith(".csv")
        # File was saved
        saved = upload_dir / job.filename
        assert saved.exists()

    def test_upload_multiple_rows(self, tmp_path, session):
        rows = [_valid_row() for _ in range(5)]
        for i, r in enumerate(rows):
            r["order_id"] = f"ORD-{i}"
        csv_path = _make_csv(tmp_path, rows)
        upload_dir = tmp_path / "uploads"

        job = upload_csv(csv_path, session=session, upload_dir=upload_dir)
        assert job.row_count == 5

    def test_upload_creates_directory(self, tmp_path, session):
        csv_path = _make_csv(tmp_path)
        upload_dir = tmp_path / "deep" / "nested" / "uploads"
        assert not upload_dir.exists()

        upload_csv(csv_path, session=session, upload_dir=upload_dir)
        assert upload_dir.exists()

    def test_upload_with_file_object(self, tmp_path, session):
        csv_path = _make_csv(tmp_path)
        upload_dir = tmp_path / "uploads"

        with open(csv_path, "rb") as f:
            job = upload_csv(f, session=session, upload_dir=upload_dir)

        assert job.row_count == 1
        assert job.status == "processing"

    def test_batch_job_persisted_in_db(self, tmp_path, session):
        csv_path = _make_csv(tmp_path)
        upload_dir = tmp_path / "uploads"

        job = upload_csv(csv_path, session=session, upload_dir=upload_dir)

        fetched = session.get(BatchJob, job.id)
        assert fetched is not None
        assert fetched.filename == job.filename

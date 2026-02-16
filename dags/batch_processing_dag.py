"""Airflow batch processing DAG — process uploaded CSV through the unified pipeline.

Triggered externally with conf={"batch_job_id": "<uuid>"}.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

import pandas as pd

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Task functions (standalone, testable without Airflow)
# ---------------------------------------------------------------------------


_CSV_COLUMN_RENAMES: dict[str, str] = {
    "ID": "order_id",
    "Warehouse_block": "warehouse_block",
    "Mode_of_Shipment": "mode_of_shipment",
    "Customer_care_calls": "customer_care_calls",
    "Customer_rating": "customer_rating",
    "Cost_of_the_Product": "cost_of_the_product",
    "Prior_purchases": "prior_purchases",
    "Product_importance": "product_importance",
    "Gender": "gender",
    "Discount_offered": "discount_offered",
    "Weight_in_gms": "weight_in_gms",
    "Reached.on.Time_Y.N": "reached_on_time",
}


def load_csv(batch_job_id: str, *, session: Any) -> list[dict[str, Any]]:
    """Load CSV data for a batch job.

    Parameters
    ----------
    batch_job_id:
        UUID string of the batch job.
    session:
        SQLAlchemy sync session.

    Returns
    -------
    List of order dicts from the CSV with snake_case keys.
    """
    from src.config.settings import get_settings
    from src.db.models import BatchJob

    uid = uuid.UUID(batch_job_id)
    job = session.query(BatchJob).filter(BatchJob.id == uid).first()
    if job is None:
        raise ValueError(f"BatchJob {batch_job_id} not found")

    settings = get_settings()
    file_path = settings.UPLOAD_DIR / job.filename
    if not file_path.exists():
        raise FileNotFoundError(f"CSV file not found: {file_path}")

    df = pd.read_csv(file_path)
    # Normalise CSV column names (Title_case → snake_case)
    df = df.rename(columns=_CSV_COLUMN_RENAMES)
    return df.to_dict(orient="records")


def validate_schema(orders: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Validate order dicts against the enriched schema.

    Returns the orders unchanged if valid, raises on failure.
    """
    from src.ingestion.schema_validator import validate_csv

    df = pd.DataFrame(orders)
    result = validate_csv(df)
    if not result["valid"]:
        raise ValueError(
            f"Schema validation failed with {result['error_count']} errors: "
            f"{result['errors'][:5]}"
        )
    return orders


def run_pipeline_task(
    orders: list[dict[str, Any]],
    batch_job_id: str,
    *,
    session: Any,
) -> dict[str, Any]:
    """Run the unified processing pipeline.

    Returns the pipeline summary dict.
    """
    from src.pipeline.processor import run_pipeline

    uid = uuid.UUID(batch_job_id)
    return run_pipeline(orders, session=session, batch_job_id=uid, source="batch")


def update_status_success(
    batch_job_id: str,
    summary: dict[str, Any],
    *,
    session: Any,
) -> None:
    """Mark batch job as completed."""
    from src.db.models import BatchJob

    uid = uuid.UUID(batch_job_id)
    job = session.query(BatchJob).filter(BatchJob.id == uid).first()
    if job:
        job.status = "completed"
        job.completed_at = datetime.now(timezone.utc)
        session.flush()


def on_failure_callback(
    batch_job_id: str,
    error_message: str,
    *,
    session: Any,
) -> None:
    """Mark batch job as failed with error message."""
    from src.db.models import BatchJob

    uid = uuid.UUID(batch_job_id)
    job = session.query(BatchJob).filter(BatchJob.id == uid).first()
    if job:
        job.status = "failed"
        job.error_message = error_message
        job.completed_at = datetime.now(timezone.utc)
        session.flush()


# ---------------------------------------------------------------------------
# Airflow DAG definition (only created when Airflow is available)
# ---------------------------------------------------------------------------

try:
    from airflow.decorators import dag, task

    @dag(
        dag_id="batch_processing",
        schedule=None,
        start_date=datetime(2024, 1, 1),
        catchup=False,
        tags=["fulfillment", "batch"],
        params={"batch_job_id": ""},
    )
    def batch_processing_dag():
        """Process an uploaded CSV file through the unified ML pipeline."""

        @task()
        def af_load_csv(**context) -> list[dict[str, Any]]:
            batch_job_id = context["params"]["batch_job_id"]
            if not batch_job_id:
                from airflow.exceptions import AirflowException

                raise AirflowException("batch_job_id is required in DAG conf")
            from src.db.session import get_sync_session

            with get_sync_session() as session:
                return load_csv(batch_job_id, session=session)

        @task()
        def af_validate_schema(orders: list[dict[str, Any]]) -> list[dict[str, Any]]:
            return validate_schema(orders)

        @task()
        def af_run_pipeline(orders: list[dict[str, Any]], **context) -> dict[str, Any]:
            batch_job_id = context["params"]["batch_job_id"]
            from src.db.session import get_sync_session

            with get_sync_session() as session:
                return run_pipeline_task(orders, batch_job_id, session=session)

        @task()
        def af_update_status(summary: dict[str, Any], **context) -> None:
            batch_job_id = context["params"]["batch_job_id"]
            from src.db.session import get_sync_session

            with get_sync_session() as session:
                update_status_success(batch_job_id, summary, session=session)

        orders = af_load_csv()
        validated = af_validate_schema(orders)
        summary = af_run_pipeline(validated)
        af_update_status(summary)

    batch_processing_dag()

except ImportError:
    # Airflow not installed — DAG won't be registered but task functions
    # remain importable for testing.
    pass

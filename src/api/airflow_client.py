"""Lightweight Airflow 3.x REST API client for triggering DAGs and checking status."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

import httpx

from src.config.settings import get_settings

logger = logging.getLogger(__name__)

_token_cache: dict[str, Any] = {}


def _get_token() -> str:
    """Obtain a JWT token from Airflow, caching it until expiry."""
    import time

    cached = _token_cache.get("token")
    expires = _token_cache.get("expires", 0)
    if cached and time.time() < expires:
        return cached

    settings = get_settings()
    resp = httpx.post(
        f"{settings.AIRFLOW_API_URL}/auth/token",
        json={"username": settings.AIRFLOW_USERNAME, "password": settings.AIRFLOW_PASSWORD},
        timeout=10,
    )
    resp.raise_for_status()
    token = resp.json()["access_token"]
    # Cache for 23 hours (tokens typically last 24h)
    _token_cache["token"] = token
    _token_cache["expires"] = time.time() + 23 * 3600
    return token


def _headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {_get_token()}",
        "Content-Type": "application/json",
    }


def trigger_batch_dag(batch_job_id: str) -> str | None:
    """Trigger the batch_processing DAG with the given batch_job_id.

    Returns the dag_run_id on success, or None on failure.
    """
    settings = get_settings()
    url = f"{settings.AIRFLOW_API_URL}/api/v2/dags/batch_processing/dagRuns"
    payload = {
        "logical_date": datetime.now(timezone.utc).isoformat(),
        "conf": {"batch_job_id": batch_job_id},
    }

    try:
        resp = httpx.post(url, json=payload, headers=_headers(), timeout=15)
        resp.raise_for_status()
        dag_run_id = resp.json().get("dag_run_id")
        logger.info("Triggered batch_processing DAG: run_id=%s batch=%s", dag_run_id, batch_job_id)
        return dag_run_id
    except Exception:
        logger.warning("Failed to trigger batch_processing DAG for %s", batch_job_id, exc_info=True)
        return None


def get_dag_run_state(dag_run_id: str) -> str | None:
    """Query Airflow for the current state of a DAG run.

    Returns the state string (queued, running, success, failed) or None on error.
    """
    settings = get_settings()
    url = f"{settings.AIRFLOW_API_URL}/api/v2/dags/batch_processing/dagRuns/{dag_run_id}"

    try:
        resp = httpx.get(url, headers=_headers(), timeout=10)
        resp.raise_for_status()
        return resp.json().get("state")
    except Exception:
        logger.warning("Failed to query DAG run state for %s", dag_run_id, exc_info=True)
        return None

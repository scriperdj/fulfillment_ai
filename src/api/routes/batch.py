"""Batch job endpoints — upload, status, results."""

from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy.orm import Session

from src.api.deps import get_db
from src.api.schemas import (
    AgentResponseRecord,
    BatchListResponse,
    BatchStatusResponse,
    BatchUploadResponse,
    DeviationResponse,
    PredictionResponse,
)
from src.db.models import AgentResponse, BatchJob, Deviation, Prediction
from src.ingestion.csv_handler import upload_csv

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/batch", tags=["batch"])

# Airflow DAG run state → user-friendly batch status
_AIRFLOW_STATE_MAP: dict[str, str] = {
    "queued": "queued",
    "running": "running",
    "success": "completed",
    "failed": "failed",
}


def _get_batch_job(batch_id: str, session: Session) -> BatchJob:
    try:
        uid = uuid.UUID(batch_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Invalid batch ID format")
    job = session.query(BatchJob).filter(BatchJob.id == uid).first()
    if not job:
        raise HTTPException(status_code=404, detail="Batch job not found")
    return job


@router.get("/", response_model=BatchListResponse)
def batch_list(session: Session = Depends(get_db)):
    jobs = session.query(BatchJob).order_by(BatchJob.created_at.desc()).limit(50).all()

    results: list[BatchStatusResponse] = []
    for job in jobs:
        status = job.status
        # Poll Airflow for non-terminal jobs with a DAG run
        if status not in ("completed", "failed") and job.dag_run_id:
            from src.api.airflow_client import get_dag_run_state

            airflow_state = get_dag_run_state(job.dag_run_id)
            if airflow_state:
                mapped = _AIRFLOW_STATE_MAP.get(airflow_state, airflow_state)
                if mapped in ("completed", "failed") and status != mapped:
                    job.status = mapped
                    session.flush()
                status = mapped

        results.append(
            BatchStatusResponse(
                batch_job_id=str(job.id),
                status=status,
                filename=job.filename,
                row_count=job.row_count,
                created_at=job.created_at,
                completed_at=job.completed_at,
                error_message=job.error_message,
            )
        )

    return BatchListResponse(jobs=results)


@router.post("/upload", response_model=BatchUploadResponse, status_code=201)
def batch_upload(file: UploadFile, session: Session = Depends(get_db)):
    job = upload_csv(file.file, session=session)

    # Trigger Airflow batch DAG asynchronously
    from src.api.airflow_client import trigger_batch_dag

    dag_run_id = trigger_batch_dag(str(job.id))
    if dag_run_id:
        job.dag_run_id = dag_run_id
        job.status = "queued"
        session.flush()
    else:
        logger.warning("Could not trigger DAG for batch %s — job will stay pending", job.id)

    return BatchUploadResponse(
        batch_job_id=str(job.id),
        filename=job.filename,
        row_count=job.row_count,
        status=job.status,
    )


@router.get("/{batch_id}/status", response_model=BatchStatusResponse)
def batch_status(batch_id: str, session: Session = Depends(get_db)):
    job = _get_batch_job(batch_id, session)

    status = job.status

    # If the job hasn't reached a terminal state and we have a DAG run,
    # query Airflow for the live execution state.
    if status not in ("completed", "failed") and job.dag_run_id:
        from src.api.airflow_client import get_dag_run_state

        airflow_state = get_dag_run_state(job.dag_run_id)
        if airflow_state:
            mapped = _AIRFLOW_STATE_MAP.get(airflow_state, airflow_state)
            # Persist terminal states so we don't keep querying Airflow
            if mapped in ("completed", "failed") and status != mapped:
                job.status = mapped
                session.flush()
            status = mapped

    return BatchStatusResponse(
        batch_job_id=str(job.id),
        status=status,
        filename=job.filename,
        row_count=job.row_count,
        created_at=job.created_at,
        completed_at=job.completed_at,
        error_message=job.error_message,
    )


@router.get("/{batch_id}/predictions", response_model=list[PredictionResponse])
def batch_predictions(batch_id: str, session: Session = Depends(get_db)):
    job = _get_batch_job(batch_id, session)
    preds = session.query(Prediction).filter(Prediction.batch_job_id == job.id).all()
    return [
        PredictionResponse(
            id=str(p.id),
            order_id=p.order_id,
            delay_probability=p.delay_probability,
            severity=p.severity,
            source=p.source,
            features_json=p.features_json,
            created_at=p.created_at,
        )
        for p in preds
    ]


@router.get("/{batch_id}/deviations", response_model=list[DeviationResponse])
def batch_deviations(batch_id: str, session: Session = Depends(get_db)):
    job = _get_batch_job(batch_id, session)
    devs = session.query(Deviation).filter(Deviation.batch_job_id == job.id).all()
    return [
        DeviationResponse(
            id=str(d.id),
            prediction_id=str(d.prediction_id),
            severity=d.severity,
            reason=d.reason,
            status=d.status,
            created_at=d.created_at,
        )
        for d in devs
    ]


@router.get("/{batch_id}/agent-responses", response_model=list[AgentResponseRecord])
def batch_agent_responses(batch_id: str, session: Session = Depends(get_db)):
    job = _get_batch_job(batch_id, session)
    dev_ids = [
        d.id for d in session.query(Deviation).filter(Deviation.batch_job_id == job.id).all()
    ]
    if not dev_ids:
        return []
    responses = (
        session.query(AgentResponse).filter(AgentResponse.deviation_id.in_(dev_ids)).all()
    )
    return [
        AgentResponseRecord(
            id=str(r.id),
            deviation_id=str(r.deviation_id),
            agent_type=r.agent_type,
            action=r.action,
            details_json=r.details_json,
            created_at=r.created_at,
        )
        for r in responses
    ]

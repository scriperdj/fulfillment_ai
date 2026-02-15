"""Unified processing pipeline — transform → infer → store → KPI → detect → publish."""

from __future__ import annotations

import asyncio
import logging
import uuid
from typing import Any

from sqlalchemy.orm import Session

from src.config.settings import get_settings
from src.db.models import Prediction
from src.detection.deviation_detector import detect_batch
from src.detection.publisher import DeviationPublisher
from src.features.transform import preserve_raw_fields
from src.kpi.calculator import compute_order_kpis
from src.ml.inference import predict_batch as ml_predict_batch

logger = logging.getLogger(__name__)


def run_pipeline(
    orders: list[dict[str, Any]],
    *,
    session: Session,
    batch_job_id: uuid.UUID | None = None,
    source: str = "batch",
) -> dict[str, Any]:
    """Execute the full processing pipeline on a list of enriched orders.

    Steps:
        1. ML inference (feature extraction + prediction)
        2. Store predictions in DB
        3. Per-order KPI computation
        4. Deviation detection
        5. Publish deviation events (best-effort)

    Returns a summary dict with prediction/deviation counts and severity breakdown.
    """
    if not orders:
        return {
            "predictions_count": 0,
            "deviations_count": 0,
            "severity_breakdown": {},
        }

    # Step 1: ML Inference (vectorized)
    predictions_data = ml_predict_batch(orders)

    # Step 2: Store Predictions
    prediction_records: list[Prediction] = []
    for i, (order, pred_data) in enumerate(zip(orders, predictions_data)):
        raw_fields = preserve_raw_fields(order)
        prediction = Prediction(
            batch_job_id=batch_job_id,
            source=source,
            order_id=pred_data["order_id"] or f"unknown-{i}",
            delay_probability=pred_data["delay_probability"],
            severity=pred_data["severity"],
            features_json=raw_fields,
        )
        session.add(prediction)
        prediction_records.append(prediction)

    session.flush()  # Assign IDs without committing

    # Step 3: Per-order KPI computation
    for order, pred_data in zip(orders, predictions_data):
        compute_order_kpis(order, pred_data["delay_probability"])

    # Step 4: Deviation detection
    detect_input = [
        {
            "prediction_id": pred.id,
            "delay_probability": pred.delay_probability,
            "order_context": {
                "batch_job_id": batch_job_id,
                "order_id": pred.order_id,
            },
        }
        for pred in prediction_records
    ]
    deviations = detect_batch(detect_input, session=session)

    # Step 5: Publish deviation events (best-effort, async)
    _publish_deviations_best_effort(deviations, orders, predictions_data)

    # Build summary
    severity_breakdown: dict[str, int] = {}
    for pred_data in predictions_data:
        sev = pred_data["severity"]
        severity_breakdown[sev] = severity_breakdown.get(sev, 0) + 1

    return {
        "predictions_count": len(prediction_records),
        "deviations_count": len(deviations),
        "severity_breakdown": severity_breakdown,
    }


def _publish_deviations_best_effort(
    deviations: list,
    orders: list[dict[str, Any]],
    predictions_data: list[dict[str, Any]],
) -> None:
    """Publish deviations to Kafka. Best-effort — logs warning on failure."""
    if not deviations:
        return

    try:
        publisher = DeviationPublisher()

        async def _publish_all():
            try:
                for dev in deviations:
                    order_context = {"order_id": dev.prediction.order_id if dev.prediction else ""}
                    await publisher.publish(dev, order_context)
            finally:
                await publisher.close()

        # Run async publish in sync context
        try:
            loop = asyncio.get_running_loop()
            # Already in async context — schedule as task
            loop.create_task(_publish_all())
        except RuntimeError:
            # No running loop — create one
            asyncio.run(_publish_all())
    except Exception:
        logger.warning("Failed to publish deviation events to Kafka", exc_info=True)

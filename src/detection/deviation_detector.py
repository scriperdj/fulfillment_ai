"""Threshold-based deviation detection for predictions."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.orm import Session

from src.config.settings import get_settings
from src.db.models import Deviation


def detect_deviation(
    prediction_id: uuid.UUID,
    delay_probability: float,
    order_context: dict[str, Any],
    *,
    session: Session,
) -> Deviation | None:
    """Detect whether a prediction exceeds severity thresholds.

    Returns a persisted ``Deviation`` record, or ``None`` if the probability
    is below the info threshold.
    """
    settings = get_settings()

    if delay_probability >= settings.SEVERITY_CRITICAL_THRESHOLD:
        severity = "critical"
        threshold = settings.SEVERITY_CRITICAL_THRESHOLD
    elif delay_probability >= settings.SEVERITY_WARNING_THRESHOLD:
        severity = "warning"
        threshold = settings.SEVERITY_WARNING_THRESHOLD
    elif delay_probability >= settings.SEVERITY_INFO_THRESHOLD:
        severity = "info"
        threshold = settings.SEVERITY_INFO_THRESHOLD
    else:
        return None

    reason = f"Delay probability {delay_probability:.2f} exceeds {severity} threshold {threshold:.2f}"

    deviation = Deviation(
        prediction_id=prediction_id,
        batch_job_id=order_context.get("batch_job_id"),
        severity=severity,
        reason=reason,
    )
    session.add(deviation)
    session.flush()
    return deviation


def detect_batch(
    predictions: list[dict[str, Any]],
    *,
    session: Session,
) -> list[Deviation]:
    """Process multiple predictions and return created Deviations.

    Each dict in *predictions* must contain ``prediction_id``,
    ``delay_probability``, and optionally ``order_context``.
    """
    deviations: list[Deviation] = []
    for pred in predictions:
        dev = detect_deviation(
            prediction_id=pred["prediction_id"],
            delay_probability=pred["delay_probability"],
            order_context=pred.get("order_context", {}),
            session=session,
        )
        if dev is not None:
            deviations.append(dev)
    return deviations

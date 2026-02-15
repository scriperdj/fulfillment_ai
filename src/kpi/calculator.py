"""KPI calculation engine — per-order and running-aggregate metrics."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from src.config.settings import get_settings
from src.db.models import Prediction


# ---------------------------------------------------------------------------
# Per-order KPIs
# ---------------------------------------------------------------------------


def compute_order_kpis(order_data: dict[str, Any], delay_probability: float) -> dict[str, Any]:
    """Compute KPIs for a single order.

    Returns
    -------
    dict with keys:
        delay_probability  – pass-through value
        severity           – "critical" | "warning" | "info" | "low"
        fulfillment_gap    – bool (shipped AND delay_probability > threshold)
    """
    settings = get_settings()

    # Severity classification
    if delay_probability >= settings.SEVERITY_CRITICAL_THRESHOLD:
        severity = "critical"
    elif delay_probability >= settings.SEVERITY_WARNING_THRESHOLD:
        severity = "warning"
    elif delay_probability >= settings.SEVERITY_INFO_THRESHOLD:
        severity = "info"
    else:
        severity = "low"

    # Fulfillment gap: order is shipped but predicted to be delayed
    order_status = order_data.get("order_status", "")
    fulfillment_gap = (
        str(order_status).lower() == "shipped"
        and delay_probability > settings.FULFILLMENT_GAP_THRESHOLD
    )

    return {
        "delay_probability": delay_probability,
        "severity": severity,
        "fulfillment_gap": fulfillment_gap,
    }


# ---------------------------------------------------------------------------
# Running / aggregate KPIs
# ---------------------------------------------------------------------------


def compute_running_kpis(session: Session) -> dict[str, Any]:
    """Query predictions from the last N days and compute aggregate KPIs.

    Parameters
    ----------
    session:
        A SQLAlchemy *sync* session.

    Returns
    -------
    dict with aggregate metrics and segment breakdowns.
    """
    settings = get_settings()
    window_start = datetime.now(timezone.utc) - timedelta(days=settings.KPI_ROLLING_WINDOW_DAYS)

    # Base query: predictions within the rolling window
    base = session.query(Prediction).filter(Prediction.created_at >= window_start)
    predictions = base.all()

    total = len(predictions)
    if total == 0:
        return {
            "total_predictions": 0,
            "avg_delay_probability": 0.0,
            "on_time_rate": 0.0,
            "high_risk_count": 0,
            "severity_breakdown": {"critical": 0, "warning": 0, "info": 0},
            "by_warehouse_block": [],
            "by_mode_of_shipment": [],
            "by_product_importance": [],
        }

    # Aggregate metrics
    probs = [p.delay_probability for p in predictions]
    avg_prob = sum(probs) / total
    on_time_count = sum(1 for p in probs if p < settings.SEVERITY_WARNING_THRESHOLD)
    on_time_rate = on_time_count / total
    high_risk_count = sum(1 for p in probs if p >= settings.SEVERITY_CRITICAL_THRESHOLD)

    # Severity breakdown
    severity_counts = {"critical": 0, "warning": 0, "info": 0}
    for p in predictions:
        sev = p.severity
        if sev in severity_counts:
            severity_counts[sev] += 1

    # Segment breakdowns from features_json
    def _segment_breakdown(key: str) -> list[dict[str, Any]]:
        buckets: dict[str, list[float]] = {}
        for p in predictions:
            features = p.features_json or {}
            segment = str(features.get(key, "unknown"))
            buckets.setdefault(segment, []).append(p.delay_probability)
        return sorted(
            [
                {
                    "segment": seg,
                    "count": len(vals),
                    "avg_delay_probability": round(sum(vals) / len(vals), 4),
                }
                for seg, vals in buckets.items()
            ],
            key=lambda x: x["segment"],
        )

    return {
        "total_predictions": total,
        "avg_delay_probability": round(avg_prob, 4),
        "on_time_rate": round(on_time_rate, 4),
        "high_risk_count": high_risk_count,
        "severity_breakdown": severity_counts,
        "by_warehouse_block": _segment_breakdown("warehouse_block"),
        "by_mode_of_shipment": _segment_breakdown("mode_of_shipment"),
        "by_product_importance": _segment_breakdown("product_importance"),
    }

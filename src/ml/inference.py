"""ML inference — single and batch prediction using the trained delay classifier."""

from __future__ import annotations

import logging
from typing import Any

import pandas as pd

from src.config.settings import get_settings
from src.features.transform import (
    MODEL_FEATURE_NAMES,
    build_feature_dataframe,
    extract_features,
)
from src.ml.model_loader import load_model, load_preprocessor

logger = logging.getLogger(__name__)


def _classify_severity(delay_probability: float) -> str:
    """Map a delay probability to a severity label."""
    settings = get_settings()
    if delay_probability >= settings.SEVERITY_CRITICAL_THRESHOLD:
        return "critical"
    if delay_probability >= settings.SEVERITY_WARNING_THRESHOLD:
        return "warning"
    if delay_probability >= settings.SEVERITY_INFO_THRESHOLD:
        return "info"
    return "low"


def predict_single(order: dict[str, Any]) -> dict[str, Any]:
    """Run inference on a single enriched order dict.

    Parameters
    ----------
    order:
        An enriched order dictionary with fields from the 18-field schema.

    Returns
    -------
    dict with keys:
        order_id           – from the input order
        delay_probability  – float in [0, 1]
        severity           – "critical" | "warning" | "info" | "low"
        features_used      – the 10 extracted features (model column names)
    """
    features = extract_features(order)
    df = build_feature_dataframe([features])

    preprocessor = load_preprocessor()
    model = load_model()

    X = preprocessor.transform(df)
    proba = model.predict_proba(X)[0]

    # delay_probability = P(class=0) — probability of NOT reaching on time
    delay_probability = float(proba[0])
    severity = _classify_severity(delay_probability)

    return {
        "order_id": order.get("order_id", ""),
        "delay_probability": delay_probability,
        "severity": severity,
        "features_used": features,
    }


def predict_batch(orders: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Run vectorized inference on a list of enriched order dicts.

    Parameters
    ----------
    orders:
        List of enriched order dictionaries.

    Returns
    -------
    List of prediction dicts (same structure as ``predict_single``).
    """
    if not orders:
        return []

    features_list = [extract_features(order) for order in orders]
    df = build_feature_dataframe(features_list)

    preprocessor = load_preprocessor()
    model = load_model()

    X = preprocessor.transform(df)
    probas = model.predict_proba(X)

    results: list[dict[str, Any]] = []
    for i, order in enumerate(orders):
        delay_probability = float(probas[i][0])
        severity = _classify_severity(delay_probability)
        results.append(
            {
                "order_id": order.get("order_id", ""),
                "delay_probability": delay_probability,
                "severity": severity,
                "features_used": features_list[i],
            }
        )

    return results

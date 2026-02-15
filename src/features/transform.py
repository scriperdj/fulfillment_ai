"""Feature engineering — extract and transform enriched order data for ML inference."""

from __future__ import annotations

import logging
from typing import Any

import pandas as pd

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Mapping: enriched schema field (snake_case) → model column name (Title_case)
# ---------------------------------------------------------------------------

_FIELD_MAP: dict[str, str] = {
    "warehouse_block": "Warehouse_block",
    "mode_of_shipment": "Mode_of_Shipment",
    "customer_care_calls": "Customer_care_calls",
    "customer_rating": "Customer_rating",
    "cost_of_the_product": "Cost_of_the_Product",
    "prior_purchases": "Prior_purchases",
    "product_importance": "Product_importance",
    "gender": "Gender",
    "discount_offered": "Discount_offered",
    "weight_in_gms": "Weight_in_gms",
}

# Ordered list of model feature names (must match model_metadata.json)
MODEL_FEATURE_NAMES: list[str] = [
    "Warehouse_block",
    "Mode_of_Shipment",
    "Product_importance",
    "Gender",
    "Customer_care_calls",
    "Customer_rating",
    "Cost_of_the_Product",
    "Prior_purchases",
    "Discount_offered",
    "Weight_in_gms",
]

# Defaults for missing fields
_DEFAULTS: dict[str, Any] = {
    "Warehouse_block": "A",
    "Mode_of_Shipment": "Ship",
    "Customer_care_calls": 0,
    "Customer_rating": 3,
    "Cost_of_the_Product": 0,
    "Prior_purchases": 0,
    "Product_importance": "Low",
    "Gender": "M",
    "Discount_offered": 0,
    "Weight_in_gms": 0,
}

# Fields to preserve for KPI calculations
_RAW_FIELDS = [
    "order_id",
    "order_status",
    "warehouse_block",
    "mode_of_shipment",
    "product_importance",
    "customer_care_calls",
    "customer_rating",
    "cost_of_the_product",
    "prior_purchases",
    "gender",
    "discount_offered",
    "weight_in_gms",
    "ship_date",
    "delivery_date",
    "customer_id",
    "order_date",
    "product_category",
]


def extract_features(row: dict[str, Any]) -> dict[str, Any]:
    """Extract the 10 model features from an enriched order dict.

    Maps snake_case field names from the enriched schema to the Title_case
    column names the trained model expects. Missing fields are filled with
    sensible defaults.
    """
    features: dict[str, Any] = {}
    for src_field, model_col in _FIELD_MAP.items():
        value = row.get(src_field)
        if value is None:
            value = _DEFAULTS[model_col]
        features[model_col] = value
    return features


def build_feature_dataframe(rows: list[dict[str, Any]]) -> pd.DataFrame:
    """Convert a list of extracted feature dicts to a DataFrame.

    The returned DataFrame has columns in ``MODEL_FEATURE_NAMES`` order with
    appropriate dtypes.
    """
    if not rows:
        return pd.DataFrame(columns=MODEL_FEATURE_NAMES)

    df = pd.DataFrame(rows, columns=MODEL_FEATURE_NAMES)

    # Ensure numeric columns have correct dtype
    numeric_cols = [
        "Customer_care_calls",
        "Customer_rating",
        "Cost_of_the_Product",
        "Prior_purchases",
        "Discount_offered",
        "Weight_in_gms",
    ]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)

    return df


def preserve_raw_fields(row: dict[str, Any]) -> dict[str, Any]:
    """Return the original row fields needed for downstream KPI calculations."""
    return {field: row.get(field) for field in _RAW_FIELDS if field in row}

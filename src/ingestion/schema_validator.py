"""Schema validation for the 18-field enriched order data format."""

from __future__ import annotations

from typing import Any

import pandas as pd


# ---------------------------------------------------------------------------
# Schema definition
# ---------------------------------------------------------------------------

ENRICHED_SCHEMA: dict[str, dict[str, Any]] = {
    # Required fields
    "order_id": {"type": "str", "required": True},
    "warehouse_block": {"type": "str", "required": True},
    "mode_of_shipment": {"type": "str", "required": True},
    "customer_care_calls": {"type": "int", "required": True},
    "customer_rating": {"type": "int", "required": True},
    "cost_of_the_product": {"type": "int", "required": True},
    "prior_purchases": {"type": "int", "required": True},
    "product_importance": {"type": "str", "required": True},
    "gender": {"type": "str", "required": True},
    "discount_offered": {"type": "int", "required": True},
    "weight_in_gms": {"type": "int", "required": True},
    # Nullable fields
    "ship_date": {"type": "str", "required": False},
    "delivery_date": {"type": "str", "required": False},
    # Additional fields
    "customer_id": {"type": "str", "required": False},
    "order_date": {"type": "str", "required": False},
    "reached_on_time": {"type": "int", "required": False},
    "product_category": {"type": "str", "required": False},
    "order_status": {"type": "str", "required": False},
}

_TYPE_CHECKERS: dict[str, type] = {
    "str": str,
    "int": (int, float),  # type: ignore[assignment]  # accept float-like ints
    "float": (int, float),  # type: ignore[assignment]
}


# ---------------------------------------------------------------------------
# Row-level validation
# ---------------------------------------------------------------------------


def validate_row(row: dict[str, Any], row_index: int = 0) -> list[dict[str, Any]]:
    """Validate a single row against *ENRICHED_SCHEMA*.

    Returns a (possibly empty) list of error dicts:
        [{"row": int, "field": str, "message": str}, ...]
    """
    errors: list[dict[str, Any]] = []

    for field, spec in ENRICHED_SCHEMA.items():
        value = row.get(field)

        # --- required check ---
        if spec["required"]:
            if value is None or (isinstance(value, float) and pd.isna(value)):
                errors.append(
                    {"row": row_index, "field": field, "message": f"Missing required field: {field}"}
                )
                continue
            if isinstance(value, str) and value.strip() == "":
                errors.append(
                    {"row": row_index, "field": field, "message": f"Empty required field: {field}"}
                )
                continue

        # --- skip type check for missing optional fields ---
        if value is None or (isinstance(value, float) and pd.isna(value)):
            continue

        # --- type check ---
        expected = spec["type"]
        if expected == "int":
            # Accept numeric values that can be interpreted as integers
            if not isinstance(value, (int, float)):
                try:
                    int(value)
                except (ValueError, TypeError):
                    errors.append(
                        {
                            "row": row_index,
                            "field": field,
                            "message": f"Invalid type for {field}: expected int, got {type(value).__name__}",
                        }
                    )
        elif expected == "float":
            if not isinstance(value, (int, float)):
                try:
                    float(value)
                except (ValueError, TypeError):
                    errors.append(
                        {
                            "row": row_index,
                            "field": field,
                            "message": f"Invalid type for {field}: expected float, got {type(value).__name__}",
                        }
                    )
        elif expected == "str":
            # Accept anything that can be stringified; only reject None (already handled)
            pass

    return errors


# ---------------------------------------------------------------------------
# DataFrame-level validation
# ---------------------------------------------------------------------------


def validate_csv(df: pd.DataFrame) -> dict[str, Any]:
    """Validate an entire DataFrame against *ENRICHED_SCHEMA*.

    Returns::

        {
            "valid": bool,
            "error_count": int,
            "errors": [{"row": int, "field": str, "message": str}, ...],
        }
    """
    all_errors: list[dict[str, Any]] = []

    # Check for missing required columns
    required_cols = {f for f, s in ENRICHED_SCHEMA.items() if s["required"]}
    missing_cols = required_cols - set(df.columns)
    if missing_cols:
        for col in sorted(missing_cols):
            for idx in range(len(df)):
                all_errors.append(
                    {"row": idx, "field": col, "message": f"Missing required field: {col}"}
                )

    # Validate each row
    for idx, row in df.iterrows():
        row_dict = row.to_dict()
        row_errors = validate_row(row_dict, row_index=int(idx))
        all_errors.extend(row_errors)

    return {
        "valid": len(all_errors) == 0,
        "error_count": len(all_errors),
        "errors": all_errors,
    }

"""Pydantic request / response models for the REST API."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


# ---------------------------------------------------------------------------
# Generic wrappers
# ---------------------------------------------------------------------------


class ErrorResponse(BaseModel):
    detail: str


class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T] = []  # type: ignore[valid-type]
    total: int = 0
    skip: int = 0
    limit: int = 50


# ---------------------------------------------------------------------------
# Order / Prediction
# ---------------------------------------------------------------------------


class OrderInput(BaseModel):
    order_id: str
    warehouse_block: str
    mode_of_shipment: str
    customer_care_calls: int
    customer_rating: int
    cost_of_the_product: int
    prior_purchases: int
    product_importance: str
    gender: str
    discount_offered: int
    weight_in_gms: int
    # Optional enriched fields
    customer_id: str | None = None
    order_date: str | None = None
    ship_date: str | None = None
    delivery_date: str | None = None
    reached_on_time: int | None = None
    product_category: str | None = None
    order_status: str | None = None


class PredictionResponse(BaseModel):
    id: str
    order_id: str
    delay_probability: float
    severity: str
    source: str
    features_json: dict[str, Any] | None = None
    created_at: datetime | None = None


class PipelineSummaryResponse(BaseModel):
    predictions_count: int
    deviations_count: int
    severity_breakdown: dict[str, int]


# ---------------------------------------------------------------------------
# Batch
# ---------------------------------------------------------------------------


class BatchUploadResponse(BaseModel):
    batch_job_id: str
    filename: str
    row_count: int
    status: str


class BatchStatusResponse(BaseModel):
    batch_job_id: str
    status: str
    filename: str
    row_count: int
    created_at: datetime | None = None
    completed_at: datetime | None = None
    error_message: str | None = None


# ---------------------------------------------------------------------------
# Deviation
# ---------------------------------------------------------------------------


class DeviationResponse(BaseModel):
    id: str
    prediction_id: str
    severity: str
    reason: str
    status: str
    created_at: datetime | None = None


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------


class AgentTriggerRequest(BaseModel):
    severity: str
    reason: str
    order_id: str
    delay_probability: float = 0.0
    deviation_id: str | None = None


class AgentResultResponse(BaseModel):
    agent_type: str
    action: str
    details: dict[str, Any] | None = None


class AgentTriggerResponse(BaseModel):
    results: list[AgentResultResponse]


class AgentResponseRecord(BaseModel):
    id: str
    deviation_id: str
    agent_type: str
    action: str
    details_json: dict[str, Any] | None = None
    created_at: datetime | None = None


class AgentActivity(BaseModel):
    id: str
    agent_type: str
    action: str
    order_id: str
    created_at: datetime
    details: dict[str, Any] | None = None


# ---------------------------------------------------------------------------
# Order detail (aggregated view)
# ---------------------------------------------------------------------------


class OrderDetailResponse(BaseModel):
    order_id: str
    predictions: list[PredictionResponse]
    deviations: list[DeviationResponse]
    agent_responses: list[AgentResponseRecord]


# ---------------------------------------------------------------------------
# KPI
# ---------------------------------------------------------------------------


class KPIDashboardResponse(BaseModel):
    total_predictions: int
    avg_delay_probability: float
    on_time_rate: float
    high_risk_count: int
    severity_breakdown: dict[str, int]
    by_warehouse_block: list[dict[str, Any]]
    by_mode_of_shipment: list[dict[str, Any]]
    by_product_importance: list[dict[str, Any]]


# ---------------------------------------------------------------------------
# Knowledge
# ---------------------------------------------------------------------------


class KnowledgeSearchRequest(BaseModel):
    query: str
    k: int = Field(default=5, ge=1, le=20)
    filter_metadata: dict[str, str] | None = None


class KnowledgeSearchResponse(BaseModel):
    results: list[dict[str, Any]]


class KnowledgeIngestResponse(BaseModel):
    chunks_ingested: int

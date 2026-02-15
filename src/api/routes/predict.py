"""Prediction endpoints — single and batch."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from src.api.deps import get_db
from src.api.schemas import OrderInput, PipelineSummaryResponse, PredictionResponse
from src.db.models import Prediction
from src.pipeline.processor import run_pipeline

router = APIRouter(tags=["predict"])


@router.post("/predict", response_model=PredictionResponse)
def predict_single(order: OrderInput, session: Session = Depends(get_db)):
    order_dict = order.model_dump(exclude_none=True)
    run_pipeline([order_dict], session=session)
    pred = (
        session.query(Prediction)
        .filter(Prediction.order_id == order.order_id)
        .order_by(Prediction.created_at.desc())
        .first()
    )
    return PredictionResponse(
        id=str(pred.id),
        order_id=pred.order_id,
        delay_probability=pred.delay_probability,
        severity=pred.severity,
        source=pred.source,
        features_json=pred.features_json,
        created_at=pred.created_at,
    )


@router.post("/predict/batch", response_model=PipelineSummaryResponse)
def predict_batch(orders: list[OrderInput], session: Session = Depends(get_db)):
    order_dicts = [o.model_dump(exclude_none=True) for o in orders]
    summary = run_pipeline(order_dicts, session=session)
    return PipelineSummaryResponse(**summary)

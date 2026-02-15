"""Order detail endpoint — aggregated view of predictions, deviations, agent responses."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.api.deps import get_db
from src.api.schemas import (
    AgentResponseRecord,
    DeviationResponse,
    OrderDetailResponse,
    PredictionResponse,
)
from src.db.models import AgentResponse, Deviation, Prediction

router = APIRouter(tags=["orders"])


@router.get("/orders/{order_id}", response_model=OrderDetailResponse)
def get_order(order_id: str, session: Session = Depends(get_db)):
    preds = (
        session.query(Prediction)
        .filter(Prediction.order_id == order_id)
        .order_by(Prediction.created_at.desc())
        .all()
    )
    if not preds:
        raise HTTPException(status_code=404, detail="Order not found")

    pred_ids = [p.id for p in preds]
    devs = session.query(Deviation).filter(Deviation.prediction_id.in_(pred_ids)).all()
    dev_ids = [d.id for d in devs]
    responses = (
        session.query(AgentResponse).filter(AgentResponse.deviation_id.in_(dev_ids)).all()
        if dev_ids
        else []
    )

    return OrderDetailResponse(
        order_id=order_id,
        predictions=[
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
        ],
        deviations=[
            DeviationResponse(
                id=str(d.id),
                prediction_id=str(d.prediction_id),
                severity=d.severity,
                reason=d.reason,
                status=d.status,
                created_at=d.created_at,
            )
            for d in devs
        ],
        agent_responses=[
            AgentResponseRecord(
                id=str(r.id),
                deviation_id=str(r.deviation_id),
                agent_type=r.agent_type,
                action=r.action,
                details_json=r.details_json,
                created_at=r.created_at,
            )
            for r in responses
        ],
    )

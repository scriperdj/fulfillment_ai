"""Deviation listing endpoints with filtering and pagination."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from src.api.deps import get_db
from src.api.schemas import DeviationResponse, PaginatedResponse
from src.db.models import Deviation, Prediction

router = APIRouter(tags=["deviations"])


@router.get("/deviations", response_model=PaginatedResponse[DeviationResponse])
def list_deviations(
    severity: str | None = Query(default=None),
    order_id: str | None = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    session: Session = Depends(get_db),
):
    q = session.query(Deviation, Prediction.order_id).join(
        Prediction, Deviation.prediction_id == Prediction.id
    )

    if severity:
        q = q.filter(Deviation.severity == severity)
    if order_id:
        q = q.filter(Prediction.order_id == order_id)

    total = q.count()
    rows = q.order_by(Deviation.created_at.desc()).offset(skip).limit(limit).all()

    items = [
        DeviationResponse(
            id=str(d.id),
            prediction_id=str(d.prediction_id),
            order_id=oid,
            severity=d.severity,
            reason=d.reason,
            status=d.status,
            created_at=d.created_at,
        )
        for d, oid in rows
    ]
    return PaginatedResponse[DeviationResponse](
        items=items, total=total, skip=skip, limit=limit
    )

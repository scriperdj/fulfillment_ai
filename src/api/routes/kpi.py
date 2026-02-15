"""KPI dashboard endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from src.api.deps import get_db
from src.api.schemas import KPIDashboardResponse
from src.kpi.calculator import compute_running_kpis

router = APIRouter(tags=["kpi"])


@router.get("/kpi/dashboard", response_model=KPIDashboardResponse)
def kpi_dashboard(session: Session = Depends(get_db)):
    data = compute_running_kpis(session)
    return KPIDashboardResponse(**data)

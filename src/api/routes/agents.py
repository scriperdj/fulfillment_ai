"""Agent trigger and activity endpoints."""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from src.agents.orchestrator import AgentOrchestrator
from src.api.deps import get_db
from src.api.schemas import (
    AgentResultResponse,
    AgentTriggerRequest,
    AgentTriggerResponse,
    AgentActivity,
)

router = APIRouter(prefix="/agents", tags=["agents"])


@router.post("/trigger", response_model=AgentTriggerResponse)
def trigger_agents(request: AgentTriggerRequest, session: Session = Depends(get_db)):
    from src.db.models import Deviation, Prediction

    ctx = request.model_dump()

    # If no deviation_id was supplied, try to find one for this order
    # (or create one) so that agent responses actually get persisted.
    if ctx.get("deviation_id") is None:
        # Look for the latest prediction for this order
        pred = (
            session.query(Prediction)
            .filter(Prediction.order_id == request.order_id)
            .order_by(Prediction.created_at.desc())
            .first()
        )
        if pred is not None:
            # Look for an existing deviation on this prediction
            dev = (
                session.query(Deviation)
                .filter(Deviation.prediction_id == pred.id)
                .order_by(Deviation.created_at.desc())
                .first()
            )
            if dev is None:
                # Create a deviation so agent responses can be stored
                dev = Deviation(
                    prediction_id=pred.id,
                    severity=request.severity,
                    reason=request.reason or "Manual agent trigger",
                    status="new",
                )
                session.add(dev)
                session.flush()
            ctx["deviation_id"] = dev.id

    orch = AgentOrchestrator(session=session)
    results = asyncio.run(orch.orchestrate(ctx))
    return AgentTriggerResponse(
        results=[
            AgentResultResponse(
                agent_type=r["agent_type"],
                action=r["action"],
                details=r.get("details"),
            )
            for r in results
        ]
    )


@router.get("/activity", response_model=list[AgentActivity])
def get_agent_activity(
    limit: int = 50, session: Session = Depends(get_db)
) -> list[AgentActivity]:
    from sqlalchemy import desc, select

    from src.db.models import AgentResponse, Deviation, Prediction

    stmt = (
        select(AgentResponse, Prediction.order_id)
        .join(Deviation, AgentResponse.deviation_id == Deviation.id)
        .join(Prediction, Deviation.prediction_id == Prediction.id)
        .order_by(desc(AgentResponse.created_at))
        .limit(limit)
    )
    results = session.execute(stmt).all()

    activity = []
    for row in results:
        agent_resp: AgentResponse = row[0]
        order_id: str = row[1]
        activity.append(
            AgentActivity(
                id=str(agent_resp.id),
                agent_type=agent_resp.agent_type,
                action=agent_resp.action,
                order_id=order_id,
                created_at=agent_resp.created_at,
                details=agent_resp.details_json,
            )
        )
    return activity

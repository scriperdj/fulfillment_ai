"""Agent trigger endpoint."""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from src.agents.orchestrator import AgentOrchestrator
from src.api.deps import get_db
from src.api.schemas import AgentResultResponse, AgentTriggerRequest, AgentTriggerResponse

router = APIRouter(prefix="/agents", tags=["agents"])


@router.post("/trigger", response_model=AgentTriggerResponse)
def trigger_agents(request: AgentTriggerRequest, session: Session = Depends(get_db)):
    ctx = request.model_dump()
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

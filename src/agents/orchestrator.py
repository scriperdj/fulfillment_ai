"""Agent orchestrator — routes deviations to specialist agents and stores results."""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.orm import Session

from src.agents.specialists import (
    CustomerAgent,
    EscalationAgent,
    PaymentAgent,
    ShipmentAgent,
)
from src.db.models import AgentResponse

logger = logging.getLogger(__name__)

# Severity-based routing rules (fallback when LLM is unavailable)
_ROUTING_RULES: dict[str, list[type]] = {
    "critical": [ShipmentAgent, CustomerAgent, EscalationAgent],
    "warning": [ShipmentAgent, CustomerAgent],
    "info": [],  # No agent action for info-level deviations
}


class AgentOrchestrator:
    """Routes deviations to specialist agents and stores their responses."""

    def __init__(self, llm: Any | None = None, session: Session | None = None) -> None:
        self._llm = llm
        self._session = session

    def _select_agents(self, deviation_context: dict[str, Any]) -> list:
        """Select which agents to invoke based on deviation severity."""
        severity = deviation_context.get("severity", "info")
        agent_classes = _ROUTING_RULES.get(severity, [])
        return [cls(llm=self._llm) for cls in agent_classes]

    async def orchestrate(self, deviation_context: dict[str, Any]) -> list[dict[str, Any]]:
        """Route a deviation to specialist agents and aggregate results.

        Parameters
        ----------
        deviation_context:
            Dict with keys like severity, reason, order_id, delay_probability,
            deviation_id.

        Returns
        -------
        List of agent result dicts.
        """
        agents = self._select_agents(deviation_context)
        if not agents:
            logger.info(
                "No agents selected for severity=%s order=%s",
                deviation_context.get("severity"),
                deviation_context.get("order_id"),
            )
            return []

        results: list[dict[str, Any]] = []
        for agent in agents:
            try:
                result = await agent.run(deviation_context)
                results.append(result)

                # Store in DB if session is available
                if self._session is not None:
                    self._store_response(result, deviation_context)

            except Exception:
                logger.warning(
                    "Agent %s failed for order=%s",
                    agent.AGENT_TYPE,
                    deviation_context.get("order_id"),
                    exc_info=True,
                )

        return results

    def _store_response(
        self, result: dict[str, Any], deviation_context: dict[str, Any]
    ) -> None:
        """Persist an agent response to the agent_responses table."""
        deviation_id = deviation_context.get("deviation_id")
        if deviation_id is None:
            logger.warning("No deviation_id in context, skipping DB storage")
            return

        response = AgentResponse(
            deviation_id=deviation_id,
            agent_type=result["agent_type"],
            action=result["action"],
            details_json=result.get("details"),
            conversation_history=result.get("conversation_history"),
        )
        self._session.add(response)
        self._session.flush()

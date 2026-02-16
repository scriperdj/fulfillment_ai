"""Agent orchestrator — routes deviations to specialist agents and stores results."""

from __future__ import annotations

import logging
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import tool
from sqlalchemy.orm import Session

from src.agents.specialists import (
    CustomerAgent,
    EscalationAgent,
    PaymentAgent,
    ShipmentAgent,
)
from src.db.models import AgentResponse

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Agent registry
# ---------------------------------------------------------------------------

_AGENT_CLASS_MAP: dict[str, type] = {
    "shipment": ShipmentAgent,
    "customer": CustomerAgent,
    "payment": PaymentAgent,
    "escalation": EscalationAgent,
}

_AGENT_DESCRIPTIONS: dict[str, str] = {
    "shipment": "Handles shipment delays: reschedules to faster modes, checks carrier status, transfers warehouse blocks.",
    "customer": "Handles customer communication: drafts apology emails, sends notifications, logs interactions.",
    "payment": "Handles payment issues: checks refund eligibility, issues refunds, applies store credits.",
    "escalation": "Handles critical escalations: creates support tickets, assigns human agents, flags priority.",
}

# Severity-based routing rules (fallback when LLM is unavailable)
_ROUTING_RULES: dict[str, list[type]] = {
    "critical": [ShipmentAgent, CustomerAgent, EscalationAgent],
    "warning": [ShipmentAgent, CustomerAgent],
    "info": [],  # No agent action for info-level deviations
}

# ---------------------------------------------------------------------------
# Routing tool for LLM-based selection
# ---------------------------------------------------------------------------

_ROUTING_SYSTEM_PROMPT = (
    "You are a routing agent for a fulfillment AI system. "
    "Given a deviation event, select which specialist agents should handle it.\n\n"
    "Available agents:\n"
    + "\n".join(f'- "{name}": {desc}' for name, desc in _AGENT_DESCRIPTIONS.items())
    + "\n\nSelect the most relevant agents for the deviation. "
    "Use the select_agents tool with a list of agent names."
)


@tool
def select_agents(agents: list[str]) -> dict:
    """Select which specialist agents should handle this deviation.

    Valid values: "shipment", "customer", "payment", "escalation".
    """
    valid = [a for a in agents if a in _AGENT_CLASS_MAP]
    return {"selected_agents": valid}


class AgentOrchestrator:
    """Routes deviations to specialist agents and stores their responses."""

    def __init__(self, llm: Any | None = None, session: Session | None = None) -> None:
        self._llm = llm
        self._session = session

    async def _llm_select_agents(self, deviation_context: dict[str, Any]) -> list[str]:
        """Use the LLM to select agents via the select_agents tool."""
        llm = self._llm
        if llm is None:
            from langchain_openai import ChatOpenAI
            from src.config.settings import get_settings
            settings = get_settings()
            llm = ChatOpenAI(model=settings.OPENAI_MODEL, temperature=0)

        llm_with_tools = llm.bind_tools([select_agents])

        user_message = (
            f"Deviation detected:\n"
            f"- Severity: {deviation_context.get('severity', 'unknown')}\n"
            f"- Reason: {deviation_context.get('reason', 'unknown')}\n"
            f"- Order ID: {deviation_context.get('order_id', 'unknown')}\n"
            f"- Delay Probability: {deviation_context.get('delay_probability', 'unknown')}\n\n"
            f"Select the appropriate agents to handle this deviation."
        )

        messages = [
            SystemMessage(content=_ROUTING_SYSTEM_PROMPT),
            HumanMessage(content=user_message),
        ]

        response = await llm_with_tools.ainvoke(messages)

        tool_calls = response.tool_calls if hasattr(response, "tool_calls") else []
        for tc in tool_calls:
            args = tc.get("args", {}) if isinstance(tc, dict) else getattr(tc, "args", {})
            agents_list = args.get("agents", [])
            # Filter to valid agent names
            return [a for a in agents_list if a in _AGENT_CLASS_MAP]

        return []

    def _severity_select_agents(self, deviation_context: dict[str, Any]) -> list:
        """Select agents using hardcoded severity rules (fallback)."""
        severity = deviation_context.get("severity", "info")
        agent_classes = _ROUTING_RULES.get(severity, [])
        return [cls(llm=self._llm) for cls in agent_classes]

    async def _select_agents(self, deviation_context: dict[str, Any]) -> list:
        """Select which agents to invoke, preferring LLM-based routing."""
        try:
            agent_types = await self._llm_select_agents(deviation_context)
            if agent_types:
                return [_AGENT_CLASS_MAP[t](llm=self._llm) for t in agent_types]
            # Empty selection — fall back to severity rules
            logger.info("LLM returned empty agent selection, using severity fallback")
        except Exception:
            logger.warning("LLM routing failed, using severity fallback", exc_info=True)

        return self._severity_select_agents(deviation_context)

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
        agents = await self._select_agents(deviation_context)
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

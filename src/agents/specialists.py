"""Specialist agents — LLM-powered domain experts with RAG context injection."""

from __future__ import annotations

import logging
from typing import Any

from src.agents.tools import (
    CUSTOMER_TOOLS,
    ESCALATION_TOOLS,
    PAYMENT_TOOLS,
    SHIPMENT_TOOLS,
)

logger = logging.getLogger(__name__)


class _BaseAgent:
    """Base class for specialist agents."""

    SYSTEM_PROMPT: str = ""
    AGENT_TYPE: str = ""
    RAG_FILTER: dict[str, str] = {}
    TOOLS: list = []

    def __init__(self, llm: Any | None = None) -> None:
        self._llm = llm

    def _get_llm(self) -> Any:
        """Return the configured LLM, creating a default if needed."""
        if self._llm is not None:
            return self._llm
        from langchain_openai import ChatOpenAI
        from src.config.settings import get_settings

        settings = get_settings()
        self._llm = ChatOpenAI(model=settings.OPENAI_MODEL, temperature=0)
        return self._llm

    def _retrieve_context(self, deviation_context: dict[str, Any]) -> str:
        """Query RAG knowledge base for relevant context."""
        try:
            from src.rag.retrieval import retrieve

            query = (
                f"{deviation_context.get('severity', '')} "
                f"{deviation_context.get('reason', '')} "
                f"order {deviation_context.get('order_id', '')}"
            )
            results = retrieve(
                query,
                k=3,
                filter_metadata=self.RAG_FILTER if self.RAG_FILTER else None,
            )
            if results:
                docs = "\n\n".join(
                    f"[{i+1}] {r['content']}" for i, r in enumerate(results)
                )
                return f"Relevant knowledge:\n{docs}"
        except Exception:
            logger.warning("RAG retrieval failed for %s", self.AGENT_TYPE, exc_info=True)
        return ""

    async def run(self, deviation_context: dict[str, Any]) -> dict[str, Any]:
        """Execute the agent with RAG context injection.

        Parameters
        ----------
        deviation_context:
            Dict with keys like severity, reason, order_id, delay_probability.

        Returns
        -------
        Dict with agent_type, action, details, conversation_history.
        """
        llm = self._get_llm()
        rag_context = self._retrieve_context(deviation_context)

        # Build the prompt
        messages = [
            {"role": "system", "content": self.SYSTEM_PROMPT},
        ]
        if rag_context:
            messages.append({"role": "system", "content": rag_context})

        user_message = (
            f"Deviation detected:\n"
            f"- Severity: {deviation_context.get('severity', 'unknown')}\n"
            f"- Reason: {deviation_context.get('reason', 'unknown')}\n"
            f"- Order ID: {deviation_context.get('order_id', 'unknown')}\n"
            f"- Delay Probability: {deviation_context.get('delay_probability', 'unknown')}\n\n"
            f"Analyze the situation and take appropriate action using your available tools."
        )
        messages.append({"role": "user", "content": user_message})

        try:
            llm_with_tools = llm.bind_tools(self.TOOLS)
            from langchain_core.messages import HumanMessage, SystemMessage

            lc_messages = []
            for msg in messages:
                if msg["role"] == "system":
                    lc_messages.append(SystemMessage(content=msg["content"]))
                else:
                    lc_messages.append(HumanMessage(content=msg["content"]))

            response = await llm_with_tools.ainvoke(lc_messages)
            action = response.content if hasattr(response, "content") else str(response)
            tool_calls = response.tool_calls if hasattr(response, "tool_calls") else []

            # Execute tool calls
            details: dict[str, Any] = {"tool_calls": []}
            for tc in tool_calls:
                tool_name = tc.get("name", "") if isinstance(tc, dict) else getattr(tc, "name", "")
                tool_args = tc.get("args", {}) if isinstance(tc, dict) else getattr(tc, "args", {})
                # Find and invoke the tool
                for t in self.TOOLS:
                    if t.name == tool_name:
                        result = t.invoke(tool_args)
                        details["tool_calls"].append(
                            {"tool": tool_name, "args": tool_args, "result": result}
                        )
                        break

            return {
                "agent_type": self.AGENT_TYPE,
                "action": action[:200] if action else f"{self.AGENT_TYPE}_action_taken",
                "details": details,
                "conversation_history": messages + [{"role": "assistant", "content": action}],
            }
        except Exception as e:
            logger.warning("LLM call failed for %s: %s", self.AGENT_TYPE, e, exc_info=True)
            # Fallback: return a default action without LLM
            return self._fallback_action(deviation_context)

    def _fallback_action(self, deviation_context: dict[str, Any]) -> dict[str, Any]:
        """Generate a rule-based fallback action when LLM is unavailable."""
        return {
            "agent_type": self.AGENT_TYPE,
            "action": f"{self.AGENT_TYPE}_fallback_action",
            "details": {"fallback": True, "deviation_context": deviation_context},
            "conversation_history": [],
        }


class ShipmentAgent(_BaseAgent):
    """Handles shipment-related deviations: rescheduling, carrier issues, warehouse transfers."""

    AGENT_TYPE = "shipment"
    TOOLS = SHIPMENT_TOOLS
    RAG_FILTER = {"agent_type": "shipment"}
    SYSTEM_PROMPT = (
        "You are the Shipment Agent for a fulfillment AI system. "
        "Your role is to handle shipment delays and logistics issues. "
        "You can reschedule shipments to faster modes, check carrier status, "
        "and transfer orders between warehouse blocks. "
        "Always prioritize getting the order to the customer as fast as possible."
    )

    def _fallback_action(self, ctx: dict[str, Any]) -> dict[str, Any]:
        order_id = ctx.get("order_id", "unknown")
        result = self.TOOLS[0].invoke(
            {"order_id": order_id, "new_mode": "Flight", "reason": f"Delay detected: {ctx.get('reason', '')}"}
        )
        return {
            "agent_type": self.AGENT_TYPE,
            "action": "rescheduled_to_flight",
            "details": {"tool_calls": [{"tool": "reschedule_shipment", "result": result}]},
            "conversation_history": [],
        }


class CustomerAgent(_BaseAgent):
    """Handles customer communication: emails, notifications, interaction logging."""

    AGENT_TYPE = "customer"
    TOOLS = CUSTOMER_TOOLS
    RAG_FILTER = {"agent_type": "customer"}
    SYSTEM_PROMPT = (
        "You are the Customer Service Agent for a fulfillment AI system. "
        "Your role is to communicate with customers about order issues. "
        "You can draft and send emails, push notifications, and log interactions. "
        "Always be empathetic and provide clear information about the situation."
    )

    def _fallback_action(self, ctx: dict[str, Any]) -> dict[str, Any]:
        order_id = ctx.get("order_id", "unknown")
        result = self.TOOLS[0].invoke(
            {"order_id": order_id, "template": "apology", "context": f"Delay detected: {ctx.get('reason', '')}"}
        )
        return {
            "agent_type": self.AGENT_TYPE,
            "action": "apology_email_drafted",
            "details": {"tool_calls": [{"tool": "draft_email", "result": result}]},
            "conversation_history": [],
        }


class PaymentAgent(_BaseAgent):
    """Handles payment issues: refund eligibility, refund processing, store credits."""

    AGENT_TYPE = "payment"
    TOOLS = PAYMENT_TOOLS
    RAG_FILTER = {"agent_type": "payment"}
    SYSTEM_PROMPT = (
        "You are the Payment Agent for a fulfillment AI system. "
        "Your role is to handle refunds and payment-related issues. "
        "You can check refund eligibility, issue refunds, and apply store credits. "
        "Follow refund policy guidelines and always verify eligibility first."
    )

    def _fallback_action(self, ctx: dict[str, Any]) -> dict[str, Any]:
        order_id = ctx.get("order_id", "unknown")
        result = self.TOOLS[0].invoke({"order_id": order_id, "amount": 0.0})
        return {
            "agent_type": self.AGENT_TYPE,
            "action": "refund_eligibility_checked",
            "details": {"tool_calls": [{"tool": "check_refund_eligibility", "result": result}]},
            "conversation_history": [],
        }


class EscalationAgent(_BaseAgent):
    """Handles escalations: ticket creation, human assignment, priority flagging."""

    AGENT_TYPE = "escalation"
    TOOLS = ESCALATION_TOOLS
    RAG_FILTER = {"agent_type": "escalation"}
    SYSTEM_PROMPT = (
        "You are the Escalation Agent for a fulfillment AI system. "
        "Your role is to handle critical issues that need human intervention. "
        "You can create support tickets, assign human agents, and flag priorities. "
        "Ensure all critical issues are properly escalated with full context."
    )

    def _fallback_action(self, ctx: dict[str, Any]) -> dict[str, Any]:
        order_id = ctx.get("order_id", "unknown")
        severity = ctx.get("severity", "warning")
        result = self.TOOLS[0].invoke(
            {"order_id": order_id, "severity": severity, "description": ctx.get("reason", "Escalation required")}
        )
        return {
            "agent_type": self.AGENT_TYPE,
            "action": "ticket_created",
            "details": {"tool_calls": [{"tool": "create_ticket", "result": result}]},
            "conversation_history": [],
        }

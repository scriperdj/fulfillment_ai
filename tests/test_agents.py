"""Tests for src/agents — tools, specialists, and orchestrator."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from src.agents.orchestrator import AgentOrchestrator, _ROUTING_RULES
from src.agents.specialists import (
    CustomerAgent,
    EscalationAgent,
    PaymentAgent,
    ShipmentAgent,
)
from src.agents.tools import (
    ALL_TOOLS,
    CUSTOMER_TOOLS,
    ESCALATION_TOOLS,
    PAYMENT_TOOLS,
    SHIPMENT_TOOLS,
    apply_credit,
    assign_human,
    check_carrier_status,
    check_refund_eligibility,
    create_ticket,
    draft_email,
    flag_priority,
    issue_refund,
    log_interaction,
    reschedule_shipment,
    send_notification,
    transfer_warehouse,
)
from src.db.models import AgentResponse, Base, Deviation, Prediction


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def engine():
    eng = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(bind=eng)
    yield eng
    eng.dispose()


@pytest.fixture()
def session(engine):
    connection = engine.connect()
    transaction = connection.begin()
    sess = Session(bind=connection)
    yield sess
    sess.close()
    transaction.rollback()
    connection.close()


SAMPLE_DEVIATION_CONTEXT = {
    "severity": "critical",
    "reason": "Delay probability 0.85 exceeds critical threshold 0.70",
    "order_id": "ORD-AGT-001",
    "delay_probability": 0.85,
    "deviation_id": None,  # Set per-test when DB is available
}


# ---------------------------------------------------------------------------
# Tool tests — Shipment
# ---------------------------------------------------------------------------


class TestShipmentTools:
    def test_reschedule_shipment_returns_dict(self):
        result = reschedule_shipment.invoke(
            {"order_id": "ORD-001", "new_mode": "Flight", "reason": "Delay detected"}
        )
        assert isinstance(result, dict)
        assert result["status"] == "rescheduled"
        assert result["new_mode"] == "Flight"
        assert "carrier" in result
        assert "new_eta" in result

    def test_check_carrier_status_returns_dict(self):
        result = check_carrier_status.invoke(
            {"order_id": "ORD-001", "carrier": "FedEx"}
        )
        assert isinstance(result, dict)
        assert result["carrier"] == "FedEx"
        assert "status" in result
        assert "current_location" in result
        assert "eta" in result

    def test_transfer_warehouse_returns_dict(self):
        result = transfer_warehouse.invoke(
            {"order_id": "ORD-001", "from_block": "A", "to_block": "B"}
        )
        assert isinstance(result, dict)
        assert result["status"] == "transferred"
        assert result["new_block"] == "B"
        assert "processing_time" in result


# ---------------------------------------------------------------------------
# Tool tests — Customer
# ---------------------------------------------------------------------------


class TestCustomerTools:
    def test_draft_email_returns_dict(self):
        result = draft_email.invoke(
            {"order_id": "ORD-001", "template": "apology", "context": "Delay detected"}
        )
        assert isinstance(result, dict)
        assert "subject" in result
        assert "body" in result
        assert "recipient" in result

    def test_send_notification_returns_dict(self):
        result = send_notification.invoke(
            {"order_id": "ORD-001", "channel": "email", "message": "Your order is delayed"}
        )
        assert isinstance(result, dict)
        assert result["status"] == "sent"
        assert result["channel"] == "email"
        assert "sent_at" in result

    def test_log_interaction_returns_dict(self):
        result = log_interaction.invoke(
            {"order_id": "ORD-001", "interaction_type": "email", "details": "Sent apology"}
        )
        assert isinstance(result, dict)
        assert result["logged"] is True
        assert "interaction_id" in result


# ---------------------------------------------------------------------------
# Tool tests — Payment
# ---------------------------------------------------------------------------


class TestPaymentTools:
    def test_check_refund_eligibility_returns_dict(self):
        result = check_refund_eligibility.invoke(
            {"order_id": "ORD-001", "amount": 100.0}
        )
        assert isinstance(result, dict)
        assert result["eligible"] is True
        assert "reason" in result
        assert "max_amount" in result

    def test_check_refund_over_limit(self):
        result = check_refund_eligibility.invoke(
            {"order_id": "ORD-001", "amount": 1000.0}
        )
        assert result["eligible"] is False

    def test_issue_refund_returns_dict(self):
        result = issue_refund.invoke(
            {"order_id": "ORD-001", "amount": 50.0, "method": "credit_card"}
        )
        assert isinstance(result, dict)
        assert result["status"] == "processed"
        assert "refund_id" in result
        assert result["amount"] == 50.0

    def test_apply_credit_returns_dict(self):
        result = apply_credit.invoke(
            {"order_id": "ORD-001", "amount": 25.0, "reason": "Delay compensation"}
        )
        assert isinstance(result, dict)
        assert result["status"] == "applied"
        assert "credit_id" in result
        assert "expiry" in result


# ---------------------------------------------------------------------------
# Tool tests — Escalation
# ---------------------------------------------------------------------------


class TestEscalationTools:
    def test_create_ticket_returns_dict(self):
        result = create_ticket.invoke(
            {"order_id": "ORD-001", "severity": "critical", "description": "Urgent delay"}
        )
        assert isinstance(result, dict)
        assert "ticket_id" in result
        assert result["priority"] == "P1"
        assert result["assigned_team"] == "Senior Support"

    def test_assign_human_returns_dict(self):
        result = assign_human.invoke(
            {"order_id": "ORD-001", "team": "Support", "reason": "Customer escalation"}
        )
        assert isinstance(result, dict)
        assert result["status"] == "assigned"
        assert "agent_name" in result
        assert "queue_position" in result

    def test_flag_priority_returns_dict(self):
        result = flag_priority.invoke(
            {"order_id": "ORD-001", "level": "high", "reason": "VIP customer"}
        )
        assert isinstance(result, dict)
        assert result["status"] == "flagged"
        assert result["priority_level"] == "high"
        assert "flagged_at" in result


# ---------------------------------------------------------------------------
# Tool collection tests
# ---------------------------------------------------------------------------


class TestToolCollections:
    def test_total_tool_count(self):
        assert len(ALL_TOOLS) == 12

    def test_shipment_tools_count(self):
        assert len(SHIPMENT_TOOLS) == 3

    def test_customer_tools_count(self):
        assert len(CUSTOMER_TOOLS) == 3

    def test_payment_tools_count(self):
        assert len(PAYMENT_TOOLS) == 3

    def test_escalation_tools_count(self):
        assert len(ESCALATION_TOOLS) == 3


# ---------------------------------------------------------------------------
# Specialist agent attribute tests
# ---------------------------------------------------------------------------


class TestSpecialistAttributes:
    def test_shipment_agent_type(self):
        agent = ShipmentAgent()
        assert agent.AGENT_TYPE == "shipment"

    def test_shipment_agent_tools(self):
        agent = ShipmentAgent()
        assert agent.TOOLS == SHIPMENT_TOOLS

    def test_shipment_agent_rag_filter(self):
        agent = ShipmentAgent()
        assert agent.RAG_FILTER == {"agent_type": "shipment"}

    def test_customer_agent_type(self):
        agent = CustomerAgent()
        assert agent.AGENT_TYPE == "customer"

    def test_customer_agent_tools(self):
        agent = CustomerAgent()
        assert agent.TOOLS == CUSTOMER_TOOLS

    def test_customer_agent_rag_filter(self):
        agent = CustomerAgent()
        assert agent.RAG_FILTER == {"agent_type": "customer"}

    def test_payment_agent_type(self):
        agent = PaymentAgent()
        assert agent.AGENT_TYPE == "payment"

    def test_payment_agent_tools(self):
        agent = PaymentAgent()
        assert agent.TOOLS == PAYMENT_TOOLS

    def test_payment_agent_rag_filter(self):
        agent = PaymentAgent()
        assert agent.RAG_FILTER == {"agent_type": "payment"}

    def test_escalation_agent_type(self):
        agent = EscalationAgent()
        assert agent.AGENT_TYPE == "escalation"

    def test_escalation_agent_tools(self):
        agent = EscalationAgent()
        assert agent.TOOLS == ESCALATION_TOOLS

    def test_escalation_agent_rag_filter(self):
        agent = EscalationAgent()
        assert agent.RAG_FILTER == {"agent_type": "escalation"}


# ---------------------------------------------------------------------------
# Specialist agent fallback tests (no LLM needed)
# ---------------------------------------------------------------------------


class TestSpecialistFallback:
    @pytest.mark.asyncio
    async def test_shipment_agent_fallback(self):
        agent = ShipmentAgent(llm=MagicMock())
        # Make LLM fail so fallback is used
        agent._get_llm = lambda: _make_failing_llm()
        result = await agent.run(SAMPLE_DEVIATION_CONTEXT)
        assert result["agent_type"] == "shipment"
        assert "action" in result
        assert "details" in result

    @pytest.mark.asyncio
    async def test_customer_agent_fallback(self):
        agent = CustomerAgent(llm=MagicMock())
        agent._get_llm = lambda: _make_failing_llm()
        result = await agent.run(SAMPLE_DEVIATION_CONTEXT)
        assert result["agent_type"] == "customer"

    @pytest.mark.asyncio
    async def test_payment_agent_fallback(self):
        agent = PaymentAgent(llm=MagicMock())
        agent._get_llm = lambda: _make_failing_llm()
        result = await agent.run(SAMPLE_DEVIATION_CONTEXT)
        assert result["agent_type"] == "payment"

    @pytest.mark.asyncio
    async def test_escalation_agent_fallback(self):
        agent = EscalationAgent(llm=MagicMock())
        agent._get_llm = lambda: _make_failing_llm()
        result = await agent.run(SAMPLE_DEVIATION_CONTEXT)
        assert result["agent_type"] == "escalation"


def _make_failing_llm():
    """Create an LLM mock that raises on invoke."""
    mock = MagicMock()
    mock.bind_tools.return_value = mock
    mock.ainvoke = AsyncMock(side_effect=Exception("LLM unavailable"))
    return mock


# ---------------------------------------------------------------------------
# Orchestrator routing tests
# ---------------------------------------------------------------------------


class TestOrchestratorRouting:
    def test_critical_routes_to_3_agents(self):
        assert len(_ROUTING_RULES["critical"]) == 3

    def test_warning_routes_to_2_agents(self):
        assert len(_ROUTING_RULES["warning"]) == 2

    def test_info_routes_to_0_agents(self):
        assert len(_ROUTING_RULES["info"]) == 0

    @pytest.mark.asyncio
    async def test_orchestrate_critical_returns_3_results(self):
        orch = AgentOrchestrator(llm=_make_failing_llm())
        ctx = {**SAMPLE_DEVIATION_CONTEXT, "severity": "critical"}
        results = await orch.orchestrate(ctx)
        assert len(results) == 3
        types = {r["agent_type"] for r in results}
        assert types == {"shipment", "customer", "escalation"}

    @pytest.mark.asyncio
    async def test_orchestrate_warning_returns_2_results(self):
        orch = AgentOrchestrator(llm=_make_failing_llm())
        ctx = {**SAMPLE_DEVIATION_CONTEXT, "severity": "warning"}
        results = await orch.orchestrate(ctx)
        assert len(results) == 2
        types = {r["agent_type"] for r in results}
        assert types == {"shipment", "customer"}

    @pytest.mark.asyncio
    async def test_orchestrate_info_returns_empty(self):
        orch = AgentOrchestrator(llm=_make_failing_llm())
        ctx = {**SAMPLE_DEVIATION_CONTEXT, "severity": "info"}
        results = await orch.orchestrate(ctx)
        assert results == []


# ---------------------------------------------------------------------------
# Orchestrator DB storage tests
# ---------------------------------------------------------------------------


class TestOrchestratorStorage:
    @pytest.mark.asyncio
    async def test_stores_agent_responses(self, session):
        # Create prerequisite records
        pred = Prediction(
            source="batch",
            order_id="ORD-AGT-001",
            delay_probability=0.85,
            severity="critical",
        )
        session.add(pred)
        session.flush()

        dev = Deviation(
            prediction_id=pred.id,
            severity="critical",
            reason="Test deviation",
        )
        session.add(dev)
        session.flush()

        orch = AgentOrchestrator(llm=_make_failing_llm(), session=session)
        ctx = {
            **SAMPLE_DEVIATION_CONTEXT,
            "severity": "critical",
            "deviation_id": dev.id,
        }
        results = await orch.orchestrate(ctx)
        assert len(results) == 3

        responses = session.query(AgentResponse).all()
        assert len(responses) == 3
        agent_types = {r.agent_type for r in responses}
        assert agent_types == {"shipment", "customer", "escalation"}

    @pytest.mark.asyncio
    async def test_responses_linked_to_deviation(self, session):
        pred = Prediction(
            source="batch",
            order_id="ORD-AGT-002",
            delay_probability=0.6,
            severity="warning",
        )
        session.add(pred)
        session.flush()

        dev = Deviation(
            prediction_id=pred.id,
            severity="warning",
            reason="Test warning",
        )
        session.add(dev)
        session.flush()

        orch = AgentOrchestrator(llm=_make_failing_llm(), session=session)
        ctx = {
            **SAMPLE_DEVIATION_CONTEXT,
            "severity": "warning",
            "deviation_id": dev.id,
        }
        await orch.orchestrate(ctx)

        responses = session.query(AgentResponse).all()
        for r in responses:
            assert r.deviation_id == dev.id

    @pytest.mark.asyncio
    async def test_no_deviation_id_skips_storage(self, session):
        orch = AgentOrchestrator(llm=_make_failing_llm(), session=session)
        ctx = {**SAMPLE_DEVIATION_CONTEXT, "severity": "warning", "deviation_id": None}
        results = await orch.orchestrate(ctx)
        assert len(results) == 2
        # No records stored because deviation_id is None
        assert session.query(AgentResponse).count() == 0

"""Tests for dags/agent_orchestration_dag.py — task functions tested directly."""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from dags.agent_orchestration_dag import (
    _REQUIRED_FIELDS,
    consume_deviation_event,
    deserialize_deviation,
    ingest_resolution,
    run_agent_orchestration,
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


VALID_DEVIATION_EVENT = json.dumps({
    "deviation_id": "d1234567-aaaa-bbbb-cccc-ddddeeee0001",
    "severity": "critical",
    "reason": "Delay probability 0.85 exceeds critical threshold 0.70",
    "order_id": "ORD-AGT-001",
    "prediction_id": "p1234567-aaaa-bbbb-cccc-ddddeeee0001",
})

VALID_DEVIATION_CONTEXT = json.loads(VALID_DEVIATION_EVENT)


# ---------------------------------------------------------------------------
# consume_deviation_event tests
# ---------------------------------------------------------------------------


class TestConsumeDeviationEvent:
    def test_returns_messages(self):
        mock_msg = MagicMock()
        mock_msg.value = VALID_DEVIATION_EVENT

        mock_consumer = MagicMock()
        mock_consumer.__iter__ = MagicMock(return_value=iter([mock_msg]))

        with patch("kafka.KafkaConsumer", return_value=mock_consumer):
            result = consume_deviation_event(bootstrap_servers="fake:9092")

        assert len(result) == 1
        assert result[0] == VALID_DEVIATION_EVENT

    def test_kafka_unavailable_returns_empty(self):
        with patch("kafka.KafkaConsumer", side_effect=Exception("Connection refused")):
            result = consume_deviation_event(bootstrap_servers="fake:9092")

        assert result == []

    def test_consumes_single_event(self):
        """Should consume one event by default (break after first)."""
        msgs = [MagicMock(value=f"msg-{i}") for i in range(5)]
        mock_consumer = MagicMock()
        mock_consumer.__iter__ = MagicMock(return_value=iter(msgs))

        with patch("kafka.KafkaConsumer", return_value=mock_consumer):
            result = consume_deviation_event(bootstrap_servers="fake:9092")

        assert len(result) == 1


# ---------------------------------------------------------------------------
# deserialize_deviation tests
# ---------------------------------------------------------------------------


class TestDeserializeDeviation:
    def test_parses_valid_event(self):
        result = deserialize_deviation([VALID_DEVIATION_EVENT])
        assert len(result) == 1
        assert result[0]["severity"] == "critical"
        assert result[0]["order_id"] == "ORD-AGT-001"

    def test_rejects_malformed_json(self):
        result = deserialize_deviation(["not json"])
        assert result == []

    def test_rejects_non_dict(self):
        result = deserialize_deviation(['[1,2,3]'])
        assert result == []

    def test_validates_required_fields(self):
        """Missing required fields should cause the event to be skipped."""
        incomplete = json.dumps({"severity": "critical"})
        result = deserialize_deviation([incomplete])
        assert result == []

    def test_required_fields_set(self):
        assert _REQUIRED_FIELDS == {"severity", "reason", "order_id", "deviation_id"}

    def test_empty_input(self):
        result = deserialize_deviation([])
        assert result == []


# ---------------------------------------------------------------------------
# run_agent_orchestration tests
# ---------------------------------------------------------------------------


class TestRunAgentOrchestration:
    @pytest.fixture(autouse=True)
    def _mock_llm(self, monkeypatch):
        """Prevent agents from constructing a real ChatOpenAI."""

        def _fake_get_llm(self_agent):
            mock = MagicMock()
            mock.bind_tools.return_value = mock
            mock.ainvoke = AsyncMock(side_effect=Exception("LLM unavailable"))
            return mock

        monkeypatch.setattr(
            "src.agents.specialists._BaseAgent._get_llm", _fake_get_llm
        )

    def test_returns_results_for_critical(self, session):
        results = run_agent_orchestration([VALID_DEVIATION_CONTEXT], session=session)
        assert len(results) == 3  # critical → shipment + customer + escalation
        types = {r["agent_type"] for r in results}
        assert types == {"shipment", "customer", "escalation"}

    def test_returns_results_for_warning(self, session):
        ctx = {**VALID_DEVIATION_CONTEXT, "severity": "warning"}
        results = run_agent_orchestration([ctx], session=session)
        assert len(results) == 2

    def test_info_returns_empty(self, session):
        ctx = {**VALID_DEVIATION_CONTEXT, "severity": "info"}
        results = run_agent_orchestration([ctx], session=session)
        assert results == []

    def test_stores_agent_responses_in_db(self, session):
        # Create prerequisite records so orchestrator can store responses
        pred = Prediction(
            source="streaming",
            order_id="ORD-AGT-001",
            delay_probability=0.85,
            severity="critical",
        )
        session.add(pred)
        session.flush()
        dev = Deviation(
            prediction_id=pred.id,
            severity="critical",
            reason="Test",
        )
        session.add(dev)
        session.flush()

        ctx = {**VALID_DEVIATION_CONTEXT, "deviation_id": dev.id}
        run_agent_orchestration([ctx], session=session)
        responses = session.query(AgentResponse).all()
        assert len(responses) == 3

    def test_empty_contexts(self, session):
        results = run_agent_orchestration([], session=session)
        assert results == []


# ---------------------------------------------------------------------------
# ingest_resolution tests
# ---------------------------------------------------------------------------


class TestIngestResolution:
    def test_empty_results_returns_zero(self):
        result = ingest_resolution([])
        assert result == 0

    def test_ingests_with_mock_embeddings(self, tmp_path):
        """Ingest resolutions using a fake embedding function."""

        class _FakeEmbeddings:
            def embed_documents(self, texts):
                return [[0.1] * 10 for _ in texts]

            def embed_query(self, text):
                return [0.1] * 10

        results = [
            {
                "agent_type": "shipment",
                "action": "rescheduled_to_flight",
                "details": {"tool_calls": []},
            }
        ]
        count = ingest_resolution(
            results,
            chroma_path=tmp_path / "chroma",
            embedding_function=_FakeEmbeddings(),
        )
        assert count == 1

    def test_failure_returns_zero(self):
        """If ingestion fails, return 0 instead of crashing."""
        with patch("langchain_chroma.Chroma", side_effect=Exception("Chroma down")):
            result = ingest_resolution(
                [{"agent_type": "test", "action": "test", "details": {}}],
            )
        assert result == 0

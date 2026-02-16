"""Integration tests against live Docker Compose services + real OpenAI.

Run with:  pytest -m integration -v
Requires:  docker compose up -d  (services must be healthy)
           OPENAI_API_KEY set in .env (for agent + RAG tests)

All configuration loaded from the .env file.
"""
from __future__ import annotations

import json
import os
import uuid
from pathlib import Path

import httpx
import psycopg2
import pytest
from dotenv import dotenv_values

# Read .env into a dict WITHOUT polluting os.environ (avoids side-effects
# on unit tests that share the same process during collection).
_ENV = dotenv_values(Path(__file__).resolve().parent.parent / ".env")

# Credentials from .env
PG_USER = _ENV.get("POSTGRES_USER", "fulfillment")
PG_PASS = _ENV.get("POSTGRES_PASSWORD", "fulfillment_pass")
PG_DB = _ENV.get("POSTGRES_DB", "fulfillment_ai")
KAFKA_TOPIC = _ENV.get("KAFKA_TOPIC", "fulfillment-events")

# Host-side endpoints (localhost on docker-compose mapped ports)
API_BASE = "http://localhost:8000"
PG_HOST = "localhost"
PG_PORT = 5432
KAFKA_BROKER = "localhost:9092"
REDPANDA_CONSOLE_URL = "http://localhost:8085"


def _api_reachable() -> bool:
    try:
        r = httpx.get(f"{API_BASE}/health", timeout=3)
        return r.status_code == 200
    except Exception:
        return False


def _pg_connect():
    """Return a psycopg2 connection using .env credentials + localhost."""
    return psycopg2.connect(
        host=PG_HOST,
        port=PG_PORT,
        dbname=PG_DB,
        user=PG_USER,
        password=PG_PASS,
    )


def _generate_order(**overrides) -> dict:
    """Generate a realistic order using ProducerSimulator, with optional overrides."""
    from src.kafka.producer_simulator import ProducerSimulator

    order = ProducerSimulator.generate_order()
    order.update(overrides)
    return order


pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        not _api_reachable(),
        reason="Docker services not running (API not reachable at localhost:8000)",
    ),
]


# ---------------------------------------------------------------------------
# Category 1: Service Health Checks
# ---------------------------------------------------------------------------


class TestServiceHealthChecks:
    def test_api_health(self):
        r = httpx.get(f"{API_BASE}/health", timeout=5)
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "healthy"
        assert data["version"] == "0.1.0"

    def test_postgres_connection(self):
        conn = _pg_connect()
        cur = conn.cursor()
        cur.execute("SELECT 1")
        assert cur.fetchone()[0] == 1
        cur.close()
        conn.close()

    def test_redpanda_broker_reachable(self):
        from kafka import KafkaConsumer

        consumer = KafkaConsumer(
            bootstrap_servers=KAFKA_BROKER,
            consumer_timeout_ms=5000,
            group_id=f"test-health-{uuid.uuid4().hex[:8]}",
        )
        topics = consumer.topics()
        consumer.close()
        assert isinstance(topics, set)

    def test_redpanda_console_reachable(self):
        r = httpx.get(REDPANDA_CONSOLE_URL, timeout=5, follow_redirects=True)
        assert r.status_code == 200


# ---------------------------------------------------------------------------
# Category 2: API Predict → Postgres Roundtrip
# ---------------------------------------------------------------------------


class TestPredictRoundtrip:
    def test_predict_stored_in_postgres(self):
        order = _generate_order()
        r = httpx.post(f"{API_BASE}/predict", json=order, timeout=15)
        data = r.json()
        order_id = data["order_id"]
        assert r.status_code == 200

        conn = _pg_connect()
        cur = conn.cursor()
        cur.execute(
            "SELECT order_id, delay_probability, severity FROM predictions WHERE order_id = %s",
            (order_id,),
        )
        row = cur.fetchone()
        cur.close()
        conn.close()

        assert row is not None
        assert row[0] == order_id
        assert abs(row[1] - data["delay_probability"]) < 1e-6
        assert row[2] == data["severity"]


# ---------------------------------------------------------------------------
# Category 3: Batch Predict
# ---------------------------------------------------------------------------


class TestBatchPredict:
    def _submit_batch(self, count: int = 5):
        orders = [_generate_order() for _ in range(count)]
        r = httpx.post(f"{API_BASE}/predict/batch", json=orders, timeout=60)
        return r, orders

    def test_batch_stored_in_postgres(self):
        r, orders = self._submit_batch(5)
        assert r.status_code == 200
        data = r.json()
        assert data["predictions_count"] == 5
        order_ids = [o["order_id"] for o in orders]

        conn = _pg_connect()
        cur = conn.cursor()
        cur.execute(
            "SELECT COUNT(*) FROM predictions WHERE order_id = ANY(%s)",
            (order_ids,),
        )
        count = cur.fetchone()[0]
        cur.close()
        conn.close()

        assert count == 5


# ---------------------------------------------------------------------------
# Category 4: Deviation Detection Roundtrip
# ---------------------------------------------------------------------------


class TestDeviationRoundtrip:
    def test_deviations_endpoint_returns_200(self):
        # Submit some orders first to ensure deviations exist
        orders = [_generate_order() for _ in range(10)]
        httpx.post(f"{API_BASE}/predict/batch", json=orders, timeout=60)

        r = httpx.get(f"{API_BASE}/deviations", timeout=10)
        assert r.status_code == 200

    def test_deviation_prediction_exists_in_postgres(self):
        r = httpx.get(f"{API_BASE}/deviations?limit=5", timeout=10)
        data = r.json()
        if not data["items"]:
            pytest.skip("No deviations found — cannot verify FK")

        prediction_id = data["items"][0]["prediction_id"]
        conn = _pg_connect()
        cur = conn.cursor()
        cur.execute(
            "SELECT id FROM predictions WHERE id = %s::uuid",
            (prediction_id,),
        )
        row = cur.fetchone()
        cur.close()
        conn.close()
        assert row is not None


# ---------------------------------------------------------------------------
# Category 5: Order Aggregation
# ---------------------------------------------------------------------------


class TestOrderAggregation:
    def test_order_detail_returns_predictions(self):
        order = _generate_order()
        httpx.post(f"{API_BASE}/predict", json=order, timeout=15)

        r = httpx.get(f"{API_BASE}/orders/{order['order_id']}", timeout=10)
        assert r.status_code == 200
        data = r.json()
        assert data["order_id"] == order["order_id"]
        assert len(data["predictions"]) >= 1

    def test_order_detail_includes_deviations(self):
        order = _generate_order()
        httpx.post(f"{API_BASE}/predict", json=order, timeout=15)

        r = httpx.get(f"{API_BASE}/orders/{order['order_id']}", timeout=10)
        data = r.json()
        # deviations list exists (may be empty if prediction was low-risk)
        assert "deviations" in data
        assert isinstance(data["deviations"], list)

    def test_nonexistent_order_returns_404(self):
        fake_id = f"ORD-NOTEXIST{uuid.uuid4().hex[:4].upper()}"
        r = httpx.get(f"{API_BASE}/orders/{fake_id}", timeout=10)
        assert r.status_code == 404


# ---------------------------------------------------------------------------
# Category 6: KPI Dashboard
# ---------------------------------------------------------------------------


class TestKPIDashboard:
    def test_kpi_returns_200(self):
        # Ensure at least one prediction exists
        order = _generate_order()
        httpx.post(f"{API_BASE}/predict", json=order, timeout=15)

        r = httpx.get(f"{API_BASE}/kpi/dashboard", timeout=10)
        assert r.status_code == 200

    def test_kpi_has_expected_fields(self):
        r = httpx.get(f"{API_BASE}/kpi/dashboard", timeout=10)
        data = r.json()
        assert data["total_predictions"] > 0
        assert isinstance(data["severity_breakdown"], dict)
        assert "avg_delay_probability" in data


# ---------------------------------------------------------------------------
# Category 7: Kafka Producer Simulator
# ---------------------------------------------------------------------------


class TestKafkaProducerSimulator:
    def test_fulfillment_events_topic_exists(self):
        from kafka import KafkaConsumer

        consumer = KafkaConsumer(
            bootstrap_servers=KAFKA_BROKER,
            consumer_timeout_ms=5000,
            group_id=f"test-topic-{uuid.uuid4().hex[:8]}",
        )
        topics = consumer.topics()
        consumer.close()
        assert KAFKA_TOPIC in topics


# ---------------------------------------------------------------------------
# Category 8: Database Schema Integrity
# ---------------------------------------------------------------------------


class TestDatabaseSchema:
    def test_expected_tables_exist(self):
        conn = _pg_connect()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT table_name FROM information_schema.tables
            WHERE table_schema = 'public'
            """
        )
        tables = {row[0] for row in cur.fetchall()}
        cur.close()
        conn.close()

        expected = {"predictions", "deviations", "agent_responses", "batch_jobs"}
        assert expected.issubset(tables), f"Missing tables: {expected - tables}"




# ---------------------------------------------------------------------------
# Category 9: Agent Orchestration with Real OpenAI
# ---------------------------------------------------------------------------


class TestAgentOrchestration:
    def test_critical_triggers_agents(self):
        payload = {
            "severity": "critical",
            "reason": "High delay probability detected",
            "order_id": f"ORD-INT{uuid.uuid4().hex[:6].upper()}",
            "delay_probability": 0.85,
        }
        r = httpx.post(f"{API_BASE}/agents/trigger", json=payload, timeout=60)
        assert r.status_code == 200
        data = r.json()
        assert "results" in data
        assert len(data["results"]) >= 2  # critical → shipment + customer + escalation

    def test_critical_includes_shipment_and_customer(self):
        payload = {
            "severity": "critical",
            "reason": "Very high delay probability",
            "order_id": f"ORD-INT{uuid.uuid4().hex[:6].upper()}",
            "delay_probability": 0.90,
        }
        r = httpx.post(f"{API_BASE}/agents/trigger", json=payload, timeout=60)
        data = r.json()
        agent_types = {res["agent_type"] for res in data["results"]}
        assert "shipment" in agent_types
        assert "customer" in agent_types

    def test_warning_triggers_fewer_agents(self):
        payload = {
            "severity": "warning",
            "reason": "Moderate delay probability",
            "order_id": f"ORD-INT{uuid.uuid4().hex[:6].upper()}",
            "delay_probability": 0.60,
        }
        r = httpx.post(f"{API_BASE}/agents/trigger", json=payload, timeout=60)
        data = r.json()
        assert len(data["results"]) >= 1
        # warning → shipment + customer (no escalation)
        agent_types = {res["agent_type"] for res in data["results"]}
        assert "escalation" not in agent_types

    def test_info_returns_empty_results(self):
        payload = {
            "severity": "info",
            "reason": "Low delay probability",
            "order_id": f"ORD-INT{uuid.uuid4().hex[:6].upper()}",
            "delay_probability": 0.35,
        }
        r = httpx.post(f"{API_BASE}/agents/trigger", json=payload, timeout=30)
        data = r.json()
        assert data["results"] == []


# ---------------------------------------------------------------------------
# Category 10: Knowledge Base Ingest + Search with Real OpenAI
# ---------------------------------------------------------------------------


class TestKnowledgeBase:
    @pytest.fixture(autouse=True, scope="class")
    def _ingest_once(self):
        """Ingest knowledge base documents once for the entire class.

        Skips all knowledge tests if ingestion fails (e.g. invalid OpenAI key).
        """
        r = httpx.post(f"{API_BASE}/knowledge/ingest", timeout=60)
        if r.status_code != 200:
            pytest.skip(
                f"Knowledge ingest failed (status {r.status_code}) — "
                "likely missing valid OPENAI_API_KEY for embeddings"
            )
        data = r.json()
        assert data["chunks_ingested"] > 0

    def test_ingest_returns_chunks(self):
        r = httpx.post(f"{API_BASE}/knowledge/ingest", timeout=60)
        assert r.status_code == 200
        data = r.json()
        assert data["chunks_ingested"] > 0

    def test_search_returns_results(self):
        payload = {"query": "shipping policy", "k": 3}
        r = httpx.post(f"{API_BASE}/knowledge/search", json=payload, timeout=30)
        assert r.status_code == 200
        data = r.json()
        assert len(data["results"]) > 0

    def test_search_result_structure(self):
        payload = {"query": "refund eligibility", "k": 3}
        r = httpx.post(f"{API_BASE}/knowledge/search", json=payload, timeout=30)
        data = r.json()
        assert len(data["results"]) > 0
        result = data["results"][0]
        assert "content" in result
        assert "metadata" in result
        assert "score" in result

    def test_search_with_metadata_filter(self):
        payload = {
            "query": "refund policy",
            "k": 5,
            "filter_metadata": {"agent_type": "payment"},
        }
        r = httpx.post(f"{API_BASE}/knowledge/search", json=payload, timeout=30)
        data = r.json()
        assert len(data["results"]) > 0
        for result in data["results"]:
            assert result["metadata"]["agent_type"] == "payment"

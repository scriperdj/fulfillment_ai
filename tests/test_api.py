"""Tests for src/api — FastAPI REST endpoints."""

from __future__ import annotations

import io
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from src.api.app import app
from src.api.deps import get_db
from src.db.models import AgentResponse, Base, BatchJob, Deviation, Prediction


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def engine():
    eng = create_engine(
        "sqlite://",
        echo=False,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=eng)
    yield eng
    eng.dispose()


@pytest.fixture()
def session(engine):
    SessionLocal = sessionmaker(bind=engine)
    sess = SessionLocal()
    yield sess
    sess.close()


@pytest.fixture()
def client(session):
    """TestClient with DB session overridden to use in-memory SQLite."""

    def _override_get_db():
        yield session

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def _clear_ml_caches():
    from src.ml.model_loader import load_model, load_preprocessor, load_metadata

    load_model.cache_clear()
    load_preprocessor.cache_clear()
    load_metadata.cache_clear()
    yield
    load_model.cache_clear()
    load_preprocessor.cache_clear()
    load_metadata.cache_clear()


SAMPLE_ORDER = {
    "order_id": "ORD-API-001",
    "warehouse_block": "B",
    "mode_of_shipment": "Flight",
    "customer_care_calls": 4,
    "customer_rating": 2,
    "cost_of_the_product": 250,
    "prior_purchases": 3,
    "product_importance": "High",
    "gender": "F",
    "discount_offered": 10,
    "weight_in_gms": 4200,
    "order_status": "shipped",
}

SAMPLE_ORDER_2 = {
    "order_id": "ORD-API-002",
    "warehouse_block": "A",
    "mode_of_shipment": "Road",
    "customer_care_calls": 1,
    "customer_rating": 5,
    "cost_of_the_product": 100,
    "prior_purchases": 8,
    "product_importance": "Low",
    "gender": "M",
    "discount_offered": 55,
    "weight_in_gms": 1000,
    "order_status": "processing",
}


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------


class TestHealthEndpoint:
    def test_health_returns_200(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200

    def test_health_returns_status_healthy(self, client):
        resp = client.get("/health")
        data = resp.json()
        assert data["status"] == "healthy"

    def test_health_returns_version(self, client):
        resp = client.get("/health")
        data = resp.json()
        assert data["version"] == "0.1.0"


# ---------------------------------------------------------------------------
# Predict
# ---------------------------------------------------------------------------


class TestPredictEndpoint:
    def test_predict_single_returns_200(self, client):
        resp = client.post("/predict", json=SAMPLE_ORDER)
        assert resp.status_code == 200

    def test_predict_single_returns_prediction(self, client):
        resp = client.post("/predict", json=SAMPLE_ORDER)
        data = resp.json()
        assert data["order_id"] == "ORD-API-001"
        assert "delay_probability" in data
        assert "severity" in data

    def test_predict_single_creates_db_record(self, client, session):
        client.post("/predict", json=SAMPLE_ORDER)
        assert session.query(Prediction).count() >= 1

    def test_predict_invalid_order_returns_422(self, client):
        resp = client.post("/predict", json={"order_id": "test"})
        assert resp.status_code == 422

    def test_predict_batch_returns_200(self, client):
        resp = client.post("/predict/batch", json=[SAMPLE_ORDER, SAMPLE_ORDER_2])
        assert resp.status_code == 200

    def test_predict_batch_returns_summary(self, client):
        resp = client.post("/predict/batch", json=[SAMPLE_ORDER, SAMPLE_ORDER_2])
        data = resp.json()
        assert data["predictions_count"] == 2
        assert "deviations_count" in data
        assert "severity_breakdown" in data


# ---------------------------------------------------------------------------
# Batch
# ---------------------------------------------------------------------------


class TestBatchEndpoint:
    def _make_csv_file(self):
        csv_content = (
            "order_id,warehouse_block,mode_of_shipment,customer_care_calls,"
            "customer_rating,cost_of_the_product,prior_purchases,product_importance,"
            "gender,discount_offered,weight_in_gms\n"
            "ORD-CSV-001,B,Flight,4,2,250,3,High,F,10,4200\n"
        )
        return io.BytesIO(csv_content.encode("utf-8"))

    def test_batch_upload_returns_201(self, client, tmp_path):
        resp = client.post(
            "/batch/upload",
            files={"file": ("test.csv", self._make_csv_file(), "text/csv")},
        )
        assert resp.status_code == 201

    def test_batch_upload_returns_batch_id(self, client):
        resp = client.post(
            "/batch/upload",
            files={"file": ("test.csv", self._make_csv_file(), "text/csv")},
        )
        data = resp.json()
        assert "batch_job_id" in data
        assert data["status"] == "processing"
        assert data["row_count"] == 1

    def test_batch_status_returns_200(self, client, session):
        # Create a batch job directly
        job = BatchJob(filename="test.csv", status="completed", row_count=5)
        session.add(job)
        session.flush()
        resp = client.get(f"/batch/{job.id}/status")
        assert resp.status_code == 200
        assert resp.json()["status"] == "completed"

    def test_batch_status_not_found(self, client):
        fake_id = str(uuid.uuid4())
        resp = client.get(f"/batch/{fake_id}/status")
        assert resp.status_code == 404

    def test_batch_predictions_returns_list(self, client, session):
        job = BatchJob(filename="test.csv", status="completed", row_count=1)
        session.add(job)
        session.flush()
        pred = Prediction(
            batch_job_id=job.id,
            source="batch",
            order_id="ORD-001",
            delay_probability=0.5,
            severity="warning",
        )
        session.add(pred)
        session.flush()
        resp = client.get(f"/batch/{job.id}/predictions")
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    def test_batch_deviations_returns_list(self, client, session):
        job = BatchJob(filename="test.csv", status="completed", row_count=1)
        session.add(job)
        session.flush()
        pred = Prediction(
            batch_job_id=job.id,
            source="batch",
            order_id="ORD-001",
            delay_probability=0.8,
            severity="critical",
        )
        session.add(pred)
        session.flush()
        dev = Deviation(
            prediction_id=pred.id,
            batch_job_id=job.id,
            severity="critical",
            reason="Test",
        )
        session.add(dev)
        session.flush()
        resp = client.get(f"/batch/{job.id}/deviations")
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    def test_batch_agent_responses_empty(self, client, session):
        job = BatchJob(filename="test.csv", status="completed", row_count=1)
        session.add(job)
        session.flush()
        resp = client.get(f"/batch/{job.id}/agent-responses")
        assert resp.status_code == 200
        assert resp.json() == []


# ---------------------------------------------------------------------------
# Deviations
# ---------------------------------------------------------------------------


class TestDeviationsEndpoint:
    def _seed_deviations(self, session):
        pred = Prediction(
            source="batch",
            order_id="ORD-DEV-001",
            delay_probability=0.85,
            severity="critical",
        )
        session.add(pred)
        session.flush()
        for sev in ["critical", "warning", "critical"]:
            dev = Deviation(prediction_id=pred.id, severity=sev, reason=f"Test {sev}")
            session.add(dev)
        session.flush()

    def test_deviations_returns_paginated(self, client, session):
        self._seed_deviations(session)
        resp = client.get("/deviations")
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "total" in data
        assert data["total"] == 3

    def test_deviations_filter_severity(self, client, session):
        self._seed_deviations(session)
        resp = client.get("/deviations?severity=critical")
        data = resp.json()
        assert data["total"] == 2
        for item in data["items"]:
            assert item["severity"] == "critical"

    def test_deviations_pagination_skip_limit(self, client, session):
        self._seed_deviations(session)
        resp = client.get("/deviations?skip=0&limit=1")
        data = resp.json()
        assert len(data["items"]) == 1
        assert data["total"] == 3


# ---------------------------------------------------------------------------
# Agents
# ---------------------------------------------------------------------------


class TestAgentEndpoint:
    @pytest.fixture(autouse=True)
    def _mock_llm(self, monkeypatch):
        """Prevent agents from constructing a real ChatOpenAI (needs API key)."""
        from unittest.mock import MagicMock, AsyncMock

        def _fake_get_llm(self_agent):
            mock = MagicMock()
            mock.bind_tools.return_value = mock
            mock.ainvoke = AsyncMock(side_effect=Exception("LLM unavailable"))
            return mock

        monkeypatch.setattr(
            "src.agents.specialists._BaseAgent._get_llm", _fake_get_llm
        )

    def test_trigger_returns_200(self, client):
        resp = client.post(
            "/agents/trigger",
            json={
                "severity": "warning",
                "reason": "Delay detected",
                "order_id": "ORD-001",
                "delay_probability": 0.65,
            },
        )
        assert resp.status_code == 200

    def test_trigger_returns_results(self, client):
        resp = client.post(
            "/agents/trigger",
            json={
                "severity": "warning",
                "reason": "Delay detected",
                "order_id": "ORD-001",
                "delay_probability": 0.65,
            },
        )
        data = resp.json()
        assert "results" in data
        assert len(data["results"]) == 2  # warning → shipment + customer

    def test_trigger_info_returns_empty(self, client):
        resp = client.post(
            "/agents/trigger",
            json={
                "severity": "info",
                "reason": "Minor",
                "order_id": "ORD-001",
                "delay_probability": 0.35,
            },
        )
        data = resp.json()
        assert data["results"] == []


# ---------------------------------------------------------------------------
# Orders
# ---------------------------------------------------------------------------


class TestOrderEndpoint:
    def test_order_returns_200(self, client, session):
        pred = Prediction(
            source="batch",
            order_id="ORD-ORD-001",
            delay_probability=0.5,
            severity="warning",
        )
        session.add(pred)
        session.flush()
        resp = client.get("/orders/ORD-ORD-001")
        assert resp.status_code == 200
        data = resp.json()
        assert data["order_id"] == "ORD-ORD-001"
        assert len(data["predictions"]) == 1

    def test_order_not_found(self, client):
        resp = client.get("/orders/NONEXISTENT")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# KPI
# ---------------------------------------------------------------------------


class TestKPIEndpoint:
    def test_kpi_dashboard_returns_200(self, client):
        resp = client.get("/kpi/dashboard")
        assert resp.status_code == 200

    def test_kpi_dashboard_empty_db(self, client):
        resp = client.get("/kpi/dashboard")
        data = resp.json()
        assert data["total_predictions"] == 0
        assert data["avg_delay_probability"] == 0.0

    def test_kpi_dashboard_with_data(self, client, session):
        pred = Prediction(
            source="batch",
            order_id="ORD-KPI-001",
            delay_probability=0.75,
            severity="critical",
        )
        session.add(pred)
        session.flush()
        resp = client.get("/kpi/dashboard")
        data = resp.json()
        assert data["total_predictions"] == 1
        assert data["high_risk_count"] == 1


# ---------------------------------------------------------------------------
# Knowledge (mocked — no OpenAI key needed)
# ---------------------------------------------------------------------------


class TestKnowledgeEndpoint:
    def test_search_returns_200(self, client, monkeypatch):
        monkeypatch.setattr(
            "src.rag.retrieval.retrieve",
            lambda query, k=5, filter_metadata=None, **kwargs: [
                {"content": "test doc", "metadata": {}, "score": 0.9}
            ],
        )
        resp = client.post(
            "/knowledge/search",
            json={"query": "shipping policy", "k": 3},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["results"]) == 1


# ---------------------------------------------------------------------------
# Global error handler
# ---------------------------------------------------------------------------


class TestErrorHandler:
    def test_unhandled_exception_returns_500(self, client, monkeypatch):
        """Trigger an unhandled exception and verify 500 response."""

        def _raise(*args, **kwargs):
            raise RuntimeError("Boom")

        monkeypatch.setattr("src.api.routes.kpi.compute_running_kpis", _raise)
        resp = client.get("/kpi/dashboard")
        assert resp.status_code == 500
        assert resp.json()["detail"] == "Internal server error"

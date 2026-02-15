"""Unit tests for src/db — models, session, init_db."""

import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import Session, sessionmaker

from src.db.models import (
    AgentResponse,
    Base,
    BatchJob,
    Deviation,
    Prediction,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def engine():
    """In-memory SQLite engine with all tables created."""
    eng = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(bind=eng)
    yield eng
    eng.dispose()


@pytest.fixture()
def session(engine):
    """Scoped session that rolls back after each test."""
    connection = engine.connect()
    transaction = connection.begin()
    sess = Session(bind=connection)
    yield sess
    sess.close()
    transaction.rollback()
    connection.close()


# ---------------------------------------------------------------------------
# Table creation / init_db
# ---------------------------------------------------------------------------


class TestInitDb:
    def test_tables_created(self, engine):
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        assert "batch_jobs" in tables
        assert "predictions" in tables
        assert "deviations" in tables
        assert "agent_responses" in tables

    def test_idempotent_create(self, engine):
        """Calling create_all twice should not error."""
        Base.metadata.create_all(bind=engine)
        Base.metadata.create_all(bind=engine)
        inspector = inspect(engine)
        assert "batch_jobs" in inspector.get_table_names()


# ---------------------------------------------------------------------------
# BatchJob model
# ---------------------------------------------------------------------------


class TestBatchJob:
    def test_create_with_defaults(self, session):
        job = BatchJob(filename="test.csv")
        session.add(job)
        session.flush()

        assert job.id is not None
        assert isinstance(job.id, uuid.UUID)
        assert job.status == "pending"
        assert job.row_count == 0
        assert job.created_at is not None
        assert job.completed_at is None
        assert job.error_message is None

    def test_create_with_explicit_values(self, session):
        job = BatchJob(
            filename="upload.csv",
            status="processing",
            row_count=500,
        )
        session.add(job)
        session.flush()

        assert job.status == "processing"
        assert job.row_count == 500

    def test_update_status(self, session):
        job = BatchJob(filename="test.csv")
        session.add(job)
        session.flush()

        job.status = "completed"
        job.completed_at = datetime.now(timezone.utc)
        session.flush()

        assert job.status == "completed"
        assert job.completed_at is not None

    def test_error_message(self, session):
        job = BatchJob(filename="bad.csv", status="failed", error_message="Parse error on row 5")
        session.add(job)
        session.flush()
        assert job.error_message == "Parse error on row 5"

    def test_repr(self, session):
        job = BatchJob(filename="test.csv", row_count=10)
        session.add(job)
        session.flush()
        r = repr(job)
        assert "BatchJob" in r
        assert "pending" in r


# ---------------------------------------------------------------------------
# Prediction model
# ---------------------------------------------------------------------------


class TestPrediction:
    def test_create_with_batch_job(self, session):
        job = BatchJob(filename="test.csv", row_count=1)
        session.add(job)
        session.flush()

        pred = Prediction(
            batch_job_id=job.id,
            source="batch",
            order_id="ORD-001",
            delay_probability=0.75,
            severity="critical",
            features_json={"weight": 1200, "discount": 10},
        )
        session.add(pred)
        session.flush()

        assert pred.id is not None
        assert pred.batch_job_id == job.id
        assert pred.delay_probability == 0.75
        assert pred.features_json["weight"] == 1200

    def test_create_streaming_without_batch_job(self, session):
        pred = Prediction(
            source="streaming",
            order_id="ORD-002",
            delay_probability=0.45,
            severity="info",
        )
        session.add(pred)
        session.flush()

        assert pred.batch_job_id is None
        assert pred.source == "streaming"

    def test_batch_job_relationship(self, session):
        job = BatchJob(filename="test.csv", row_count=1)
        pred = Prediction(
            source="batch",
            order_id="ORD-003",
            delay_probability=0.6,
            severity="warning",
        )
        job.predictions.append(pred)
        session.add(job)
        session.flush()

        assert pred.batch_job is job
        assert pred in job.predictions

    def test_repr(self, session):
        pred = Prediction(
            source="batch",
            order_id="ORD-004",
            delay_probability=0.55,
            severity="warning",
        )
        session.add(pred)
        session.flush()
        r = repr(pred)
        assert "Prediction" in r
        assert "ORD-004" in r


# ---------------------------------------------------------------------------
# Deviation model
# ---------------------------------------------------------------------------


class TestDeviation:
    def _make_prediction(self, session):
        pred = Prediction(
            source="batch",
            order_id="ORD-010",
            delay_probability=0.8,
            severity="critical",
        )
        session.add(pred)
        session.flush()
        return pred

    def test_create_deviation(self, session):
        pred = self._make_prediction(session)
        dev = Deviation(
            prediction_id=pred.id,
            severity="critical",
            reason="Delay probability 0.80 exceeds critical threshold",
        )
        session.add(dev)
        session.flush()

        assert dev.id is not None
        assert dev.status == "new"
        assert dev.prediction_id == pred.id

    def test_deviation_with_batch_job(self, session):
        job = BatchJob(filename="test.csv", row_count=1)
        session.add(job)
        session.flush()

        pred = Prediction(
            batch_job_id=job.id,
            source="batch",
            order_id="ORD-011",
            delay_probability=0.9,
            severity="critical",
        )
        session.add(pred)
        session.flush()

        dev = Deviation(
            prediction_id=pred.id,
            batch_job_id=job.id,
            severity="critical",
            reason="Very high delay probability",
        )
        session.add(dev)
        session.flush()

        assert dev.batch_job_id == job.id
        assert dev.prediction is pred
        assert dev in pred.deviations

    def test_prediction_relationship(self, session):
        pred = self._make_prediction(session)
        dev = Deviation(
            prediction_id=pred.id,
            severity="warning",
            reason="test",
        )
        session.add(dev)
        session.flush()

        assert dev.prediction is pred
        assert dev in pred.deviations


# ---------------------------------------------------------------------------
# AgentResponse model
# ---------------------------------------------------------------------------


class TestAgentResponse:
    def _make_chain(self, session):
        pred = Prediction(
            source="streaming",
            order_id="ORD-020",
            delay_probability=0.85,
            severity="critical",
        )
        session.add(pred)
        session.flush()

        dev = Deviation(
            prediction_id=pred.id,
            severity="critical",
            reason="High delay",
        )
        session.add(dev)
        session.flush()
        return pred, dev

    def test_create_agent_response(self, session):
        _, dev = self._make_chain(session)
        resp = AgentResponse(
            deviation_id=dev.id,
            agent_type="shipment",
            action="reschedule_shipment",
            details_json={"new_tracking_id": "TRK-999", "carrier": "FedEx"},
            conversation_history=[
                {"role": "system", "content": "You are a shipping agent."},
                {"role": "assistant", "content": "Rescheduling shipment..."},
            ],
        )
        session.add(resp)
        session.flush()

        assert resp.id is not None
        assert resp.agent_type == "shipment"
        assert resp.details_json["new_tracking_id"] == "TRK-999"
        assert len(resp.conversation_history) == 2

    def test_deviation_relationship(self, session):
        _, dev = self._make_chain(session)
        resp = AgentResponse(
            deviation_id=dev.id,
            agent_type="customer",
            action="send_notification",
        )
        session.add(resp)
        session.flush()

        assert resp.deviation is dev
        assert resp in dev.agent_responses

    def test_multiple_responses_per_deviation(self, session):
        _, dev = self._make_chain(session)
        r1 = AgentResponse(
            deviation_id=dev.id, agent_type="shipment", action="reschedule"
        )
        r2 = AgentResponse(
            deviation_id=dev.id, agent_type="customer", action="notify"
        )
        session.add_all([r1, r2])
        session.flush()

        assert len(dev.agent_responses) == 2


# ---------------------------------------------------------------------------
# Cascade behavior
# ---------------------------------------------------------------------------


class TestCascade:
    def test_delete_batch_job_cascades_predictions(self, session):
        job = BatchJob(filename="cascade.csv", row_count=1)
        pred = Prediction(
            source="batch",
            order_id="ORD-C1",
            delay_probability=0.5,
            severity="info",
        )
        job.predictions.append(pred)
        session.add(job)
        session.flush()

        pred_id = pred.id
        session.delete(job)
        session.flush()

        assert session.get(Prediction, pred_id) is None

    def test_delete_prediction_cascades_deviations(self, session):
        pred = Prediction(
            source="streaming",
            order_id="ORD-C2",
            delay_probability=0.8,
            severity="critical",
        )
        session.add(pred)
        session.flush()

        dev = Deviation(
            prediction_id=pred.id, severity="critical", reason="test"
        )
        session.add(dev)
        session.flush()

        dev_id = dev.id
        session.delete(pred)
        session.flush()

        assert session.get(Deviation, dev_id) is None

    def test_delete_deviation_cascades_agent_responses(self, session):
        pred = Prediction(
            source="batch",
            order_id="ORD-C3",
            delay_probability=0.9,
            severity="critical",
        )
        session.add(pred)
        session.flush()

        dev = Deviation(
            prediction_id=pred.id, severity="critical", reason="test"
        )
        session.add(dev)
        session.flush()

        resp = AgentResponse(
            deviation_id=dev.id, agent_type="escalation", action="create_ticket"
        )
        session.add(resp)
        session.flush()

        resp_id = resp.id
        session.delete(dev)
        session.flush()

        assert session.get(AgentResponse, resp_id) is None


# ---------------------------------------------------------------------------
# Indexes
# ---------------------------------------------------------------------------


class TestIndexes:
    def test_expected_indexes_exist(self, engine):
        inspector = inspect(engine)

        def get_index_names(table_name):
            return {idx["name"] for idx in inspector.get_indexes(table_name)}

        batch_idx = get_index_names("batch_jobs")
        assert "ix_batch_jobs_status" in batch_idx
        assert "ix_batch_jobs_created_at" in batch_idx

        pred_idx = get_index_names("predictions")
        assert "ix_predictions_order_id" in pred_idx
        assert "ix_predictions_severity" in pred_idx
        assert "ix_predictions_created_at" in pred_idx

        dev_idx = get_index_names("deviations")
        assert "ix_deviations_severity" in dev_idx
        assert "ix_deviations_status" in dev_idx
        assert "ix_deviations_created_at" in dev_idx

        resp_idx = get_index_names("agent_responses")
        assert "ix_agent_responses_agent_type" in resp_idx
        assert "ix_agent_responses_created_at" in resp_idx


# ---------------------------------------------------------------------------
# FK columns
# ---------------------------------------------------------------------------


class TestForeignKeys:
    def test_predictions_fk_to_batch_jobs(self, engine):
        inspector = inspect(engine)
        fks = inspector.get_foreign_keys("predictions")
        referred_tables = {fk["referred_table"] for fk in fks}
        assert "batch_jobs" in referred_tables

    def test_deviations_fk_to_predictions(self, engine):
        inspector = inspect(engine)
        fks = inspector.get_foreign_keys("deviations")
        referred_tables = {fk["referred_table"] for fk in fks}
        assert "predictions" in referred_tables
        assert "batch_jobs" in referred_tables

    def test_agent_responses_fk_to_deviations(self, engine):
        inspector = inspect(engine)
        fks = inspector.get_foreign_keys("agent_responses")
        referred_tables = {fk["referred_table"] for fk in fks}
        assert "deviations" in referred_tables


# ---------------------------------------------------------------------------
# Session factories (sync only — async tested separately)
# ---------------------------------------------------------------------------


class TestSyncSession:
    def test_session_factory_creates_session(self):
        """Verify we can create a sync session with SQLite."""
        eng = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=eng)
        factory = sessionmaker(bind=eng)
        sess = factory()
        try:
            job = BatchJob(filename="session_test.csv")
            sess.add(job)
            sess.commit()
            assert sess.get(BatchJob, job.id) is not None
        finally:
            sess.close()
            eng.dispose()

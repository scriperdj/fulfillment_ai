"""Tests for src/detection — deviation detection and Kafka publishing."""

from __future__ import annotations

import json
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from src.db.models import Base, Deviation, Prediction
from src.detection.deviation_detector import detect_batch, detect_deviation
from src.detection.publisher import DeviationPublisher
from src.kafka.client import KafkaClient


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


def _make_prediction(session: Session, *, order_id: str = "ORD-001", delay_probability: float = 0.5) -> Prediction:
    pred = Prediction(
        source="batch",
        order_id=order_id,
        delay_probability=delay_probability,
        severity="warning",
    )
    session.add(pred)
    session.flush()
    return pred


# ---------------------------------------------------------------------------
# detect_deviation tests
# ---------------------------------------------------------------------------


class TestDetectDeviation:
    def test_critical_severity(self, session):
        pred = _make_prediction(session, delay_probability=0.8)
        dev = detect_deviation(pred.id, 0.8, {}, session=session)
        assert dev is not None
        assert dev.severity == "critical"
        assert "0.80" in dev.reason
        assert "critical" in dev.reason

    def test_warning_severity(self, session):
        pred = _make_prediction(session, delay_probability=0.6)
        dev = detect_deviation(pred.id, 0.6, {}, session=session)
        assert dev is not None
        assert dev.severity == "warning"

    def test_info_severity(self, session):
        pred = _make_prediction(session, delay_probability=0.4)
        dev = detect_deviation(pred.id, 0.4, {}, session=session)
        assert dev is not None
        assert dev.severity == "info"

    def test_below_threshold_returns_none(self, session):
        pred = _make_prediction(session, delay_probability=0.1)
        dev = detect_deviation(pred.id, 0.1, {}, session=session)
        assert dev is None

    def test_exact_critical_threshold(self, session):
        pred = _make_prediction(session, delay_probability=0.7)
        dev = detect_deviation(pred.id, 0.7, {}, session=session)
        assert dev is not None
        assert dev.severity == "critical"

    def test_exact_warning_threshold(self, session):
        pred = _make_prediction(session, delay_probability=0.5)
        dev = detect_deviation(pred.id, 0.5, {}, session=session)
        assert dev is not None
        assert dev.severity == "warning"

    def test_exact_info_threshold(self, session):
        pred = _make_prediction(session, delay_probability=0.3)
        dev = detect_deviation(pred.id, 0.3, {}, session=session)
        assert dev is not None
        assert dev.severity == "info"

    def test_just_below_info_threshold(self, session):
        pred = _make_prediction(session, delay_probability=0.29)
        dev = detect_deviation(pred.id, 0.29, {}, session=session)
        assert dev is None

    def test_deviation_persisted_to_db(self, session):
        pred = _make_prediction(session, delay_probability=0.8)
        dev = detect_deviation(pred.id, 0.8, {}, session=session)
        assert dev.id is not None
        fetched = session.get(Deviation, dev.id)
        assert fetched is not None
        assert fetched.prediction_id == pred.id

    def test_batch_job_id_stored(self, session):
        pred = _make_prediction(session, delay_probability=0.8)
        batch_id = uuid.uuid4()
        dev = detect_deviation(pred.id, 0.8, {"batch_job_id": batch_id}, session=session)
        assert dev.batch_job_id == batch_id

    def test_no_batch_job_id(self, session):
        pred = _make_prediction(session, delay_probability=0.8)
        dev = detect_deviation(pred.id, 0.8, {}, session=session)
        assert dev.batch_job_id is None


# ---------------------------------------------------------------------------
# detect_batch tests
# ---------------------------------------------------------------------------


class TestDetectBatch:
    def test_empty_list(self, session):
        result = detect_batch([], session=session)
        assert result == []

    def test_mixed_severities(self, session):
        preds = []
        for i, prob in enumerate([0.8, 0.6, 0.1]):
            p = _make_prediction(session, order_id=f"ORD-{i}", delay_probability=prob)
            preds.append({"prediction_id": p.id, "delay_probability": prob})

        result = detect_batch(preds, session=session)
        assert len(result) == 2  # 0.8 and 0.6 trigger; 0.1 does not
        severities = {d.severity for d in result}
        assert "critical" in severities
        assert "warning" in severities

    def test_all_below_threshold(self, session):
        preds = []
        for i in range(3):
            p = _make_prediction(session, order_id=f"ORD-{i}", delay_probability=0.1)
            preds.append({"prediction_id": p.id, "delay_probability": 0.1})

        result = detect_batch(preds, session=session)
        assert result == []

    def test_order_context_forwarded(self, session):
        batch_id = uuid.uuid4()
        p = _make_prediction(session, delay_probability=0.8)
        preds = [
            {
                "prediction_id": p.id,
                "delay_probability": 0.8,
                "order_context": {"batch_job_id": batch_id},
            }
        ]
        result = detect_batch(preds, session=session)
        assert len(result) == 1
        assert result[0].batch_job_id == batch_id


# ---------------------------------------------------------------------------
# DeviationPublisher.serialize_deviation tests
# ---------------------------------------------------------------------------


class TestSerializeDeviation:
    def test_json_structure(self, session):
        pred = _make_prediction(session, delay_probability=0.8)
        dev = detect_deviation(pred.id, 0.8, {}, session=session)
        data = json.loads(
            DeviationPublisher.serialize_deviation(dev, {"order_id": "ORD-001"})
        )
        assert data["deviation_id"] == str(dev.id)
        assert data["severity"] == "critical"
        assert data["order_id"] == "ORD-001"
        assert data["prediction_id"] == str(pred.id)
        assert "reason" in data
        assert "timestamp" in data

    def test_missing_order_id_defaults_empty(self, session):
        pred = _make_prediction(session, delay_probability=0.8)
        dev = detect_deviation(pred.id, 0.8, {}, session=session)
        data = json.loads(DeviationPublisher.serialize_deviation(dev, {}))
        assert data["order_id"] == ""


# ---------------------------------------------------------------------------
# DeviationPublisher.publish severity filtering tests
# ---------------------------------------------------------------------------


class TestPublisherSeverityFilter:
    @pytest.mark.asyncio
    async def test_publish_critical(self, session):
        pred = _make_prediction(session, delay_probability=0.8)
        dev = detect_deviation(pred.id, 0.8, {}, session=session)

        publisher = DeviationPublisher()
        publisher._client = MagicMock(spec=KafkaClient)
        publisher._client.publish_message = AsyncMock()

        await publisher.publish(dev, {"order_id": "ORD-001"})
        publisher._client.publish_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_publish_warning(self, session):
        pred = _make_prediction(session, delay_probability=0.6)
        dev = detect_deviation(pred.id, 0.6, {}, session=session)

        publisher = DeviationPublisher()
        publisher._client = MagicMock(spec=KafkaClient)
        publisher._client.publish_message = AsyncMock()

        await publisher.publish(dev, {"order_id": "ORD-002"})
        publisher._client.publish_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_skip_info_severity(self, session):
        pred = _make_prediction(session, delay_probability=0.4)
        dev = detect_deviation(pred.id, 0.4, {}, session=session)

        publisher = DeviationPublisher()
        publisher._client = MagicMock(spec=KafkaClient)
        publisher._client.publish_message = AsyncMock()

        await publisher.publish(dev, {"order_id": "ORD-003"})
        publisher._client.publish_message.assert_not_called()


# ---------------------------------------------------------------------------
# KafkaClient graceful handling tests
# ---------------------------------------------------------------------------


class TestKafkaClientGraceful:
    @pytest.mark.asyncio
    async def test_publish_when_kafka_unavailable(self):
        """KafkaClient should not crash when Kafka is unreachable."""
        client = KafkaClient(bootstrap_servers="localhost:19092")
        # get_producer will fail to connect, setting _producer to None
        producer = await client.get_producer()
        assert producer is None
        # publish_message should be a no-op
        await client.publish_message("test-topic", key="k1", value=b"v1")

    @pytest.mark.asyncio
    async def test_close_without_connection(self):
        """Closing a KafkaClient that never connected should not raise."""
        client = KafkaClient(bootstrap_servers="localhost:19092")
        await client.close()  # no error

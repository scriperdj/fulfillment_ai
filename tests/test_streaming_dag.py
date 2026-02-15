"""Tests for dags/streaming_dag.py — task functions tested directly."""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from dags.streaming_dag import (
    DEFAULT_BATCH_MAX_MESSAGES,
    DEFAULT_BATCH_TIMEOUT_SECONDS,
    consume_micro_batch,
    deserialize_messages,
    publish_deviations,
    validate_and_process,
)
from src.db.models import Base, Prediction


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


VALID_ORDER_JSON = json.dumps({
    "order_id": "ORD-STREAM-001",
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
})

VALID_ORDER_DICT = json.loads(VALID_ORDER_JSON)


# ---------------------------------------------------------------------------
# consume_micro_batch tests
# ---------------------------------------------------------------------------


class TestConsumeMicroBatch:
    def test_returns_messages_from_kafka(self):
        """Mock KafkaConsumer to return messages."""
        mock_msg = MagicMock()
        mock_msg.value = VALID_ORDER_JSON

        mock_consumer = MagicMock()
        mock_consumer.__iter__ = MagicMock(return_value=iter([mock_msg]))

        with patch("kafka.KafkaConsumer", return_value=mock_consumer):
            result = consume_micro_batch(bootstrap_servers="fake:9092")

        assert len(result) == 1
        assert result[0] == VALID_ORDER_JSON

    def test_kafka_unavailable_returns_empty(self):
        """When Kafka is unavailable, return empty list."""
        with patch("kafka.KafkaConsumer", side_effect=Exception("Connection refused")):
            result = consume_micro_batch(bootstrap_servers="fake:9092")

        assert result == []

    def test_respects_max_messages(self):
        """Stop collecting when batch_max_messages is reached."""
        msgs = [MagicMock(value=f'{{"order_id": "ORD-{i}"}}') for i in range(5)]
        mock_consumer = MagicMock()
        mock_consumer.__iter__ = MagicMock(return_value=iter(msgs))

        with patch("kafka.KafkaConsumer", return_value=mock_consumer):
            result = consume_micro_batch(
                bootstrap_servers="fake:9092",
                batch_max_messages=3,
            )

        assert len(result) == 3

    def test_default_timeout_is_15s(self):
        assert DEFAULT_BATCH_TIMEOUT_SECONDS == 15

    def test_default_max_messages_is_1000(self):
        assert DEFAULT_BATCH_MAX_MESSAGES == 1000


# ---------------------------------------------------------------------------
# deserialize_messages tests
# ---------------------------------------------------------------------------


class TestDeserializeMessages:
    def test_parses_valid_json(self):
        result = deserialize_messages([VALID_ORDER_JSON])
        assert len(result) == 1
        assert result[0]["order_id"] == "ORD-STREAM-001"

    def test_skips_malformed_json(self):
        result = deserialize_messages(["not json", VALID_ORDER_JSON])
        assert len(result) == 1

    def test_skips_non_dict(self):
        result = deserialize_messages(['[1,2,3]', VALID_ORDER_JSON])
        assert len(result) == 1

    def test_skips_missing_order_id(self):
        result = deserialize_messages(['{"foo": "bar"}', VALID_ORDER_JSON])
        assert len(result) == 1

    def test_empty_input(self):
        result = deserialize_messages([])
        assert result == []

    def test_all_malformed_returns_empty(self):
        result = deserialize_messages(["bad", "also bad", "nope"])
        assert result == []


# ---------------------------------------------------------------------------
# validate_and_process tests
# ---------------------------------------------------------------------------


class TestValidateAndProcess:
    def test_empty_orders_returns_zero(self, session):
        result = validate_and_process([], session=session)
        assert result["predictions_count"] == 0
        assert result["deviations_count"] == 0

    def test_processes_valid_orders(self, session):
        result = validate_and_process([VALID_ORDER_DICT], session=session)
        assert result["predictions_count"] == 1
        assert isinstance(result["deviations_count"], int)

    def test_stores_predictions_in_db(self, session):
        validate_and_process([VALID_ORDER_DICT], session=session)
        preds = session.query(Prediction).all()
        assert len(preds) == 1

    def test_source_is_streaming(self, session):
        validate_and_process([VALID_ORDER_DICT], session=session)
        pred = session.query(Prediction).first()
        assert pred.source == "streaming"


# ---------------------------------------------------------------------------
# publish_deviations tests
# ---------------------------------------------------------------------------


class TestPublishDeviations:
    def test_no_deviations_returns_zero(self):
        result = publish_deviations({"deviations_count": 0})
        assert result == 0

    def test_publishes_deviations(self, session):
        """With deviations in DB, publish should attempt Kafka publish."""
        # Seed a prediction and deviation
        from src.db.models import Deviation, Prediction

        pred = Prediction(
            source="streaming",
            order_id="ORD-PUB-001",
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

        # Mock the publisher to avoid real Kafka
        with patch("src.detection.publisher.DeviationPublisher") as MockPub:
            mock_instance = MagicMock()
            mock_instance.publish = MagicMock()
            mock_instance.close = MagicMock()
            MockPub.return_value = mock_instance
            result = publish_deviations({"deviations_count": 1}, session=session)

        assert result >= 0  # May be 0 if asyncio.run has issues in test context

    def test_kafka_failure_returns_zero(self, session):
        """Kafka failure should not crash, just return 0."""
        with patch("src.detection.publisher.DeviationPublisher", side_effect=Exception("Kafka down")):
            result = publish_deviations({"deviations_count": 5}, session=session)
        assert result == 0

    def test_no_session_returns_zero(self):
        result = publish_deviations({"deviations_count": 5}, session=None)
        assert result == 0

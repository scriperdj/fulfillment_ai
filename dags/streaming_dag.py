"""Airflow streaming DAG — consume fulfillment events from Kafka in micro-batches.

Consumes from ``fulfillment-events`` topic, processes through the unified
pipeline, and publishes critical deviations to ``deviation-events``.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from datetime import datetime
from typing import Any

import pandas as pd

logger = logging.getLogger(__name__)

# Defaults — overridable via DAG conf
DEFAULT_BATCH_TIMEOUT_SECONDS = 15
DEFAULT_BATCH_MAX_MESSAGES = 1000


# ---------------------------------------------------------------------------
# Task functions (standalone, testable without Airflow or Kafka)
# ---------------------------------------------------------------------------


def consume_micro_batch(
    *,
    bootstrap_servers: str | None = None,
    topic: str = "fulfillment-events",
    group_id: str = "streaming-dag-consumer",
    batch_timeout: int = DEFAULT_BATCH_TIMEOUT_SECONDS,
    batch_max_messages: int = DEFAULT_BATCH_MAX_MESSAGES,
) -> list[str]:
    """Collect a micro-batch of raw JSON messages from Kafka.

    Returns when EITHER condition is met:
    - ``batch_timeout`` seconds have elapsed, OR
    - ``batch_max_messages`` messages have been collected.

    Returns a list of raw JSON strings.
    Gracefully handles Kafka being unavailable (returns empty list).
    """
    from src.config.settings import get_settings

    broker = bootstrap_servers or get_settings().KAFKA_BROKER
    messages: list[str] = []

    try:
        from kafka import KafkaConsumer  # kafka-python

        consumer = KafkaConsumer(
            topic,
            bootstrap_servers=broker,
            group_id=group_id,
            auto_offset_reset="latest",
            enable_auto_commit=True,
            consumer_timeout_ms=batch_timeout * 1000,
            value_deserializer=lambda m: m.decode("utf-8"),
        )
    except Exception:
        logger.warning("Kafka consumer unavailable at %s — returning empty batch", broker, exc_info=True)
        return messages

    try:
        start = time.monotonic()
        for msg in consumer:
            messages.append(msg.value)
            if len(messages) >= batch_max_messages:
                logger.info("Micro-batch full: %d messages collected", len(messages))
                break
            if time.monotonic() - start >= batch_timeout:
                logger.info("Micro-batch timeout: %d messages collected in %.1fs", len(messages), batch_timeout)
                break
    except Exception:
        logger.warning("Error consuming from Kafka", exc_info=True)
    finally:
        try:
            consumer.close()
        except Exception:
            pass

    logger.info("Micro-batch collected %d messages from %s", len(messages), topic)
    return messages


def deserialize_messages(raw_messages: list[str]) -> list[dict[str, Any]]:
    """Parse raw JSON strings into order dicts.

    Malformed messages are logged and skipped.
    """
    orders: list[dict[str, Any]] = []
    for i, raw in enumerate(raw_messages):
        try:
            data = json.loads(raw)
            if not isinstance(data, dict):
                logger.warning("Message %d is not a dict, skipping", i)
                continue
            if "order_id" not in data:
                logger.warning("Message %d missing order_id, skipping", i)
                continue
            orders.append(data)
        except (json.JSONDecodeError, TypeError):
            logger.warning("Malformed JSON in message %d, skipping", i)
    logger.info("Deserialized %d/%d messages successfully", len(orders), len(raw_messages))
    return orders


def validate_and_process(
    orders: list[dict[str, Any]],
    *,
    session: Any,
) -> dict[str, Any]:
    """Validate schema and run the unified processing pipeline.

    Returns the pipeline summary dict.
    """
    if not orders:
        return {"predictions_count": 0, "deviations_count": 0, "severity_breakdown": {}}

    from src.ingestion.schema_validator import validate_csv
    from src.pipeline.processor import run_pipeline

    df = pd.DataFrame(orders)
    validation = validate_csv(df)
    if not validation["valid"]:
        logger.warning(
            "Schema validation found %d errors; processing valid rows only",
            validation["error_count"],
        )

    return run_pipeline(orders, session=session, source="streaming")


def publish_deviations(
    summary: dict[str, Any],
    *,
    session: Any | None = None,
) -> int:
    """Publish critical/warning deviations to the ``deviation-events`` topic.

    Best-effort: logs warning on failure, never crashes.
    Returns count of deviations published.
    """
    deviations_count = summary.get("deviations_count", 0)
    if deviations_count == 0:
        return 0

    try:
        from src.db.models import Deviation
        from src.detection.publisher import DeviationPublisher

        if session is None:
            logger.warning("No session provided for publish_deviations; skipping")
            return 0

        devs = (
            session.query(Deviation)
            .filter(Deviation.severity.in_(["critical", "warning"]))
            .order_by(Deviation.created_at.desc())
            .limit(deviations_count)
            .all()
        )

        if not devs:
            return 0

        publisher = DeviationPublisher()

        async def _publish():
            try:
                for dev in devs:
                    order_id = dev.prediction.order_id if dev.prediction else ""
                    await publisher.publish(dev, {"order_id": order_id})
            finally:
                await publisher.close()

        try:
            loop = asyncio.get_running_loop()
            loop.create_task(_publish())
        except RuntimeError:
            asyncio.run(_publish())

        return len(devs)
    except Exception:
        logger.warning("Failed to publish deviations to Kafka", exc_info=True)
        return 0


# ---------------------------------------------------------------------------
# Airflow DAG definition (only created when Airflow is available)
# ---------------------------------------------------------------------------

try:
    from airflow.decorators import dag, task

    @dag(
        dag_id="streaming_processing",
        schedule=None,
        start_date=datetime(2024, 1, 1),
        catchup=False,
        tags=["fulfillment", "streaming"],
        params={
            "batch_timeout": DEFAULT_BATCH_TIMEOUT_SECONDS,
            "batch_max_messages": DEFAULT_BATCH_MAX_MESSAGES,
        },
    )
    def streaming_processing_dag():
        """Consume fulfillment events from Kafka and process in micro-batches."""

        @task()
        def af_consume(**context) -> list[str]:
            params = context.get("params", {})
            return consume_micro_batch(
                batch_timeout=params.get("batch_timeout", DEFAULT_BATCH_TIMEOUT_SECONDS),
                batch_max_messages=params.get("batch_max_messages", DEFAULT_BATCH_MAX_MESSAGES),
            )

        @task()
        def af_deserialize(raw: list[str]) -> list[dict[str, Any]]:
            return deserialize_messages(raw)

        @task()
        def af_validate_process(orders: list[dict[str, Any]]) -> dict[str, Any]:
            from src.db.session import get_sync_session

            with get_sync_session() as session:
                return validate_and_process(orders, session=session)

        @task()
        def af_publish(summary: dict[str, Any]) -> None:
            from src.db.session import get_sync_session

            with get_sync_session() as session:
                publish_deviations(summary, session=session)

        raw = af_consume()
        orders = af_deserialize(raw)
        summary = af_validate_process(orders)
        af_publish(summary)

    streaming_processing_dag()

except ImportError:
    pass

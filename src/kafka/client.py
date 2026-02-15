"""Async Kafka producer/consumer utilities."""

from __future__ import annotations

import logging

from src.config.settings import get_settings

logger = logging.getLogger(__name__)


class KafkaClient:
    """Thin wrapper around an async Kafka producer.

    Handles connection errors gracefully — logs a warning instead of crashing
    when Kafka is unavailable.
    """

    def __init__(self, bootstrap_servers: str | None = None) -> None:
        self._bootstrap_servers = bootstrap_servers or get_settings().KAFKA_BROKER
        self._producer = None

    async def get_producer(self):
        """Return a lazy-initialised AIOKafkaProducer singleton."""
        if self._producer is not None:
            return self._producer

        try:
            from aiokafka import AIOKafkaProducer

            self._producer = AIOKafkaProducer(
                bootstrap_servers=self._bootstrap_servers,
            )
            await self._producer.start()
            logger.info("Kafka producer connected to %s", self._bootstrap_servers)
        except Exception:
            logger.warning(
                "Kafka unavailable at %s — messages will be dropped",
                self._bootstrap_servers,
                exc_info=True,
            )
            self._producer = None
        return self._producer

    async def publish_message(self, topic: str, key: str, value: bytes) -> None:
        """Publish a single message.  No-op if the producer is not connected."""
        producer = await self.get_producer()
        if producer is None:
            logger.warning("Kafka producer not available — dropping message for topic=%s key=%s", topic, key)
            return
        try:
            await producer.send_and_wait(topic, value=value, key=key.encode("utf-8"))
        except Exception:
            logger.warning("Failed to publish message to topic=%s key=%s", topic, key, exc_info=True)

    async def close(self) -> None:
        """Flush and close the producer if it is running."""
        if self._producer is not None:
            try:
                await self._producer.stop()
            except Exception:
                logger.warning("Error closing Kafka producer", exc_info=True)
            finally:
                self._producer = None

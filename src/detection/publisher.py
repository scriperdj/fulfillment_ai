"""Deviation event publisher — serializes and publishes to Kafka."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

from src.config.settings import get_settings
from src.db.models import Deviation
from src.kafka.client import KafkaClient

logger = logging.getLogger(__name__)


class DeviationPublisher:
    """Publishes deviation events to a Kafka topic.

    Only deviations with severity >= ``"warning"`` are published (``"info"``
    is skipped).
    """

    _PUBLISHABLE_SEVERITIES = {"warning", "critical"}

    def __init__(
        self,
        bootstrap_servers: str | None = None,
        topic: str = "deviation-events",
    ) -> None:
        self._topic = topic
        self._client = KafkaClient(bootstrap_servers=bootstrap_servers)

    @staticmethod
    def serialize_deviation(deviation: Deviation, order_context: dict[str, Any]) -> bytes:
        """Serialize a Deviation + order context to JSON bytes."""
        payload = {
            "deviation_id": str(deviation.id),
            "severity": deviation.severity,
            "reason": deviation.reason,
            "order_id": order_context.get("order_id", ""),
            "prediction_id": str(deviation.prediction_id),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        return json.dumps(payload).encode("utf-8")

    async def publish(self, deviation: Deviation, order_context: dict[str, Any]) -> None:
        """Publish a deviation event if severity >= warning."""
        if deviation.severity not in self._PUBLISHABLE_SEVERITIES:
            logger.debug(
                "Skipping publish for severity=%s deviation_id=%s",
                deviation.severity,
                deviation.id,
            )
            return

        value = self.serialize_deviation(deviation, order_context)
        key = order_context.get("order_id", str(deviation.id))
        await self._client.publish_message(self._topic, key=key, value=value)

    async def close(self) -> None:
        """Flush and close the underlying Kafka producer."""
        await self._client.close()

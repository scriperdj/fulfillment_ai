"""Kafka producer simulator — generates synthetic enriched order events.

Publishes realistic order data to the ``fulfillment-events`` topic at a
configurable rate. Designed to run as a continuous Docker service.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import random
import signal
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Realistic field distributions
# ---------------------------------------------------------------------------

_WAREHOUSE_BLOCKS = ["A", "B", "C", "D", "E"]
_WAREHOUSE_WEIGHTS = [0.15, 0.15, 0.15, 0.30, 0.25]  # D,E more common

_SHIPMENT_MODES = ["Ship", "Flight", "Road"]
_SHIPMENT_WEIGHTS = [0.50, 0.20, 0.30]  # Ship most common

_PRODUCT_IMPORTANCE = ["Low", "Medium", "High"]
_PRODUCT_IMPORTANCE_WEIGHTS = [0.35, 0.40, 0.25]

_GENDERS = ["M", "F"]

_PRODUCT_CATEGORIES = ["Electronics", "Clothing", "Home", "Sports", "Books"]

_REGIONS = ["North", "South", "East", "West", "Central"]

_PAYMENT_METHODS = ["credit_card", "debit_card", "upi", "cod", "wallet"]

_ORDER_STATUSES = ["processing", "shipped", "in_transit", "delivered"]
_ORDER_STATUS_WEIGHTS = [0.20, 0.35, 0.30, 0.15]


class ProducerSimulator:
    """Generates and publishes synthetic enriched order events to Kafka."""

    def __init__(
        self,
        broker: str = "localhost:9092",
        topic: str = "fulfillment-events",
        events_per_second: float = 5.0,
    ) -> None:
        self.broker = broker
        self.topic = topic
        self.events_per_second = events_per_second
        self._running = True
        self._producer = None

    @staticmethod
    def generate_order() -> dict[str, Any]:
        """Generate a single synthetic enriched order matching the 18-field schema."""
        order_id = f"ORD-{uuid.uuid4().hex[:8].upper()}"

        # Core 11 required fields
        warehouse_block = random.choices(_WAREHOUSE_BLOCKS, weights=_WAREHOUSE_WEIGHTS, k=1)[0]
        mode_of_shipment = random.choices(_SHIPMENT_MODES, weights=_SHIPMENT_WEIGHTS, k=1)[0]
        customer_care_calls = max(0, min(7, int(random.gauss(3, 1.5))))
        customer_rating = random.randint(1, 5)
        cost_of_the_product = random.randint(96, 310)
        prior_purchases = random.randint(2, 10)
        product_importance = random.choices(
            _PRODUCT_IMPORTANCE, weights=_PRODUCT_IMPORTANCE_WEIGHTS, k=1
        )[0]
        gender = random.choice(_GENDERS)
        discount_offered = random.randint(0, 65)

        # Bimodal weight distribution (cluster around 2000 and 5000)
        if random.random() < 0.5:
            weight_in_gms = max(1000, min(7100, int(random.gauss(2000, 500))))
        else:
            weight_in_gms = max(1000, min(7100, int(random.gauss(5000, 800))))

        # Enriched fields
        customer_id = f"CUST-{uuid.uuid4().hex[:6].upper()}"
        order_date = (
            datetime.now(timezone.utc) - timedelta(days=random.randint(0, 30))
        ).strftime("%Y-%m-%d")
        product_category = random.choice(_PRODUCT_CATEGORIES)
        order_status = random.choices(_ORDER_STATUSES, weights=_ORDER_STATUS_WEIGHTS, k=1)[0]

        return {
            "order_id": order_id,
            "warehouse_block": warehouse_block,
            "mode_of_shipment": mode_of_shipment,
            "customer_care_calls": customer_care_calls,
            "customer_rating": customer_rating,
            "cost_of_the_product": cost_of_the_product,
            "prior_purchases": prior_purchases,
            "product_importance": product_importance,
            "gender": gender,
            "discount_offered": discount_offered,
            "weight_in_gms": weight_in_gms,
            # Enriched fields
            "customer_id": customer_id,
            "order_date": order_date,
            "product_category": product_category,
            "order_status": order_status,
        }

    async def _get_producer(self):
        """Lazy-initialise the AIOKafkaProducer."""
        if self._producer is not None:
            return self._producer

        from aiokafka import AIOKafkaProducer

        self._producer = AIOKafkaProducer(
            bootstrap_servers=self.broker,
        )
        await self._producer.start()
        logger.info("Producer connected to %s", self.broker)
        return self._producer

    async def run(self) -> None:
        """Continuous loop publishing events at the configured rate."""
        producer = await self._get_producer()
        interval = 1.0 / self.events_per_second
        published = 0
        last_log_time = time.monotonic()

        logger.info(
            "Starting producer: topic=%s, rate=%.1f events/sec",
            self.topic,
            self.events_per_second,
        )

        try:
            while self._running:
                order = self.generate_order()
                value = json.dumps(order).encode("utf-8")
                key = order["order_id"].encode("utf-8")

                try:
                    await producer.send_and_wait(self.topic, value=value, key=key)
                    published += 1
                except Exception:
                    logger.warning("Failed to publish event", exc_info=True)

                # Log rate every 10 seconds
                now = time.monotonic()
                if now - last_log_time >= 10.0:
                    rate = published / (now - last_log_time)
                    logger.info("Published %d events (%.1f/sec)", published, rate)
                    published = 0
                    last_log_time = now

                await asyncio.sleep(interval)
        finally:
            await self._close()

    async def _close(self) -> None:
        """Flush and close the producer."""
        if self._producer is not None:
            try:
                await self._producer.stop()
            except Exception:
                logger.warning("Error closing producer", exc_info=True)
            finally:
                self._producer = None

    def stop(self) -> None:
        """Signal the run loop to stop."""
        self._running = False


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """Parse environment variables and start the simulator."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    broker = os.environ.get("KAFKA_BROKER", "localhost:9092")
    topic = os.environ.get("KAFKA_TOPIC", "fulfillment-events")
    eps = float(os.environ.get("EVENTS_PER_SECOND", "5"))

    simulator = ProducerSimulator(broker=broker, topic=topic, events_per_second=eps)

    loop = asyncio.new_event_loop()

    def _shutdown(sig, frame):
        logger.info("Received signal %s, shutting down ...", sig)
        simulator.stop()

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    try:
        loop.run_until_complete(simulator.run())
    except KeyboardInterrupt:
        pass
    finally:
        loop.close()
        logger.info("Producer simulator stopped.")


if __name__ == "__main__":
    main()

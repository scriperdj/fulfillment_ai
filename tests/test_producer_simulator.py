"""Tests for src/kafka/producer_simulator.py — synthetic event generator."""

from __future__ import annotations

import re
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.kafka.producer_simulator import ProducerSimulator


# ---------------------------------------------------------------------------
# generate_order tests
# ---------------------------------------------------------------------------


class TestGenerateOrder:
    def test_returns_dict(self):
        order = ProducerSimulator.generate_order()
        assert isinstance(order, dict)

    def test_has_required_fields(self):
        order = ProducerSimulator.generate_order()
        required = {
            "order_id",
            "warehouse_block",
            "mode_of_shipment",
            "customer_care_calls",
            "customer_rating",
            "cost_of_the_product",
            "prior_purchases",
            "product_importance",
            "gender",
            "discount_offered",
            "weight_in_gms",
        }
        assert required.issubset(set(order.keys()))

    def test_has_enriched_fields(self):
        order = ProducerSimulator.generate_order()
        enriched = {"customer_id", "order_date", "product_category", "order_status"}
        assert enriched.issubset(set(order.keys()))

    def test_order_id_format(self):
        order = ProducerSimulator.generate_order()
        assert re.match(r"^ORD-[A-F0-9]{8}$", order["order_id"])

    def test_warehouse_block_valid(self):
        order = ProducerSimulator.generate_order()
        assert order["warehouse_block"] in ["A", "B", "C", "D", "E"]

    def test_mode_of_shipment_valid(self):
        order = ProducerSimulator.generate_order()
        assert order["mode_of_shipment"] in ["Ship", "Flight", "Road"]

    def test_customer_rating_range(self):
        order = ProducerSimulator.generate_order()
        assert 1 <= order["customer_rating"] <= 5

    def test_cost_of_product_range(self):
        order = ProducerSimulator.generate_order()
        assert 96 <= order["cost_of_the_product"] <= 310

    def test_weight_in_gms_range(self):
        order = ProducerSimulator.generate_order()
        assert 1000 <= order["weight_in_gms"] <= 7100

    def test_passes_schema_validation(self):
        from src.ingestion.schema_validator import validate_row

        order = ProducerSimulator.generate_order()
        errors = validate_row(order)
        assert errors == [], f"Schema validation errors: {errors}"

    def test_distribution_over_1000_orders(self):
        """Generate 1000 orders and verify field distributions are realistic."""
        orders = [ProducerSimulator.generate_order() for _ in range(1000)]

        # All warehouse blocks should appear
        blocks = {o["warehouse_block"] for o in orders}
        assert blocks == {"A", "B", "C", "D", "E"}

        # All shipment modes should appear
        modes = {o["mode_of_shipment"] for o in orders}
        assert modes == {"Ship", "Flight", "Road"}

        # All importance levels should appear
        importances = {o["product_importance"] for o in orders}
        assert importances == {"Low", "Medium", "High"}

        # Ratings span 1-5
        ratings = {o["customer_rating"] for o in orders}
        assert 1 in ratings and 5 in ratings

        # Weights span a wide range
        weights = [o["weight_in_gms"] for o in orders]
        assert min(weights) < 2000
        assert max(weights) > 4000


# ---------------------------------------------------------------------------
# ProducerSimulator init tests
# ---------------------------------------------------------------------------


class TestProducerSimulatorInit:
    def test_default_config(self):
        sim = ProducerSimulator()
        assert sim.broker == "localhost:9092"
        assert sim.topic == "fulfillment-events"
        assert sim.events_per_second == 5.0

    def test_custom_config(self):
        sim = ProducerSimulator(
            broker="kafka:9092",
            topic="test-topic",
            events_per_second=10.0,
        )
        assert sim.broker == "kafka:9092"
        assert sim.topic == "test-topic"
        assert sim.events_per_second == 10.0

    def test_stop_method(self):
        sim = ProducerSimulator()
        assert sim._running is True
        sim.stop()
        assert sim._running is False


# ---------------------------------------------------------------------------
# ProducerSimulator run tests
# ---------------------------------------------------------------------------


class TestProducerSimulatorRun:
    @pytest.mark.asyncio
    async def test_run_publishes_to_kafka(self):
        """Mock the Kafka producer and verify messages are sent."""
        mock_producer = AsyncMock()
        mock_producer.start = AsyncMock()
        mock_producer.stop = AsyncMock()
        mock_producer.send_and_wait = AsyncMock()

        sim = ProducerSimulator(events_per_second=100)

        with patch("aiokafka.AIOKafkaProducer", return_value=mock_producer):
            # Run for a very short time, then stop
            import asyncio

            async def _stop_after():
                await asyncio.sleep(0.05)
                sim.stop()

            await asyncio.gather(sim.run(), _stop_after())

        assert mock_producer.send_and_wait.call_count > 0
        mock_producer.stop.assert_awaited_once()

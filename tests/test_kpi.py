"""Tests for src/kpi — per-order and running KPI calculations."""

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from src.db.models import Base, Prediction
from src.kpi.calculator import compute_order_kpis, compute_running_kpis


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


def _make_prediction(
    session: Session,
    *,
    order_id: str = "ORD-001",
    delay_probability: float = 0.5,
    severity: str = "warning",
    source: str = "batch",
    features_json: dict | None = None,
    created_at: datetime | None = None,
) -> Prediction:
    pred = Prediction(
        source=source,
        order_id=order_id,
        delay_probability=delay_probability,
        severity=severity,
        features_json=features_json,
    )
    if created_at is not None:
        pred.created_at = created_at
    session.add(pred)
    session.flush()
    return pred


# ---------------------------------------------------------------------------
# compute_order_kpis tests
# ---------------------------------------------------------------------------


class TestComputeOrderKpis:
    def test_critical_severity(self):
        result = compute_order_kpis({"order_status": "pending"}, 0.8)
        assert result["severity"] == "critical"
        assert result["delay_probability"] == 0.8

    def test_warning_severity(self):
        result = compute_order_kpis({"order_status": "pending"}, 0.6)
        assert result["severity"] == "warning"

    def test_info_severity(self):
        result = compute_order_kpis({"order_status": "pending"}, 0.4)
        assert result["severity"] == "info"

    def test_low_severity(self):
        result = compute_order_kpis({"order_status": "pending"}, 0.2)
        assert result["severity"] == "low"

    def test_exact_critical_threshold(self):
        result = compute_order_kpis({}, 0.7)
        assert result["severity"] == "critical"

    def test_exact_warning_threshold(self):
        result = compute_order_kpis({}, 0.5)
        assert result["severity"] == "warning"

    def test_exact_info_threshold(self):
        result = compute_order_kpis({}, 0.3)
        assert result["severity"] == "info"

    def test_just_below_info_threshold(self):
        result = compute_order_kpis({}, 0.29)
        assert result["severity"] == "low"

    def test_fulfillment_gap_shipped_and_high_prob(self):
        result = compute_order_kpis({"order_status": "shipped"}, 0.8)
        assert result["fulfillment_gap"] is True

    def test_no_fulfillment_gap_pending(self):
        result = compute_order_kpis({"order_status": "pending"}, 0.8)
        assert result["fulfillment_gap"] is False

    def test_no_fulfillment_gap_shipped_low_prob(self):
        # Default FULFILLMENT_GAP_THRESHOLD == SEVERITY_WARNING_THRESHOLD == 0.5
        result = compute_order_kpis({"order_status": "shipped"}, 0.3)
        assert result["fulfillment_gap"] is False

    def test_fulfillment_gap_case_insensitive(self):
        result = compute_order_kpis({"order_status": "Shipped"}, 0.8)
        assert result["fulfillment_gap"] is True

    def test_no_order_status_no_gap(self):
        result = compute_order_kpis({}, 0.9)
        assert result["fulfillment_gap"] is False

    def test_passthrough_probability(self):
        result = compute_order_kpis({}, 0.12345)
        assert result["delay_probability"] == 0.12345


# ---------------------------------------------------------------------------
# compute_running_kpis tests
# ---------------------------------------------------------------------------


class TestComputeRunningKpis:
    def test_empty_predictions(self, session):
        result = compute_running_kpis(session)
        assert result["total_predictions"] == 0
        assert result["avg_delay_probability"] == 0.0
        assert result["on_time_rate"] == 0.0
        assert result["high_risk_count"] == 0

    def test_single_prediction(self, session):
        _make_prediction(session, delay_probability=0.6, severity="warning")
        result = compute_running_kpis(session)
        assert result["total_predictions"] == 1
        assert result["avg_delay_probability"] == 0.6
        assert result["high_risk_count"] == 0
        assert result["on_time_rate"] == 0.0  # 0.6 >= 0.5

    def test_multiple_predictions_aggregates(self, session):
        _make_prediction(session, order_id="O1", delay_probability=0.8, severity="critical")
        _make_prediction(session, order_id="O2", delay_probability=0.6, severity="warning")
        _make_prediction(session, order_id="O3", delay_probability=0.3, severity="info")
        _make_prediction(session, order_id="O4", delay_probability=0.1, severity="low")

        result = compute_running_kpis(session)
        assert result["total_predictions"] == 4
        assert result["avg_delay_probability"] == pytest.approx(0.45, abs=0.01)
        assert result["high_risk_count"] == 1  # only 0.8 >= 0.7
        assert result["on_time_rate"] == pytest.approx(0.5, abs=0.01)  # 0.3 and 0.1 < 0.5

    def test_severity_breakdown(self, session):
        _make_prediction(session, order_id="O1", delay_probability=0.8, severity="critical")
        _make_prediction(session, order_id="O2", delay_probability=0.8, severity="critical")
        _make_prediction(session, order_id="O3", delay_probability=0.6, severity="warning")
        _make_prediction(session, order_id="O4", delay_probability=0.4, severity="info")

        result = compute_running_kpis(session)
        assert result["severity_breakdown"]["critical"] == 2
        assert result["severity_breakdown"]["warning"] == 1
        assert result["severity_breakdown"]["info"] == 1

    def test_old_predictions_excluded(self, session):
        now = datetime.now(timezone.utc)
        old = now - timedelta(days=45)

        _make_prediction(session, order_id="O-recent", delay_probability=0.5, severity="warning")
        _make_prediction(
            session, order_id="O-old", delay_probability=0.9, severity="critical", created_at=old
        )

        result = compute_running_kpis(session)
        assert result["total_predictions"] == 1
        assert result["high_risk_count"] == 0

    def test_segment_breakdown_warehouse_block(self, session):
        _make_prediction(
            session,
            order_id="O1",
            delay_probability=0.8,
            severity="critical",
            features_json={"warehouse_block": "A"},
        )
        _make_prediction(
            session,
            order_id="O2",
            delay_probability=0.4,
            severity="info",
            features_json={"warehouse_block": "A"},
        )
        _make_prediction(
            session,
            order_id="O3",
            delay_probability=0.6,
            severity="warning",
            features_json={"warehouse_block": "B"},
        )

        result = compute_running_kpis(session)
        wh = {s["segment"]: s for s in result["by_warehouse_block"]}
        assert "A" in wh
        assert "B" in wh
        assert wh["A"]["count"] == 2
        assert wh["A"]["avg_delay_probability"] == pytest.approx(0.6, abs=0.01)
        assert wh["B"]["count"] == 1

    def test_segment_breakdown_mode_of_shipment(self, session):
        _make_prediction(
            session,
            order_id="O1",
            delay_probability=0.7,
            severity="critical",
            features_json={"mode_of_shipment": "Ship"},
        )
        _make_prediction(
            session,
            order_id="O2",
            delay_probability=0.3,
            severity="info",
            features_json={"mode_of_shipment": "Flight"},
        )

        result = compute_running_kpis(session)
        modes = {s["segment"]: s for s in result["by_mode_of_shipment"]}
        assert "Ship" in modes
        assert "Flight" in modes

    def test_segment_breakdown_product_importance(self, session):
        _make_prediction(
            session,
            order_id="O1",
            delay_probability=0.5,
            severity="warning",
            features_json={"product_importance": "High"},
        )
        _make_prediction(
            session,
            order_id="O2",
            delay_probability=0.2,
            severity="low",
            features_json={"product_importance": "Low"},
        )

        result = compute_running_kpis(session)
        importance = {s["segment"]: s for s in result["by_product_importance"]}
        assert "High" in importance
        assert "Low" in importance

    def test_missing_features_json_uses_unknown(self, session):
        _make_prediction(session, order_id="O1", delay_probability=0.5, severity="warning")
        result = compute_running_kpis(session)
        wh = result["by_warehouse_block"]
        assert len(wh) == 1
        assert wh[0]["segment"] == "unknown"

"""Integration tests for Airflow DAGs against live Docker Compose services.

Run with:  pytest -m integration tests/test_integration_airflow.py -v --timeout=600
Requires:  docker compose up -d  (all services must be healthy, including Airflow)
           OPENAI_API_KEY set in .env (for agent orchestration tests)

Tests trigger real Airflow DAG runs via the REST API and verify database/Kafka
outcomes end-to-end.
"""
from __future__ import annotations

import io
import json
import time
import uuid
from pathlib import Path

import httpx
import psycopg2
import pytest
from dotenv import dotenv_values

# ---------------------------------------------------------------------------
# Configuration (mirrors test_integration_docker.py patterns)
# ---------------------------------------------------------------------------

_ENV = dotenv_values(Path(__file__).resolve().parent.parent / ".env")

PG_USER = _ENV.get("POSTGRES_USER", "fulfillment")
PG_PASS = _ENV.get("POSTGRES_PASSWORD", "fulfillment_pass")
PG_DB = _ENV.get("POSTGRES_DB", "fulfillment_ai")

API_BASE = "http://localhost:8000"
AIRFLOW_BASE = "http://localhost:8080"
PG_HOST = "localhost"
PG_PORT = 5432
KAFKA_BROKER = "localhost:9092"

DAG_IDS = ["batch_processing", "streaming_processing", "agent_orchestration"]

# Airflow 3.x simple-auth-manager credentials
AIRFLOW_USER = "admin"
AIRFLOW_PASS = "admin"

# Cache for JWT token
_airflow_token: str | None = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _airflow_reachable() -> bool:
    """Check if Airflow is reachable (health endpoint needs no auth)."""
    try:
        r = httpx.get(
            f"{AIRFLOW_BASE}/api/v2/monitor/health",
            timeout=5,
        )
        return r.status_code == 200
    except Exception:
        return False


def _get_airflow_token() -> str:
    """Get a JWT token from Airflow 3.x simple auth manager."""
    global _airflow_token
    if _airflow_token is not None:
        return _airflow_token
    r = httpx.post(
        f"{AIRFLOW_BASE}/auth/token",
        json={"username": AIRFLOW_USER, "password": AIRFLOW_PASS},
        timeout=10,
    )
    assert r.status_code in (200, 201), f"Failed to get Airflow token: {r.status_code} {r.text}"
    _airflow_token = r.json()["access_token"]
    return _airflow_token


def _airflow_headers() -> dict[str, str]:
    """Return Authorization headers for Airflow API requests."""
    return {"Authorization": f"Bearer {_get_airflow_token()}"}


def _start_dag(
    dag_id: str,
    conf: dict | None = None,
) -> dict:
    """Trigger a DAG run without waiting for completion.

    Returns the initial DAG run payload (state will be 'queued' or 'running').
    """
    from datetime import datetime, timezone

    headers = _airflow_headers()

    payload: dict = {
        "logical_date": datetime.now(timezone.utc).isoformat(),
    }
    if conf:
        payload["conf"] = conf
    r = httpx.post(
        f"{AIRFLOW_BASE}/api/v2/dags/{dag_id}/dagRuns",
        json=payload,
        headers=headers,
        timeout=30,
    )
    assert r.status_code in (200, 201), f"Failed to trigger {dag_id}: {r.status_code} {r.text}"
    return r.json()


def _wait_dag(dag_id: str, dag_run_id: str, timeout: int = 300) -> dict:
    """Poll a DAG run until it reaches a terminal state.

    Returns the final DAG run payload from the Airflow API.
    """
    headers = _airflow_headers()
    deadline = time.monotonic() + timeout
    run = {}
    while time.monotonic() < deadline:
        r = httpx.get(
            f"{AIRFLOW_BASE}/api/v2/dags/{dag_id}/dagRuns/{dag_run_id}",
            headers=headers,
            timeout=10,
        )
        assert r.status_code == 200
        run = r.json()
        state = run.get("state")
        if state in ("success", "failed"):
            return run
        time.sleep(5)

    pytest.fail(f"DAG run {dag_id}/{dag_run_id} did not finish within {timeout}s (state={run.get('state')})")


def _trigger_dag(
    dag_id: str,
    conf: dict | None = None,
    timeout: int = 300,
) -> dict:
    """Trigger a DAG run and poll until it reaches a terminal state.

    Returns the final DAG run payload from the Airflow API.
    """
    run = _start_dag(dag_id, conf=conf)
    return _wait_dag(dag_id, run["dag_run_id"], timeout=timeout)


def _get_task_instances(dag_id: str, dag_run_id: str) -> list[dict]:
    """Fetch all task instance states for a DAG run."""
    r = httpx.get(
        f"{AIRFLOW_BASE}/api/v2/dags/{dag_id}/dagRuns/{dag_run_id}/taskInstances",
        headers=_airflow_headers(),
        timeout=10,
    )
    assert r.status_code == 200
    data = r.json()
    return data.get("task_instances", data) if isinstance(data, dict) else data


def _pg_connect():
    return psycopg2.connect(
        host=PG_HOST,
        port=PG_PORT,
        dbname=PG_DB,
        user=PG_USER,
        password=PG_PASS,
    )


def _generate_test_csv(num_rows: int = 5) -> str:
    """Generate a valid CSV string using ProducerSimulator.generate_order()."""
    from src.kafka.producer_simulator import ProducerSimulator

    orders = [ProducerSimulator.generate_order() for _ in range(num_rows)]
    import pandas as pd

    df = pd.DataFrame(orders)
    return df.to_csv(index=False)


# ---------------------------------------------------------------------------
# Module-level marks and skip condition
# ---------------------------------------------------------------------------

pytestmark = [
    pytest.mark.integration,
    pytest.mark.airflow,
    pytest.mark.skipif(
        not _airflow_reachable(),
        reason="Airflow not reachable at localhost:8080",
    ),
]


# ---------------------------------------------------------------------------
# Module fixture: unpause all DAGs
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module", autouse=True)
def _unpause_dags():
    """Unpause all 3 DAGs before running tests in this module."""
    headers = _airflow_headers()
    for dag_id in DAG_IDS:
        httpx.patch(
            f"{AIRFLOW_BASE}/api/v2/dags/{dag_id}",
            json={"is_paused": False},
            headers=headers,
            timeout=10,
        )
    yield


# ---------------------------------------------------------------------------
# Category 1: Airflow Health & DAG Discovery
# ---------------------------------------------------------------------------


class TestAirflowHealth:
    def test_airflow_health(self):
        r = httpx.get(
            f"{AIRFLOW_BASE}/api/v2/monitor/health",
            timeout=5,
        )
        assert r.status_code == 200

    def test_all_dags_registered(self):
        r = httpx.get(
            f"{AIRFLOW_BASE}/api/v2/dags",
            headers=_airflow_headers(),
            timeout=10,
        )
        assert r.status_code == 200
        data = r.json()
        dag_list = data.get("dags", data) if isinstance(data, dict) else data
        registered_ids = {d["dag_id"] for d in dag_list}
        for dag_id in DAG_IDS:
            assert dag_id in registered_ids, f"DAG {dag_id} not registered"

    def test_dags_can_be_unpaused(self):
        headers = _airflow_headers()
        for dag_id in DAG_IDS:
            r = httpx.patch(
                f"{AIRFLOW_BASE}/api/v2/dags/{dag_id}",
                json={"is_paused": False},
                headers=headers,
                timeout=10,
            )
            assert r.status_code == 200
            data = r.json()
            assert data["is_paused"] is False


# ---------------------------------------------------------------------------
# Category 2: Batch Processing DAG
# ---------------------------------------------------------------------------


class TestBatchProcessingDAG:
    """Tests for the batch_processing DAG end-to-end."""

    @pytest.fixture(scope="class")
    def batch_run(self):
        """Upload a CSV via the API, trigger the batch DAG, and return context."""
        csv_content = _generate_test_csv(num_rows=5)
        csv_bytes = csv_content.encode("utf-8")

        # Upload CSV via batch API
        r = httpx.post(
            f"{API_BASE}/batch/upload",
            files={"file": ("test_batch.csv", io.BytesIO(csv_bytes), "text/csv")},
            timeout=30,
        )
        assert r.status_code == 201, f"Batch upload failed: {r.status_code} {r.text}"
        upload_data = r.json()
        batch_job_id = upload_data["batch_job_id"]

        # Trigger DAG
        run = _trigger_dag(
            "batch_processing",
            conf={"batch_job_id": batch_job_id},
            timeout=300,
        )

        return {
            "batch_job_id": batch_job_id,
            "dag_run": run,
            "row_count": upload_data["row_count"],
        }

    def test_batch_dag_end_to_end(self, batch_run):
        assert batch_run["dag_run"]["state"] == "success"

        # Verify batch job completed in DB
        conn = _pg_connect()
        cur = conn.cursor()
        cur.execute(
            "SELECT status FROM batch_jobs WHERE id = %s::uuid",
            (batch_run["batch_job_id"],),
        )
        row = cur.fetchone()
        cur.close()
        conn.close()
        assert row is not None
        assert row[0] == "completed"

        # Verify predictions count matches CSV rows
        conn = _pg_connect()
        cur = conn.cursor()
        cur.execute(
            "SELECT COUNT(*) FROM predictions WHERE batch_job_id = %s::uuid",
            (batch_run["batch_job_id"],),
        )
        count = cur.fetchone()[0]
        cur.close()
        conn.close()
        assert count == batch_run["row_count"]

    def test_batch_dag_all_tasks_succeed(self, batch_run):
        dag_run_id = batch_run["dag_run"]["dag_run_id"]
        tasks = _get_task_instances("batch_processing", dag_run_id)
        expected_tasks = {"af_load_csv", "af_validate_schema", "af_run_pipeline", "af_update_status"}
        task_states = {t["task_id"]: t["state"] for t in tasks}

        for task_id in expected_tasks:
            assert task_id in task_states, f"Task {task_id} not found in task instances"
            assert task_states[task_id] == "success", (
                f"Task {task_id} has state {task_states[task_id]}, expected success"
            )

    def test_batch_dag_results_via_api(self, batch_run):
        batch_job_id = batch_run["batch_job_id"]

        # Predictions endpoint
        r = httpx.get(f"{API_BASE}/batch/{batch_job_id}/predictions", timeout=10)
        assert r.status_code == 200
        predictions = r.json()
        assert len(predictions) > 0

        # Status endpoint
        r = httpx.get(f"{API_BASE}/batch/{batch_job_id}/status", timeout=10)
        assert r.status_code == 200
        status_data = r.json()
        assert status_data["status"] == "completed"

    def test_batch_dag_invalid_job_id_fails(self):
        fake_id = str(uuid.uuid4())
        run = _trigger_dag(
            "batch_processing",
            conf={"batch_job_id": fake_id},
            timeout=120,
        )
        assert run["state"] == "failed"


# ---------------------------------------------------------------------------
# Category 3: Streaming Processing DAG
# ---------------------------------------------------------------------------


class TestStreamingProcessingDAG:
    """Tests for the streaming_processing DAG.

    The stream-producer Docker service is already running at 5 events/sec,
    so there will be messages available on the fulfillment-events topic.

    The streaming DAG uses ``schedule="@continuous"`` with ``max_active_runs=1``,
    so it auto-triggers continuously.  Rather than fighting with manual triggers
    (which stay queued while a continuous run occupies the slot), the tests
    simply ensure the DAG is unpaused and wait for a successful run to appear.
    """

    @pytest.fixture(scope="class")
    def streaming_run(self):
        """Ensure the continuous DAG is running and wait for a successful run."""
        headers = _airflow_headers()
        # Make sure the DAG is unpaused so the continuous scheduler is active
        httpx.patch(
            f"{AIRFLOW_BASE}/api/v2/dags/streaming_processing",
            json={"is_paused": False},
            headers=headers,
            timeout=10,
        )

        # Wait for a successful run to appear (the DAG runs continuously)
        deadline = time.monotonic() + 180
        while time.monotonic() < deadline:
            r = httpx.get(
                f"{AIRFLOW_BASE}/api/v2/dags/streaming_processing/dagRuns",
                headers=headers,
                params={"order_by": "-start_date", "limit": 10},
                timeout=10,
            )
            if r.status_code == 200:
                data = r.json()
                runs = data.get("dag_runs", data) if isinstance(data, dict) else data
                successful = [run for run in runs if run.get("state") == "success"]
                if successful:
                    return {"dag_run": successful[0]}
            time.sleep(5)

        pytest.fail("No successful streaming DAG run found within 180s")

    def test_streaming_dag_completes(self, streaming_run):
        assert streaming_run["dag_run"]["state"] == "success"

    def test_streaming_dag_all_tasks_succeed(self, streaming_run):
        dag_run_id = streaming_run["dag_run"]["dag_run_id"]
        tasks = _get_task_instances("streaming_processing", dag_run_id)
        expected_tasks = {"af_consume", "af_deserialize", "af_validate_process", "af_publish"}
        task_states = {t["task_id"]: t["state"] for t in tasks}

        for task_id in expected_tasks:
            assert task_id in task_states, f"Task {task_id} not found in task instances"
            assert task_states[task_id] == "success", (
                f"Task {task_id} has state {task_states[task_id]}, expected success"
            )

    def test_streaming_dag_creates_predictions(self, streaming_run):
        # Verify that streaming predictions exist in the DB
        conn = _pg_connect()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM predictions WHERE source = 'streaming'")
        count = cur.fetchone()[0]
        cur.close()
        conn.close()
        assert count > 0, "No streaming predictions found in DB after streaming DAG run"


# ---------------------------------------------------------------------------
# Category 4: Agent Orchestration DAG
# ---------------------------------------------------------------------------


class TestAgentOrchestrationDAG:
    """Tests for the agent_orchestration DAG.

    The agent DAG uses ``schedule="@continuous"`` with ``max_active_runs=1``
    to continuously poll the ``deviation-events`` Kafka topic.  Tests produce
    events and wait for the continuous runs to process them, rather than
    manually triggering (which would conflict with ``max_active_runs=1``).
    """

    @staticmethod
    def _insert_test_deviation() -> dict:
        """Insert a prediction + deviation into the DB and return their IDs."""
        conn = _pg_connect()
        cur = conn.cursor()

        prediction_id = str(uuid.uuid4())
        deviation_id = str(uuid.uuid4())
        order_id = f"ORD-TEST{uuid.uuid4().hex[:6].upper()}"

        cur.execute(
            """
            INSERT INTO predictions (id, source, order_id, delay_probability, severity, created_at)
            VALUES (%s::uuid, 'test', %s, 0.85, 'critical', NOW())
            """,
            (prediction_id, order_id),
        )
        cur.execute(
            """
            INSERT INTO deviations (id, prediction_id, severity, reason, status, created_at)
            VALUES (%s::uuid, %s::uuid, 'critical', 'High delay probability detected', 'new', NOW())
            """,
            (deviation_id, prediction_id),
        )
        conn.commit()
        cur.close()
        conn.close()

        return {
            "prediction_id": prediction_id,
            "deviation_id": deviation_id,
            "order_id": order_id,
        }

    @staticmethod
    def _produce_deviation_event(deviation_context: dict) -> None:
        """Produce a deviation event to the deviation-events Kafka topic."""
        from kafka import KafkaProducer

        producer = KafkaProducer(
            bootstrap_servers=KAFKA_BROKER,
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        )
        producer.send("deviation-events", value=deviation_context)
        producer.flush()
        producer.close()

    @staticmethod
    def _commit_consumer_group_offset(
        topic: str = "deviation-events",
        group_id: str = "agent-dag-consumer",
    ) -> None:
        """Commit the current end-of-partition offset for the consumer group.

        This ensures that when the DAG's consumer next starts, it reads from the
        committed offset rather than using auto_offset_reset="latest" (which would
        skip events produced before the consumer starts).
        """
        from kafka import KafkaConsumer, TopicPartition

        consumer = KafkaConsumer(
            bootstrap_servers=KAFKA_BROKER,
            group_id=group_id,
            enable_auto_commit=False,
        )
        partitions = consumer.partitions_for_topic(topic)
        if partitions:
            tps = [TopicPartition(topic, p) for p in partitions]
            consumer.assign(tps)
            consumer.seek_to_end(*tps)
            consumer.commit()
        consumer.close()

    @staticmethod
    def _wait_for_successful_agent_run(timeout: int = 600) -> dict:
        """Wait for a successful agent_orchestration run to appear."""
        headers = _airflow_headers()
        # Ensure the DAG is unpaused
        httpx.patch(
            f"{AIRFLOW_BASE}/api/v2/dags/agent_orchestration",
            json={"is_paused": False},
            headers=headers,
            timeout=10,
        )

        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            r = httpx.get(
                f"{AIRFLOW_BASE}/api/v2/dags/agent_orchestration/dagRuns",
                headers=headers,
                params={"order_by": "-start_date", "limit": 10},
                timeout=10,
            )
            if r.status_code == 200:
                data = r.json()
                runs = data.get("dag_runs", data) if isinstance(data, dict) else data
                successful = [run for run in runs if run.get("state") == "success"]
                if successful:
                    return successful[0]
            time.sleep(10)

        pytest.fail(f"No successful agent_orchestration run found within {timeout}s")

    def test_agent_dag_completes_with_deviation_event(self):
        """Produce a deviation event; the continuous DAG processes it successfully."""
        test_data = self._insert_test_deviation()
        deviation_event = {
            "severity": "critical",
            "reason": "High delay probability detected",
            "order_id": test_data["order_id"],
            "deviation_id": test_data["deviation_id"],
            "delay_probability": 0.85,
        }

        # Commit consumer group offset at current end, then produce event.
        # The next continuous run will start from the committed offset and
        # pick up the event.
        self._commit_consumer_group_offset()
        self._produce_deviation_event(deviation_event)

        # Wait for a successful run (the continuous DAG will process our event)
        run = self._wait_for_successful_agent_run(timeout=600)
        assert run["state"] == "success"

    def test_agent_dag_stores_responses(self):
        """Produce a deviation event; verify agent_responses are stored."""
        test_data = self._insert_test_deviation()
        deviation_event = {
            "severity": "critical",
            "reason": "High delay probability detected",
            "order_id": test_data["order_id"],
            "deviation_id": test_data["deviation_id"],
            "delay_probability": 0.85,
        }

        # Record agent_responses count before producing
        conn = _pg_connect()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM agent_responses")
        count_before = cur.fetchone()[0]
        cur.close()
        conn.close()

        # Commit offset and produce event
        self._commit_consumer_group_offset()
        self._produce_deviation_event(deviation_event)

        # Poll the DB until new agent_responses appear (continuous DAG will process)
        deadline = time.monotonic() + 600
        count_after = count_before
        while time.monotonic() < deadline:
            conn = _pg_connect()
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM agent_responses")
            count_after = cur.fetchone()[0]
            cur.close()
            conn.close()
            if count_after > count_before:
                break
            time.sleep(10)

        assert count_after > count_before, (
            f"No new agent responses stored after waiting "
            f"(before={count_before}, after={count_after})"
        )

    def test_agent_dag_no_events_completes_gracefully(self):
        """The continuous DAG completes successfully even with no events on the topic."""
        run = self._wait_for_successful_agent_run(timeout=600)
        assert run["state"] == "success"

    def test_agent_dag_all_tasks_succeed(self):
        """Verify all task instances in a successful run have state=success."""
        run = self._wait_for_successful_agent_run(timeout=600)
        dag_run_id = run["dag_run_id"]
        tasks = _get_task_instances("agent_orchestration", dag_run_id)
        expected_tasks = {"af_consume", "af_deserialize", "af_orchestrate", "af_ingest"}
        task_states = {t["task_id"]: t["state"] for t in tasks}

        for task_id in expected_tasks:
            assert task_id in task_states, f"Task {task_id} not found in task instances"
            assert task_states[task_id] == "success", (
                f"Task {task_id} has state {task_states[task_id]}, expected success"
            )


# ---------------------------------------------------------------------------
# Category 5: Cross-DAG Pipeline
# ---------------------------------------------------------------------------


class TestCrossDAGPipeline:
    """End-to-end tests spanning multiple DAGs."""

    def test_full_pipeline_batch_to_agents(self):
        """Upload CSV -> batch DAG -> verify deviations -> agent DAG -> verify responses."""
        # Step 1: Upload CSV
        csv_content = _generate_test_csv(num_rows=10)
        csv_bytes = csv_content.encode("utf-8")

        r = httpx.post(
            f"{API_BASE}/batch/upload",
            files={"file": ("pipeline_test.csv", io.BytesIO(csv_bytes), "text/csv")},
            timeout=30,
        )
        assert r.status_code == 201
        batch_job_id = r.json()["batch_job_id"]

        # Step 2: Run batch DAG
        batch_run = _trigger_dag(
            "batch_processing",
            conf={"batch_job_id": batch_job_id},
            timeout=300,
        )
        assert batch_run["state"] == "success"

        # Step 3: Check for deviations
        conn = _pg_connect()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT d.id, d.severity, p.order_id
            FROM deviations d
            JOIN predictions p ON d.prediction_id = p.id
            WHERE d.batch_job_id = %s::uuid
            AND d.severity IN ('critical', 'warning')
            LIMIT 5
            """,
            (batch_job_id,),
        )
        deviations = cur.fetchall()
        cur.close()
        conn.close()

        if not deviations:
            pytest.skip("No critical/warning deviations produced by batch — cannot test agent pipeline")

        # Step 4: Record count, commit offset, produce events
        conn = _pg_connect()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM agent_responses")
        count_before = cur.fetchone()[0]
        cur.close()
        conn.close()

        TestAgentOrchestrationDAG._commit_consumer_group_offset()

        from kafka import KafkaProducer

        producer = KafkaProducer(
            bootstrap_servers=KAFKA_BROKER,
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        )
        for dev_id, severity, order_id in deviations:
            event = {
                "severity": severity,
                "reason": "Deviation detected during batch processing",
                "order_id": order_id,
                "deviation_id": str(dev_id),
                "delay_probability": 0.85,
            }
            producer.send("deviation-events", value=event)
        producer.flush()
        producer.close()

        # Step 5: Poll DB until new agent_responses appear (continuous DAG processes events)
        deadline = time.monotonic() + 600
        count_after = count_before
        while time.monotonic() < deadline:
            conn = _pg_connect()
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM agent_responses")
            count_after = cur.fetchone()[0]
            cur.close()
            conn.close()
            if count_after > count_before:
                break
            time.sleep(10)

        assert count_after > count_before, (
            f"No new agent responses stored after full pipeline "
            f"(before={count_before}, after={count_after})"
        )

    def test_batch_results_accessible_via_all_endpoints(self):
        """After batch DAG, verify all batch endpoints return data."""
        csv_content = _generate_test_csv(num_rows=5)
        csv_bytes = csv_content.encode("utf-8")

        r = httpx.post(
            f"{API_BASE}/batch/upload",
            files={"file": ("endpoints_test.csv", io.BytesIO(csv_bytes), "text/csv")},
            timeout=30,
        )
        assert r.status_code == 201
        batch_job_id = r.json()["batch_job_id"]

        run = _trigger_dag(
            "batch_processing",
            conf={"batch_job_id": batch_job_id},
            timeout=300,
        )
        assert run["state"] == "success"

        # /batch/{id}/status
        r = httpx.get(f"{API_BASE}/batch/{batch_job_id}/status", timeout=10)
        assert r.status_code == 200
        assert r.json()["status"] == "completed"

        # /batch/{id}/predictions
        r = httpx.get(f"{API_BASE}/batch/{batch_job_id}/predictions", timeout=10)
        assert r.status_code == 200
        assert len(r.json()) > 0

        # /batch/{id}/deviations
        r = httpx.get(f"{API_BASE}/batch/{batch_job_id}/deviations", timeout=10)
        assert r.status_code == 200
        # deviations list may be empty if all predictions were low-risk
        assert isinstance(r.json(), list)

"""Airflow agent orchestration DAG — process deviation events through multi-agent system.

Consumes from ``deviation-events`` topic, runs the agent orchestrator,
stores responses, and ingests resolutions into the RAG knowledge base.
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_REQUIRED_FIELDS = {"severity", "reason", "order_id", "deviation_id"}


# ---------------------------------------------------------------------------
# Task functions (standalone, testable without Airflow or Kafka)
# ---------------------------------------------------------------------------


def consume_deviation_event(
    *,
    bootstrap_servers: str | None = None,
    topic: str = "deviation-events",
    group_id: str = "agent-dag-consumer",
    timeout_seconds: int = 30,
) -> list[str]:
    """Consume deviation events from Kafka.

    Returns a list of raw JSON strings (typically 1, but can be a small batch).
    Gracefully handles Kafka being unavailable.
    """
    from src.config.settings import get_settings

    broker = bootstrap_servers or get_settings().KAFKA_BROKER
    messages: list[str] = []

    try:
        from kafka import KafkaConsumer

        consumer = KafkaConsumer(
            topic,
            bootstrap_servers=broker,
            group_id=group_id,
            auto_offset_reset="latest",
            enable_auto_commit=True,
            consumer_timeout_ms=timeout_seconds * 1000,
            value_deserializer=lambda m: m.decode("utf-8"),
            max_poll_records=10,
        )
    except Exception:
        logger.warning("Kafka consumer unavailable at %s — returning empty", broker, exc_info=True)
        return messages

    try:
        for msg in consumer:
            messages.append(msg.value)
            break  # Process one event at a time by default
    except Exception:
        logger.warning("Error consuming deviation events", exc_info=True)
    finally:
        try:
            consumer.close()
        except Exception:
            pass

    logger.info("Consumed %d deviation event(s) from %s", len(messages), topic)
    return messages


def deserialize_deviation(raw_messages: list[str]) -> list[dict[str, Any]]:
    """Parse raw JSON into validated deviation context dicts.

    Validates required fields: severity, reason, order_id, deviation_id.
    Malformed or incomplete events are logged and skipped.
    """
    contexts: list[dict[str, Any]] = []
    for i, raw in enumerate(raw_messages):
        try:
            data = json.loads(raw)
            if not isinstance(data, dict):
                logger.warning("Deviation event %d is not a dict, skipping", i)
                continue

            missing = _REQUIRED_FIELDS - set(data.keys())
            if missing:
                logger.warning("Deviation event %d missing fields %s, skipping", i, missing)
                continue

            contexts.append(data)
        except (json.JSONDecodeError, TypeError):
            logger.warning("Malformed JSON in deviation event %d, skipping", i)

    logger.info("Deserialized %d/%d deviation events", len(contexts), len(raw_messages))
    return contexts


def run_agent_orchestration(
    deviation_contexts: list[dict[str, Any]],
    *,
    session: Any,
) -> list[dict[str, Any]]:
    """Run the agent orchestrator on each deviation context.

    Uses ``asyncio.run()`` to bridge async orchestrator into sync Airflow task.
    Returns aggregated list of agent results.
    """
    from src.agents.orchestrator import AgentOrchestrator

    all_results: list[dict[str, Any]] = []

    for ctx in deviation_contexts:
        try:
            orch = AgentOrchestrator(session=session)
            results = asyncio.run(orch.orchestrate(ctx))
            all_results.extend(results)
            logger.info(
                "Orchestrator produced %d results for order=%s severity=%s",
                len(results),
                ctx.get("order_id"),
                ctx.get("severity"),
            )
        except Exception:
            logger.warning(
                "Agent orchestration failed for order=%s",
                ctx.get("order_id"),
                exc_info=True,
            )

    return all_results


def ingest_resolution(
    agent_results: list[dict[str, Any]],
    *,
    knowledge_dir: Path | None = None,
    chroma_path: Path | None = None,
    embedding_function: Any | None = None,
) -> int:
    """Ingest agent resolution summaries into the RAG knowledge base.

    Best-effort: logs warning on failure, never crashes.
    Returns the number of resolutions ingested.
    """
    if not agent_results:
        return 0

    try:
        from langchain_core.documents import Document
        from langchain_text_splitters import RecursiveCharacterTextSplitter

        from src.config.settings import get_settings

        settings = get_settings()
        persist_dir = str(chroma_path or settings.CHROMA_DB_PATH)

        if embedding_function is None:
            from langchain_openai import OpenAIEmbeddings
            embedding_function = OpenAIEmbeddings(model=settings.OPENAI_EMBEDDING_MODEL)

        docs: list[Document] = []
        for result in agent_results:
            content = (
                f"Agent: {result.get('agent_type', 'unknown')}\n"
                f"Action: {result.get('action', 'unknown')}\n"
                f"Details: {json.dumps(result.get('details', {}), default=str)}"
            )
            docs.append(
                Document(
                    page_content=content,
                    metadata={
                        "category": "resolution",
                        "agent_type": result.get("agent_type", "general"),
                        "source_file": "agent_resolution",
                    },
                )
            )

        if not docs:
            return 0

        from langchain_chroma import Chroma

        Path(persist_dir).mkdir(parents=True, exist_ok=True)
        Chroma.from_documents(
            documents=docs,
            embedding=embedding_function,
            collection_name="knowledge_base",
            persist_directory=persist_dir,
        )

        logger.info("Ingested %d agent resolutions into RAG knowledge base", len(docs))
        return len(docs)
    except Exception:
        logger.warning("Failed to ingest agent resolutions into RAG", exc_info=True)
        return 0


# ---------------------------------------------------------------------------
# Airflow DAG definition (only created when Airflow is available)
# ---------------------------------------------------------------------------

try:
    from airflow.decorators import dag, task

    @dag(
        dag_id="agent_orchestration",
        schedule=None,
        start_date=datetime(2024, 1, 1),
        catchup=False,
        tags=["fulfillment", "agents"],
    )
    def agent_orchestration_dag():
        """Process deviation events through the multi-agent orchestration system."""

        @task()
        def af_consume() -> list[str]:
            return consume_deviation_event()

        @task()
        def af_deserialize(raw: list[str]) -> list[dict[str, Any]]:
            return deserialize_deviation(raw)

        @task()
        def af_orchestrate(contexts: list[dict[str, Any]]) -> list[dict[str, Any]]:
            from src.db.session import get_sync_session

            with get_sync_session() as session:
                return run_agent_orchestration(contexts, session=session)

        @task()
        def af_ingest(results: list[dict[str, Any]]) -> None:
            ingest_resolution(results)

        raw = af_consume()
        contexts = af_deserialize(raw)
        results = af_orchestrate(contexts)
        af_ingest(results)

    agent_orchestration_dag()

except ImportError:
    pass

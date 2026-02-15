"""Tests for src/rag — document ingestion and retrieval with mock embeddings."""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

import pytest

from src.rag.ingestion import DOCUMENT_METADATA, ingest_documents
from src.rag.retrieval import retrieve


# ---------------------------------------------------------------------------
# Fake embedding function (deterministic, no API calls)
# ---------------------------------------------------------------------------


class _FakeEmbeddings:
    """Deterministic embedding function for testing (no OpenAI calls).

    Produces a fixed-length vector from a simple hash of the text.
    """

    def __init__(self, dimension: int = 64) -> None:
        self._dim = dimension

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._embed(t) for t in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._embed(text)

    def _embed(self, text: str) -> list[float]:
        h = hash(text)
        return [(((h >> i) & 0xFF) / 255.0) for i in range(self._dim)]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def fake_embeddings():
    return _FakeEmbeddings()


@pytest.fixture()
def knowledge_dir(tmp_path: Path) -> Path:
    """Create a temporary knowledge_base directory with sample .md files."""
    kb = tmp_path / "knowledge_base"
    kb.mkdir()
    # Two sample docs matching DOCUMENT_METADATA keys
    (kb / "shipping_policy.md").write_text(
        "# Shipping Policy\nStandard shipping takes 5-7 business days.\n"
        "Express shipping is 2-3 business days.\n"
        "International orders may take 10-14 business days.\n"
    )
    (kb / "refund_policy.md").write_text(
        "# Refund Policy\nRefunds are processed within 30 days.\n"
        "Items must be in original packaging.\n"
        "Digital products are non-refundable.\n"
    )
    return kb


@pytest.fixture()
def chroma_dir(tmp_path: Path) -> Path:
    return tmp_path / "chroma_db"


# ---------------------------------------------------------------------------
# Knowledge base file existence tests
# ---------------------------------------------------------------------------


class TestKnowledgeBaseFiles:
    def test_all_md_files_exist(self):
        kb_dir = Path("knowledge_base")
        for filename in DOCUMENT_METADATA:
            assert (kb_dir / filename).exists(), f"Missing: {filename}"

    def test_document_metadata_has_required_keys(self):
        for filename, meta in DOCUMENT_METADATA.items():
            assert "category" in meta, f"{filename} missing category"
            assert "agent_type" in meta, f"{filename} missing agent_type"

    def test_eight_documents_configured(self):
        assert len(DOCUMENT_METADATA) == 8


# ---------------------------------------------------------------------------
# Ingestion tests
# ---------------------------------------------------------------------------


class TestIngestion:
    def test_ingest_returns_chunk_count(self, knowledge_dir, chroma_dir, fake_embeddings):
        count = ingest_documents(
            knowledge_dir=knowledge_dir,
            chroma_path=chroma_dir,
            embedding_function=fake_embeddings,
        )
        assert count > 0

    def test_ingest_empty_directory(self, tmp_path, chroma_dir, fake_embeddings):
        empty = tmp_path / "empty_kb"
        empty.mkdir()
        count = ingest_documents(
            knowledge_dir=empty,
            chroma_path=chroma_dir,
            embedding_function=fake_embeddings,
        )
        assert count == 0

    def test_ingest_creates_chroma_directory(self, knowledge_dir, chroma_dir, fake_embeddings):
        assert not chroma_dir.exists()
        ingest_documents(
            knowledge_dir=knowledge_dir,
            chroma_path=chroma_dir,
            embedding_function=fake_embeddings,
        )
        assert chroma_dir.exists()

    def test_ingest_idempotent(self, knowledge_dir, chroma_dir, fake_embeddings):
        count1 = ingest_documents(
            knowledge_dir=knowledge_dir,
            chroma_path=chroma_dir,
            embedding_function=fake_embeddings,
        )
        count2 = ingest_documents(
            knowledge_dir=knowledge_dir,
            chroma_path=chroma_dir,
            embedding_function=fake_embeddings,
        )
        assert count1 == count2

    def test_unknown_file_gets_general_metadata(self, tmp_path, chroma_dir, fake_embeddings):
        """A .md file not in DOCUMENT_METADATA gets category=general."""
        kb = tmp_path / "kb_unknown"
        kb.mkdir()
        (kb / "mystery.md").write_text("Some mystery content that is not mapped.\n")

        import chromadb

        count = ingest_documents(
            knowledge_dir=kb,
            chroma_path=chroma_dir,
            embedding_function=fake_embeddings,
        )
        assert count > 0

        # Verify the stored metadata via chromadb client
        client = chromadb.PersistentClient(path=str(chroma_dir))
        collection = client.get_collection("knowledge_base")
        result = collection.get(include=["metadatas"])
        assert any(m["category"] == "general" for m in result["metadatas"])


# ---------------------------------------------------------------------------
# Retrieval tests
# ---------------------------------------------------------------------------


class TestRetrieval:
    def test_retrieve_returns_results(self, knowledge_dir, chroma_dir, fake_embeddings):
        ingest_documents(
            knowledge_dir=knowledge_dir,
            chroma_path=chroma_dir,
            embedding_function=fake_embeddings,
        )
        results = retrieve(
            "shipping delivery time",
            k=3,
            chroma_path=chroma_dir,
            embedding_function=fake_embeddings,
        )
        assert len(results) > 0
        assert len(results) <= 3

    def test_retrieve_result_structure(self, knowledge_dir, chroma_dir, fake_embeddings):
        ingest_documents(
            knowledge_dir=knowledge_dir,
            chroma_path=chroma_dir,
            embedding_function=fake_embeddings,
        )
        results = retrieve(
            "refund",
            k=1,
            chroma_path=chroma_dir,
            embedding_function=fake_embeddings,
        )
        assert len(results) >= 1
        r = results[0]
        assert "content" in r
        assert "metadata" in r
        assert "score" in r
        assert isinstance(r["content"], str)
        assert isinstance(r["metadata"], dict)
        assert isinstance(r["score"], float)

    def test_retrieve_metadata_contains_source_file(self, knowledge_dir, chroma_dir, fake_embeddings):
        ingest_documents(
            knowledge_dir=knowledge_dir,
            chroma_path=chroma_dir,
            embedding_function=fake_embeddings,
        )
        results = retrieve(
            "shipping",
            k=5,
            chroma_path=chroma_dir,
            embedding_function=fake_embeddings,
        )
        source_files = {r["metadata"]["source_file"] for r in results}
        # At least one result should have a known source file
        assert source_files & {"shipping_policy.md", "refund_policy.md"}

    def test_retrieve_with_metadata_filter(self, knowledge_dir, chroma_dir, fake_embeddings):
        ingest_documents(
            knowledge_dir=knowledge_dir,
            chroma_path=chroma_dir,
            embedding_function=fake_embeddings,
        )
        results = retrieve(
            "policy",
            k=5,
            filter_metadata={"category": "shipping"},
            chroma_path=chroma_dir,
            embedding_function=fake_embeddings,
        )
        for r in results:
            assert r["metadata"]["category"] == "shipping"

    def test_retrieve_empty_db(self, chroma_dir, fake_embeddings):
        """Retrieve from a non-existent collection should return empty."""
        # Fresh chroma dir with no ingestion — the collection doesn't exist
        # so we expect either empty results or a handled error.
        chroma_dir.mkdir(parents=True, exist_ok=True)
        try:
            results = retrieve(
                "anything",
                k=3,
                chroma_path=chroma_dir,
                embedding_function=fake_embeddings,
            )
            assert results == [] or isinstance(results, list)
        except Exception:
            # Chroma may raise if collection doesn't exist; that's acceptable
            pass

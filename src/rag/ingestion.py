"""Document ingestion pipeline — chunking, embedding, and Chroma storage."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from src.config.settings import get_settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Metadata mapping: filename → {category, agent_type}
# ---------------------------------------------------------------------------

DOCUMENT_METADATA: dict[str, dict[str, str]] = {
    "shipping_policy.md": {"category": "shipping", "agent_type": "shipment"},
    "refund_policy.md": {"category": "refund", "agent_type": "payment"},
    "escalation_criteria.md": {"category": "escalation", "agent_type": "escalation"},
    "communication_guidelines.md": {"category": "communication", "agent_type": "customer"},
    "carrier_slas.md": {"category": "carrier", "agent_type": "shipment"},
    "warehouse_slas.md": {"category": "warehouse", "agent_type": "shipment"},
    "apology_email.md": {"category": "communication", "agent_type": "customer"},
    "refund_confirmation.md": {"category": "refund", "agent_type": "payment"},
}


def ingest_documents(
    knowledge_dir: Path | None = None,
    chroma_path: Path | None = None,
    embedding_function: Any | None = None,
) -> int:
    """Ingest markdown documents into a Chroma vector store.

    Parameters
    ----------
    knowledge_dir:
        Directory containing ``.md`` policy documents.
        Defaults to ``settings.KNOWLEDGE_BASE_DIR``.
    chroma_path:
        Persist directory for Chroma.
        Defaults to ``settings.CHROMA_DB_PATH``.
    embedding_function:
        Optional override for the embedding function (useful for testing).
        Defaults to ``OpenAIEmbeddings(model=settings.OPENAI_EMBEDDING_MODEL)``.

    Returns
    -------
    int — number of chunks ingested.
    """
    from langchain_text_splitters import RecursiveCharacterTextSplitter
    from langchain_core.documents import Document

    settings = get_settings()
    kb_dir = Path(knowledge_dir or settings.KNOWLEDGE_BASE_DIR)
    persist_dir = Path(chroma_path or settings.CHROMA_DB_PATH)
    persist_dir.mkdir(parents=True, exist_ok=True)

    # Build embedding function
    if embedding_function is None:
        from langchain_openai import OpenAIEmbeddings

        embedding_function = OpenAIEmbeddings(model=settings.OPENAI_EMBEDDING_MODEL)

    # Load and chunk documents
    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    all_docs: list[Document] = []

    for md_file in sorted(kb_dir.glob("*.md")):
        text = md_file.read_text(encoding="utf-8")
        meta = DOCUMENT_METADATA.get(md_file.name, {"category": "general", "agent_type": "general"})
        chunks = splitter.split_text(text)
        for chunk in chunks:
            all_docs.append(
                Document(
                    page_content=chunk,
                    metadata={
                        "source_file": md_file.name,
                        "category": meta["category"],
                        "agent_type": meta["agent_type"],
                    },
                )
            )

    if not all_docs:
        logger.warning("No documents found in %s", kb_dir)
        return 0

    # Delete existing collection for idempotency, then create fresh
    import chromadb

    client = chromadb.PersistentClient(path=str(persist_dir))
    try:
        client.delete_collection("knowledge_base")
    except Exception:
        pass  # Collection doesn't exist yet

    from langchain_chroma import Chroma

    Chroma.from_documents(
        documents=all_docs,
        embedding=embedding_function,
        collection_name="knowledge_base",
        persist_directory=str(persist_dir),
    )

    logger.info("Ingested %d chunks from %s into %s", len(all_docs), kb_dir, persist_dir)
    return len(all_docs)

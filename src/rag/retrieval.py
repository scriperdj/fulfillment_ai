"""Similarity search over the Chroma knowledge base."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from src.config.settings import get_settings

logger = logging.getLogger(__name__)


def retrieve(
    query: str,
    *,
    k: int = 5,
    filter_metadata: dict[str, str] | None = None,
    chroma_path: Path | None = None,
    embedding_function: Any | None = None,
) -> list[dict[str, Any]]:
    """Search the knowledge base for documents similar to *query*.

    Parameters
    ----------
    query:
        The search query string.
    k:
        Number of results to return.
    filter_metadata:
        Optional Chroma ``where`` filter, e.g. ``{"agent_type": "shipment"}``.
    chroma_path:
        Persist directory for Chroma. Defaults to ``settings.CHROMA_DB_PATH``.
    embedding_function:
        Optional override for the embedding function (useful for testing).

    Returns
    -------
    list of dicts, each with ``content``, ``metadata``, and ``score`` keys.
    """
    from langchain_chroma import Chroma

    settings = get_settings()
    persist_dir = str(chroma_path or settings.CHROMA_DB_PATH)

    if embedding_function is None:
        from langchain_openai import OpenAIEmbeddings

        embedding_function = OpenAIEmbeddings(model=settings.OPENAI_EMBEDDING_MODEL)

    store = Chroma(
        collection_name="knowledge_base",
        persist_directory=persist_dir,
        embedding_function=embedding_function,
    )

    kwargs: dict[str, Any] = {"k": k}
    if filter_metadata:
        kwargs["filter"] = filter_metadata

    results = store.similarity_search_with_relevance_scores(query, **kwargs)

    return [
        {
            "content": doc.page_content,
            "metadata": doc.metadata,
            "score": float(score),
        }
        for doc, score in results
    ]

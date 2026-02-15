"""Knowledge base endpoints — ingest and search."""

from __future__ import annotations

import logging

from fastapi import APIRouter

from src.api.schemas import (
    KnowledgeIngestResponse,
    KnowledgeSearchRequest,
    KnowledgeSearchResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/knowledge", tags=["knowledge"])


@router.post("/ingest", response_model=KnowledgeIngestResponse)
def ingest_knowledge():
    from src.rag.ingestion import ingest_documents

    count = ingest_documents()
    return KnowledgeIngestResponse(chunks_ingested=count)


@router.post("/search", response_model=KnowledgeSearchResponse)
def search_knowledge(request: KnowledgeSearchRequest):
    from src.rag.retrieval import retrieve

    results = retrieve(
        request.query,
        k=request.k,
        filter_metadata=request.filter_metadata,
    )
    return KnowledgeSearchResponse(results=results)

"""FastAPI dependency injection helpers."""

from __future__ import annotations

from collections.abc import Generator

from sqlalchemy.orm import Session


def get_db() -> Generator[Session, None, None]:
    """Yield a sync DB session.

    This is the default implementation that uses the real database.
    Override this dependency in tests with an in-memory SQLite session.
    """
    from src.db.session import get_sync_session

    with get_sync_session() as session:
        yield session

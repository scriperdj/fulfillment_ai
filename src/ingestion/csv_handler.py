"""CSV upload handler — saves file and creates a BatchJob record."""

from __future__ import annotations

import shutil
import uuid
from pathlib import Path
from typing import IO, Union

import pandas as pd
from sqlalchemy.orm import Session

from src.config.settings import get_settings
from src.db.models import BatchJob


def upload_csv(
    file: Union[str, Path, IO[bytes]],
    *,
    session: Session,
    upload_dir: Path | None = None,
) -> BatchJob:
    """Accept a CSV file (path or file-like), persist it, and create a BatchJob.

    Parameters
    ----------
    file:
        A file path (str/Path) or a file-like object (e.g. ``UploadFile.file``).
    session:
        A SQLAlchemy sync session for DB writes.
    upload_dir:
        Override the upload directory (defaults to ``settings.UPLOAD_DIR``).

    Returns
    -------
    BatchJob
        The newly created ``BatchJob`` instance (already flushed so ``id`` is set).
    """
    settings = get_settings()
    dest_dir = upload_dir or settings.UPLOAD_DIR
    dest_dir = Path(dest_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)

    batch_job_id = uuid.uuid4()
    dest_path = dest_dir / f"{batch_job_id}.csv"

    # Save the file
    if isinstance(file, (str, Path)):
        src = Path(file)
        shutil.copy2(src, dest_path)
    else:
        # file-like object
        with open(dest_path, "wb") as out:
            content = file.read()
            if isinstance(content, str):
                content = content.encode("utf-8")
            out.write(content)

    # Count rows (header excluded)
    df = pd.read_csv(dest_path)
    row_count = len(df)

    # Create BatchJob record
    job = BatchJob(
        id=batch_job_id,
        filename=dest_path.name,
        status="processing",
        row_count=row_count,
    )
    session.add(job)
    session.flush()

    return job

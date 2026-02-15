"""Model loading utilities — load trained artifacts with caching."""

from __future__ import annotations

import json
import logging
from functools import lru_cache
from pathlib import Path
from typing import Any

import joblib

from src.config.settings import get_settings

logger = logging.getLogger(__name__)


@lru_cache()
def load_model(path: str | None = None) -> Any:
    """Load the trained delay classifier from a joblib file.

    Parameters
    ----------
    path:
        Explicit path to the classifier file.
        Defaults to ``settings.MODEL_PATH / settings.MODEL_CLASSIFIER_FILE``.

    Returns
    -------
    A fitted classifier with ``predict_proba`` method.

    Raises
    ------
    FileNotFoundError
        If the model file does not exist.
    """
    if path is None:
        settings = get_settings()
        model_path = settings.MODEL_PATH / settings.MODEL_CLASSIFIER_FILE
    else:
        model_path = Path(path)

    if not model_path.exists():
        raise FileNotFoundError(f"Model file not found: {model_path}")

    model = joblib.load(model_path)
    logger.info("Loaded classifier from %s", model_path)
    return model


@lru_cache()
def load_preprocessor(path: str | None = None) -> Any:
    """Load the trained preprocessing pipeline from a joblib file.

    Parameters
    ----------
    path:
        Explicit path to the preprocessor file.
        Defaults to ``settings.MODEL_PATH / settings.MODEL_PREPROCESSOR_FILE``.

    Returns
    -------
    A fitted transformer with ``transform`` method.

    Raises
    ------
    FileNotFoundError
        If the preprocessor file does not exist.
    """
    if path is None:
        settings = get_settings()
        preprocessor_path = settings.MODEL_PATH / settings.MODEL_PREPROCESSOR_FILE
    else:
        preprocessor_path = Path(path)

    if not preprocessor_path.exists():
        raise FileNotFoundError(f"Preprocessor file not found: {preprocessor_path}")

    preprocessor = joblib.load(preprocessor_path)
    logger.info("Loaded preprocessor from %s", preprocessor_path)
    return preprocessor


@lru_cache()
def load_metadata(path: str | None = None) -> dict[str, Any]:
    """Load model metadata from a JSON file.

    Parameters
    ----------
    path:
        Explicit path to the metadata JSON.
        Defaults to ``settings.MODEL_PATH / settings.MODEL_METADATA_FILE``.

    Returns
    -------
    dict with model metadata (feature_names, metrics, etc.).

    Raises
    ------
    FileNotFoundError
        If the metadata file does not exist.
    """
    if path is None:
        settings = get_settings()
        meta_path = settings.MODEL_PATH / settings.MODEL_METADATA_FILE
    else:
        meta_path = Path(path)

    if not meta_path.exists():
        raise FileNotFoundError(f"Metadata file not found: {meta_path}")

    with open(meta_path, encoding="utf-8") as f:
        metadata = json.load(f)

    logger.info("Loaded metadata from %s", meta_path)
    return metadata

"""Centralized configuration loading from environment variables and .env files."""

from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables and .env file.

    Environment variables take precedence over .env file values.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/fulfillment_ai"
    DATABASE_URL_SYNC: str = "postgresql+psycopg2://postgres:postgres@localhost:5432/fulfillment_ai"

    # Kafka
    KAFKA_BROKER: str = "localhost:9092"

    # AI / LLM
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o-mini"
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"

    # ML Model
    MODEL_PATH: Path = Path("models/")
    MODEL_CLASSIFIER_FILE: str = "delay_classifier.joblib"
    MODEL_PREPROCESSOR_FILE: str = "preprocessor.joblib"
    MODEL_METADATA_FILE: str = "model_metadata.json"

    # Severity thresholds
    SEVERITY_CRITICAL_THRESHOLD: float = 0.7
    SEVERITY_WARNING_THRESHOLD: float = 0.5
    SEVERITY_INFO_THRESHOLD: float = 0.3

    # Data paths
    UPLOAD_DIR: Path = Path("data/uploads/")
    CHROMA_DB_PATH: Path = Path("data/chroma_db/")
    KNOWLEDGE_BASE_DIR: Path = Path("knowledge_base/")
    RAW_DATA_DIR: Path = Path("data/raw/")

    # API
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    DEBUG: bool = False
    ENVIRONMENT: str = "development"

    # Logging
    LOG_LEVEL: str = "INFO"

    # KPI
    KPI_ROLLING_WINDOW_DAYS: int = 30
    FULFILLMENT_GAP_THRESHOLD: Optional[float] = None

    @model_validator(mode="after")
    def _set_fulfillment_gap_default(self) -> "Settings":
        if self.FULFILLMENT_GAP_THRESHOLD is None:
            self.FULFILLMENT_GAP_THRESHOLD = self.SEVERITY_WARNING_THRESHOLD
        return self


@lru_cache()
def get_settings() -> Settings:
    """Return a cached Settings instance (singleton)."""
    return Settings()

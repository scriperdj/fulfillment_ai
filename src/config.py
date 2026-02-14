"""
Configuration module for fulfillment_ai
Loads environment variables and provides config objects
"""

from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings from environment variables"""

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    debug: bool = False

    # OpenAI
    openai_api_key: str
    openai_model: str = "gpt-4-turbo-preview"
    openai_temperature: float = 0.7

    # Data
    data_path: str = "./data/raw"
    processed_data_path: str = "./data/processed"
    cache_ttl: int = 3600

    # Agent
    agent_timeout: int = 30
    agent_max_tokens: int = 2000

    # Logging
    log_level: str = "INFO"
    log_format: str = "json"

    # Database (optional)
    database_url: Optional[str] = None

    # Environment
    environment: str = "development"

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()

from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_name: str = "Chatter Copilot"
    app_version: str = "0.1.0"
    debug: bool = False

    # API Keys
    anthropic_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None
    google_cloud_vision_key: Optional[str] = None

    # Database
    database_url: str = "postgresql+asyncpg://localhost:5432/chatter_copilot"

    # Vector Database
    chroma_persist_directory: str = "./data/knowledge_base/chroma"

    # OCR Settings
    ocr_batch_size: int = 50
    ocr_rate_limit_per_minute: int = 1800  # Google Cloud Vision limit

    # CORS
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:5173"]

    # Paths
    handbook_path: str = "./Chatter Marines Field Handbook"
    ocr_output_path: str = "./data/ocr_output"
    parsed_conversations_path: str = "./data/parsed_conversations"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()

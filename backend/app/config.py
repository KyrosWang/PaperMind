from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=False)

    environment: Literal["development", "test", "production"] = "development"
    app_name: str = "PaperMind"
    api_prefix: str = "/api"
    app_api_key: str = "change-me"
    frontend_origin: str = "http://localhost:3000"

    database_url: str = "postgresql+psycopg://papermind:papermind@localhost:5432/papermind"
    redis_url: str = "redis://localhost:6379/0"
    data_root: Path = Path("./data")
    max_upload_mb: int = Field(default=100, ge=1, le=2_000)

    grobid_url: str = "http://localhost:8070"
    grobid_timeout_seconds: int = 180
    chunk_target_tokens: int = Field(default=500, ge=100)
    chunk_overlap_tokens: int = Field(default=60, ge=0)

    zotero_api_key: str | None = None
    zotero_user_id: str | None = None
    zotero_library_type: Literal["user", "group"] = "user"

    llm_provider: str = "openai"
    embedding_provider: str = "openai"
    openai_api_key: str | None = None
    openai_model: str = "gpt-4.1-mini"
    openai_embedding_model: str = "text-embedding-3-small"
    embedding_dimension: int = Field(default=1536, ge=1)

    @field_validator("data_root", mode="before")
    @classmethod
    def expand_data_root(cls, value: str | Path) -> Path:
        return Path(value).expanduser()

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    return Settings()

"""Configuration helpers for the finance agent."""

from functools import lru_cache
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Environment-driven configuration for the agent runtime."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    model_name: str = Field(
        default="openai/gpt-4.1-mini",
        description="Fully qualified model identifier understood by OpenRouter.",
    )
    openrouter_api_key: str = Field(
        min_length=10,
        description="API key used to authenticate with OpenRouter.",
        validation_alias="OPENROUTER_API_KEY",
        alias="OPENROUTER_API_KEY",
        env="OPENROUTER_API_KEY",
    )
    temperature: float = Field(default=0.5, ge=0.0, le=2.0)
    max_output_tokens: Optional[int] = Field(
        default=None,
        description="Optional token cap passed to the model; mirrors OpenAI-like semantics.",
    )


@lru_cache(maxsize=1)
def load_settings() -> Settings:
    """Load settings once per process."""

    return Settings()

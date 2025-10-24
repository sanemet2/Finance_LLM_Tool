"""Environment and configuration helpers for the OpenRouter chat package."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

# Project and tool locations are fixed relative to this module.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
TOOLS_ROOT = PROJECT_ROOT / "agent_tools"
ENV_FILE = PROJECT_ROOT / ".env"

DEFAULT_MODEL = "openai/gpt-5"
DEFAULT_BASE_URL = "https://openrouter.ai/api/v1/chat/completions"


@dataclass(frozen=True)
class ProjectPaths:
    """Convenience container for commonly accessed project locations."""

    project_root: Path
    tools_root: Path
    env_file: Path


def resolve_project_paths() -> ProjectPaths:
    """Return the static project paths used throughout the package."""

    return ProjectPaths(
        project_root=PROJECT_ROOT,
        tools_root=TOOLS_ROOT,
        env_file=ENV_FILE,
    )


def load_local_env(env_path: Optional[Path] = None) -> None:
    """Populate os.environ with values from a local .env file if present."""

    path = env_path or ENV_FILE
    if not path.exists():
        return

    try:
        for raw_line in path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            if not key or key in os.environ:
                continue
            os.environ[key] = value.strip().strip('"').strip("'")
    except OSError as exc:
        print(f"Warning: failed to read .env file ({exc}).")


def require_openrouter_api_key() -> str:
    """Return the configured OpenRouter API key or exit if missing."""

    key = os.getenv("OPENROUTER_API_KEY")
    if not key:
        raise SystemExit("OPENROUTER_API_KEY environment variable is required.")
    return key


def optional_openrouter_metadata() -> dict[str, str]:
    """Collect optional OpenRouter header metadata values from the environment."""

    headers: dict[str, str] = {}
    org = os.getenv("OPENROUTER_ORG")
    if org:
        headers["X-OpenRouter-Org"] = org
    site_url = os.getenv("OPENROUTER_SITE_URL")
    if site_url:
        headers["HTTP-Referer"] = site_url
    app_name = os.getenv("OPENROUTER_APP_NAME")
    if app_name:
        headers["X-Title"] = app_name
    return headers

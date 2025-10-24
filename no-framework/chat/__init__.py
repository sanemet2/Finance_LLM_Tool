"""Public package API for the OpenRouter chat client."""

from __future__ import annotations

from .conversation import chat_once, interactive_loop, run_single_prompt
from .environment import load_local_env, resolve_project_paths
from .cli import main

# Load .env values on import for compatibility with the original script behaviour.
load_local_env()

__all__ = [
    "chat_once",
    "interactive_loop",
    "run_single_prompt",
    "main",
    "load_local_env",
    "resolve_project_paths",
]

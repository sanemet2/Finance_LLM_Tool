# Repository Guidelines

## Project Structure & Module Organization
- `finance_agent/` is the main package. Core orchestration lives in `agent.py`, CLI entrypoints in `cli.py`, and runtime configuration in `config.py`.
- Tooling logic is grouped in `services/` (market data loaders) and `tools.py` (agent tool registration).
- The FastAPI chat UI is under `finance_agent/web_app/` with `app.py` for the backend and `index.html` for the client.
- Project metadata and dependency pins are defined in `pyproject.toml`; environment secrets belong in `.env`.

## Build, Test, and Development Commands
- `uv sync` (or `pip install -e .[dev]`) installs runtime and dev dependencies from `pyproject.toml`.
- `python -m finance_agent.cli "prompt"` runs the agent once via the CLI.
- `python -m uvicorn finance_agent.web_app.app:app --reload` launches the streaming UI on http://127.0.0.1:8000.
- `uv run ruff check` and `uv run ruff format` lint and format the codebase (swap `uv run` for `python -m` if not using uv).

## Coding Style & Naming Conventions
- Target Python 3.10+ with 4-space indentation, type annotations, and descriptive snake_case names.
- Keep modules focused; prefer private helpers over large functions. Group related services and tools by domain.
- Run `ruff` before committing. Align docstrings and error messages with the professional tone used in `README.md`.

## Testing Guidelines
- Tests should reside in a top-level `tests/` package that mirrors the runtime layout (e.g., `tests/web_app/test_app.py`).
- Use `pytest` with `pytest-asyncio` for coroutine coverage. Run via `uv run pytest`.
- Aim to cover new tools, settings, and HTTP endpoints with unit or integration tests; include regression cases for finance data parsing.

## Commit & Pull Request Guidelines
- Write concise, present-tense commit messages (`fix: handle empty SSE payload`, `docs: clarify API key setup`).
- Each PR should state the problem, the approach, and manual/automated verification. Link issues or discussions when available.
- Capture UI-affecting changes with screenshots or GIFs, and mention required env vars when they differ from defaults.

## Environment & Security Tips
- Copy `.env.example` to `.env` and provide `OPENROUTER_API_KEY` before running the agent.
- Never commit secrets or personal market data. Validate external inputs in tools and surface safe error messages to the UI.

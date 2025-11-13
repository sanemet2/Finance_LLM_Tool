# Repository Guidelines

## Project Structure & Module Organization
The root contains two active workspaces. The `agent/` directory houses the finance-focused assistant (`agent.py` plus prompt assets such as `Pydantic Core Concepts.md`) and is the right place for custom orchestration code. The upstream framework lives in `pydantic-ai/`, which follows the official Pydantic AI layout: runtime packages in `pydantic_ai*/`, documentation and examples under `docs/` and `examples/`, and the canonical regression suite in `tests/`. Keep personal scratch files out of these tracked paths; if you need environment tweaks, place them in `agent/.env` or ignore them via `.gitignore`.

## Agent Authoring Workflow
- Treat `agent/Pydantic Core Concepts.md` as the quick-reference playbook when evolving agents; cite the relevant numbered subsection (e.g., `Core Concepts section 1.III`) inside code comments or review notes when you rely on it.
- When the outline lacks enough detail, consult the upstream docs in `pydantic-ai/docs` (start with `docs/agents.md`, `docs/tools.md`, `docs/output.md`, and `docs/dependencies.md`) and reference the exact path or section you used so Codex can fetch the full context later.
- Feed new findings back into the Core Concepts file before relying on them in new code so the guide remains authoritative.
- Core Concepts formatting legend (powers the visualization colors): keep the hierarchy `# <n>. Title` (level 1), `  *I. Section*` (level 2, italic Roman numerals), `    A. Detail` (level 3, capital letters), and `      **i. Note**` (level 4, bold lowercase Roman numerals) with the same leading spaces and punctuation, and document any new depth before using different symbols.


## Build, Test, and Development Commands
- `cd pydantic-ai && make install` – syncs dependencies with `uv`, installs editable extras, and registers pre-commit hooks; run once per machine.
- `cd pydantic-ai && make format` / `make lint` – wraps `uv run ruff format` and `ruff check` to enforce style.
- `cd pydantic-ai && make test` – executes the full pytest suite with coverage and parallelization.
- `cd agent && python agent.py` – runs the finance agent against OpenRouter; ensure `OPENROUTER_API_KEY` and `OPENROUTER_MODEL` (optional) are exported or stored in `.env`.

## Coding Style & Naming Conventions
We inherit the Ruff configuration from `pyproject.toml`: 120-character lines, single quotes for inline strings, Google-style docstrings where required, and strict type annotations (Pyright runs in `strict` mode). Prefer descriptive module names (`agent_config.py`, not `misc.py`) and PascalCase for dataclasses. Imports should group stdlib / third-party / first-party, which `ruff format` and `ruff check --fix` can enforce. Avoid ad-hoc formatting; always run the Makefile targets before committing.
- When adding new lines of code, append an ASCII arrow comment like `# <-- new code` so reviewers can immediately spot fresh additions; keep these markers unless explicitly told to remove them.

## Testing Guidelines
`pytest` lives in `pydantic-ai/tests` with node IDs mirroring package paths (e.g., `tests/agents/test_streaming.py`). Add new tests beside the code they cover and name files `test_<feature>.py`. Use parametrized cases over ad-hoc loops, and keep fixtures reusable. Coverage is collected automatically via `make test`; aim to keep deltas green before opening a PR. Agent-specific smoke tests can live in `agent/tests/` if they rely on custom prompts—mark them with `@pytest.mark.external` when they hit live providers.

## Commit & Pull Request Guidelines
History favors short, imperative messages (e.g., “Add RunContext helper”); follow that style and group related changes into a single commit. Every PR should describe the motivation, testing performed (`make test`, manual agent run, etc.), and reference any relevant issues. Include screenshots or terminal snippets when the change affects docs or UX, and call out secrets/config expectations so reviewers can reproduce results.

## Security & Configuration Tips
Never hard-code API keys. Use `.env` entries (`OPENROUTER_API_KEY`, `OPENROUTER_MODEL`) and document any new secrets in the PR body. When editing the upstream `pydantic-ai` package, prefer feature flags or dependency injection over global state so multi-tenant deployments remain safe.

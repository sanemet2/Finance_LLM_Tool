# Repository Guidelines

## Project Structure & Module Organization
- `agent_tools/` bundles modular tools usable by LLM agents. Each tool ships with its own `AGENTS.md`, `tool_code/`, `tool_outputs/`, and supporting assets.
- `agent_tools/Retrieve Financial Data/` currently implements market-data retrieval via yfinance. Start with that tool's `AGENTS.md` to understand specifics.
- `diagnostics/` hosts the shared timing tracer (`TraceRecorder`) used across the orchestrator and tools; surface timings with runtime flags instead of reimplementing instrumentation.
- `chat/` contains the refactored OpenRouter orchestrator split into focused modules; review `chat/AGENTS.md` for an architectural map before editing.
- Tool-specific API references (e.g., `yfinance_specs.md`) live under each tool's `API_specs/` directory and should be updated alongside code changes.
- `Where We Are At.txt` captures repo-wide milestones; append concise bullets after meaningful changes.
- Plan future tests under `tests/` mirroring tool names, with large payloads saved under `tests/fixtures/` as required.
- `app.py` is the entry script for launching the chat client; it delegates into the `chat` package.
- Secrets belong in `.env` (ignored via `.gitignore`); copy `.env.example` and fill in `OPENROUTER_API_KEY` plus optional metadata.

## Status Log
<!-- STATUS-LOG START -->
- Reorganized agent tooling into per-tool directories under `agent_tools/`, starting with `Retrieve Financial Data/`.
- Introduced tool-local outputs and guides so agents consult `agent_tools/<tool>/AGENTS.md` before running commands.
- Next: add regression tests covering price history CLI parsing and JSON payload schemas.
<!-- STATUS-LOG END -->

## Build, Test, and Development Commands
- Run `cd no-framework` (or prefix the paths below) before executing commands; all legacy tooling now lives inside this subdirectory.
- `python "agent_tools/Retrieve Financial Data/tool_code/yfinance_service.py" --operation list_operations` lists supported operations and validates imports.
- `python "agent_tools/Retrieve Financial Data/tool_code/price_history_cli.py" --ticker COST --period 2y --interval 1d --output-json "agent_tools/Retrieve Financial Data/tool_outputs/cost.json"` fetches daily history and stores the full response.
- `python "agent_tools/Retrieve Financial Data/tool_code/price_history_cli.py" --ticker COST --period 2y --compact` prints only summary metadata (start/end/row count) to stdout.
- `python app.py` launches the terminal chat orchestrator (requires `OPENROUTER_API_KEY` in your local `.env`; use `--prompt` for one-shot queries).
- `python app.py --prompt "Pull today's S&P 500 close." --trace --verbose` runs a single-shot query while printing the timing report from `diagnostics/TraceRecorder`.
- `python app.py --prompt "Pull today's S&P 500 close." --live-stream --verbose` streams tokens to the terminal while still buffering transcripts; omit `--live-stream` for the default single-print behaviour.
- `python -m chat.ui.simple_textual` opens the Textual-based desktop sandbox with separate panes for chat, tool output, and diagnostics; streaming and tracing map to the on-screen checkboxes.
- `python -m pytest tests/chat` executes the chat guardrails covering the tool registry + transcript behaviours.
- Install dependencies inside a virtualenv via `python -m pip install yfinance pandas numpy pandas-datareader pytest black ruff textual`.
- Do not modify text between `<!-- STATUS-LOG START -->` and `<!-- STATUS-LOG END -->`; preserve the inline history.

## Coding Style & Naming Conventions
- Target Python 3.10+, four-space indentation, snake_case identifiers, PascalCase for classes, and UPPER_CASE for constants.
- Type-annotate public functions, keep external service calls isolated for testability, and prefer pure helpers.
- Format code with `black` (88 columns) and lint with `ruff`; document intentional deviations inline.

## Testing Guidelines
- Use `pytest`, naming files `test_<module>.py` and functions `test_<behavior>`.
- Mock network calls or rely on fixtures saved under `tests/fixtures/`; avoid live requests in automated suites.
- Cover JSON serialization, error paths, and CLI argument parsing before shipping.

## Commit & Pull Request Guidelines
- Write imperative subjects (<=72 chars) with optional wrapped bodies; reference issues using `Refs #123` or `Fixes #123`.
- PRs should include summary bullets, manual verification notes, updated docs/specs, and sample payloads or screenshots when user-facing.
- Ensure lint and tests pass (or justify exceptions) before requesting review.

## Agent System Prompt
```
You are operating inside a modular LLM tooling workspace.
1. Inspect `agent_tools/` and choose the tool that matches the user's request (e.g., `Retrieve Financial Data/`).
2. Read the selected tool's `AGENTS.md` to learn parameters, commands, and output expectations.
3. Run commands from the repository root, targeting the tool's `tool_code/` and writing artifacts into its `tool_outputs/` directory.
4. Request escalated permissions before any network use and summarize results with start/end dates plus relevant counts.
```
- Default to compact output unless the user asks for full rows or a file artifact.
- Respect sandbox constraints; cache results in tool-specific `tool_outputs/` directories when repeated calls are required.
- Never edit the `STATUS-LOG` block; treat it as read-only project history.



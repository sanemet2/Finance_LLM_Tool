# Retrieve Financial Data Guidelines

## Folder Layout
- `API_specs/` stores canonical yfinance documentation (`yfinance_specs.md`). Update it before exposing new endpoints.
- `tool_code/` contains executable assets: `yfinance_service.py`, `price_history_cli.py`, `openrouter_tools.py`, and `price_history_request.jsonc`.
- `tool_outputs/` holds generated payloads (e.g., `cost_history.json`, `cost_history_compact.json`). Prune artifacts when no longer required and keep filenames descriptive.

## Usage Workflow
- Always run commands from the tool root: `python tool_code/price_history_cli.py --ticker COST --period 2y --interval 1d --output-json tool_outputs/cost.json`.
- Prefer `--compact` for quick summaries and `--output-json` when downstream processing is needed.
- To call the core service directly, provide a JSON request: `python tool_code/yfinance_service.py --input-json payload.json`.
- Do not modify text between `<!-- STATUS-LOG START -->` and `<!-- STATUS-LOG END -->`; it records the latest milestones for this tool.

## OpenRouter Tool Calling
- Import `tool_code/openrouter_tools.py` to expose the service to OpenRouter's built-in function-calling interface.
- `get_tool_definitions()` returns the JSON schema needed for the `tools` parameter.
- `execute_tool_call(tool_name, arguments)` runs the corresponding `YFinanceService` method and produces a `{"ok": ..., "result": ...}` payload ready for a `tool` message.
- The helper CLI supports local smoke tests: `python tool_code/openrouter_tools.py --list-tools` or `--call download_price_history --arguments '{"tickers": "COST"}'`.
- For full chat orchestration, run the repository entry script `python app.py` (or `python -m chat`) after setting OpenRouter API credentials (interactive terminal UI; requires network access).

## Coding & Data Standards
- Python 3.10+, four-space indentation, snake_case identifiers, PascalCase classes, and UPPER_CASE constants.
- Keep external I/O (network, filesystem) inside thin wrappers so agents can stub or replay easily.
- Sanitize pandas/numpy objects into JSON primitives before writing to `tool_outputs/`.

## Testing & Validation
- Place tests under `tests/retrieve_financial_data/` (create when needed) and use `pytest` with fixtures that avoid live network calls.
- Validate new parameters locally, then capture representative outputs in `tool_outputs/` for documentation.

## Status Log
<!-- STATUS-LOG START -->
- Initial structure established with dedicated folders for specs, code, and outputs.
- COST two-year history fetched via `price_history_cli.py` to demonstrate both compact and full responses.
- Next: add pytest coverage for CLI argument parsing and JSON schema validation.
<!-- STATUS-LOG END -->

## Agent Prompt Snippet
```
You are inside Retrieve Financial Data.
Run `python tool_code/price_history_cli.py --ticker <SYMBOL> --period <RANGE> --interval <CADENCE> [--compact|--output-json tool_outputs/<FILE>]`.
Use `tool_code/price_history_request.jsonc` when you must craft raw payloads for `tool_code/yfinance_service.py`.
Request escalated permissions before hitting the network and report start/end dates plus row counts.
```
- Respect sandbox limits and cache repeatable outputs in `tool_outputs/`.
- Never edit the `STATUS-LOG` block; treat it as read-only history for this tool.

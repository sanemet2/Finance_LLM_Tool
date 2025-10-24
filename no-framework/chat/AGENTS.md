# Chat Package Guidelines

## Folder Layout
- `environment.py` centralises project paths, `.env` loading, and OpenRouter defaults (`DEFAULT_MODEL`, `DEFAULT_BASE_URL`, header metadata helpers).
- `tool_registry.py` lazily discovers `agent_tools/*/tool_code/openrouter_tools.py` modules and exposes a `ToolRegistry` for fetching tool schemas and executing calls.
- `http_client.py` owns OpenRouter streaming I/O: request payload construction, SSE parsing, and timing metadata collection.
- `transcript.py` provides the `Transcript` helper that manages chat history, tool-call insertion, and assistant content normalisation.
- `conversation.py` implements the high-level chat loops (`chat_once`, `run_single_prompt`, `interactive_loop`) that orchestrate completions, tool calls, and tracing.
- `cli.py` parses CLI arguments, wires dependencies, and terminates with meaningful exit codes.
- `ui/` hosts optional presentation layers; `simple_textual.py` renders a Textual-based desktop chat shell with distinct panes for assistant replies, tool output, and diagnostics.
- `__init__.py` re-exports the primary helpers and triggers `.env` loading so legacy imports keep functioning.
- `__main__.py` allows `python -m chat` to invoke the CLI without touching `app.py`.

## Usage Workflow
- Commands below assume you've changed into `no-framework/` (`cd no-framework`) before running them.
- Launch the chat client from this directory via `python app.py` (interactive) or `python app.py --prompt "<question>"` for one-shot replies.
- You can run the package directly with `python -m chat --prompt "<question>" --trace --verbose`; flags mirror those on `app.py`.
- `python -m chat.ui.simple_textual` opens the Textual desktop sandbox; toggle "Stream tokens" and "Trace timings" to mirror the CLI `--live-stream` / `--trace` flags while monitoring tool output separately.
- Set `OPENROUTER_API_KEY` (and optional metadata headers) in `.env` before invoking the CLI; `environment.load_local_env()` handles loading on import.
- Keep new tools under `agent_tools/*/tool_code/openrouter_tools.py`; the registry auto-discovers them at runtime--no manual imports required.

## Diagnostics & Tracing
- Pass `--trace` to surface per-segment timings captured by `diagnostics.TraceRecorder`; adjust bar width with `--trace-width`, or rely on the Textual UI diagnostics pane.
- `--verbose` echoes tool outputs as they are appended to the transcript; combine with `--live-stream` to print tokens as they arrive, or rely on the UI's tool pane (internally wired via `tool_result_handler`).
- The HTTP client records request payload size, TTFB, and response bytes automatically when tracing is enabled.

## Status Log
<!-- STATUS-LOG START -->
- Chat orchestrator split into modular package under `chat/` with documented entrypoints and helpers.
<!-- STATUS-LOG END -->

## Agent Prompt Snippet
```
You are operating inside the chat orchestrator package.
1. Import helpers from `chat` instead of the legacy `openrouter_chat.py` script.
2. Run `python app.py [--prompt "..."] [--trace] [--live-stream] [--verbose]` from the repository root after setting `OPENROUTER_API_KEY` in `.env`.
3. When editing behaviour, update the corresponding module (`environment`, `tool_registry`, `http_client`, `transcript`, or `conversation`) and keep this guide in sync.
```
- Respect sandbox limits when invoking external APIs; request elevated permissions when required.
- Never edit the `STATUS-LOG` block; treat it as read-only history for this package.

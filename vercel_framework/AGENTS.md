# Vercel Framework Guide

This folder hosts the Vercel AI SDK flavor of the finance assistant. The code talks to OpenRouter for completions and reuses the existing Python yfinance tools for data retrieval.

## Directory Layout
- `src/config/constants.ts` - model name, base URL, and timeout settings.
- `src/config/paths.ts` - resolves the local `./python` path so Node can reach the bundled Python script.
- `src/tools/pythonBridge.ts` - spawns `yfinance_service.py`, streams stdout/stderr, and enforces timeouts.
- `src/tools/yfinance.ts` - Zod schemas plus helpers that call the bridge and post-process responses.
- `src/agent/financeAgent.ts` - orchestrates the chat loop and dispatches tool calls.
- `src/agent/chatTypes.ts`, `systemPrompt.ts`, `tooling.ts`, `requestCompletion.ts`, `openRouterUtils.ts`, `schemaUtils.ts` - supporting modules for shared types, system instructions, tool metadata/executors, OpenRouter calls, and utility helpers.
- `src/scripts/askQuestion.ts` - simple CLI wrapper (`npm run ask -- "prompt"`).
- `docs/` - usage cheat sheet (`usage.md`) and integration plan (`integration-plan.md`).
- `.env` - must contain `OPENROUTER_API_KEY=...` for the agent to authenticate.
## Runtime Flow
1. CLI invokes `generateFinanceAnswer(prompt)`.
2. We send `{system, user}` messages to OpenRouter (model `openai/gpt-4.1-mini`).
3. If the model emits `tool_calls`, the executor runs the matching Python helper and appends the tool result to the chat history.
4. Repeat until the model responds without requesting another tool; return that text.

## Tool Mapping
- `download_price_history` – Python `download_price_history` (supports ticker, period, interval, start/end, etc.; prefer supplying explicit `start`/`end` ISO dates for precise spans).
- `get_ticker_fast_info` – Python `get_ticker_fast_info`.
- `get_ticker_summary` – Python `get_ticker_summary`.
- `get_ticker_news` – Python `get_ticker_news`.
- `get_ticker_fundamentals` – Python `get_ticker_fundamentals`.

Each tool call returns the original `{ok,result|error}` envelope so the agent can surface errors or data verbatim.

## Useful Commands
```powershell
cd "C:\Users\franc\OneDrive\Desktop\Programming\Finance LLM Tool\vercel framework"
npm install             # once, to install deps
npm run smoke:python    # run a direct yfinance call without LLM
npm run ask -- "Prompt" # query the agent (requires .env with OPENROUTER_API_KEY)
```

## Notes
- Python must be available on PATH with the dependencies required by the bundled script (`python/yfinance_service.py`).
- Each tool call logs `[tool] name args: â€¦` to the console for easy tracing.
- Adjust the shim in `src/tools/yfinance.ts` if you want different period fallbacks or schema changes.

# Pydantic-AI Finance Agent

Python-first port of the existing Vercel finance agent, implemented with
[pydantic-ai](https://github.com/pydantic/pydantic-ai). The project reuses the proven
yfinance tooling while moving the agent loop, tool registration, and orchestration entirely
into Python.

## Features
- Pydantic-validated tool schemas and typed agent outputs.
- First-class OpenRouter support through `OpenRouterProvider`.
- Direct reuse of `yfinance_service.py` for deterministic market data.
- CLI and web surfaces that mirror the original TypeScript ergonomics.

## Getting Started
1. Install dependencies (adjust for your environment):
   ```bash
   uv sync
   # or
   pip install -e .
   ```
2. Copy `.env.example` to `.env` and supply your OpenRouter key:
   ```bash
   OPENROUTER_API_KEY=sk-...
   ```
3. Run the CLI for a quick prompt:
   ```bash
   python -m finance_agent.cli "Provide a quick market update for AAPL over the last month."
   ```

## Streaming Web UI
Launch a modern streaming chat surface backed by FastAPI:
```bash
uvicorn finance_agent.web_app.app:app --reload
```
Open http://127.0.0.1:8000/ to chat. The UI streams tokens live, keeps conversation history,
and adapts cleanly to both desktop and mobile screens.

## Project Layout
```
finance_agent/
├── __init__.py
├── agent.py          # Agent builder and run helpers
├── cli.py            # Command-line entrypoint
├── config.py         # Environment-backed settings
├── dependencies.py   # Dependency container (yfinance service)
├── prompts.py        # System prompt text
├── services/
│   ├── __init__.py
│   └── yfinance_loader.py
├── tools.py          # Tool registration wrapping yfinance operations
└── web_app/          # Streaming chat UI
    ├── __init__.py
    ├── app.py        # FastAPI backend with SSE streaming
    └── index.html    # Modern chat interface
README.md
pyproject.toml
```

## Next Steps
- Integrate the agent with your preferred runtime (FastAPI routes, Lambda, etc.).
- Add evaluation suites using `pydantic-ai`'s eval tooling for regression tracking.
- Retire the legacy Node.js scaffolding once the Python stack reaches parity.

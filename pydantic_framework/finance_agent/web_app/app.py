"""FastAPI app that serves a streaming chat UI for the finance agent."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any, AsyncIterator

from fastapi import Body, FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse

from ..agent import FinanceAgentRunner, build_agent


def _load_html() -> str:
    template_path = Path(__file__).with_name("index.html")
    return template_path.read_text(encoding="utf-8")


app = FastAPI(title="Finance Agent UI", default_response_class=JSONResponse)
_runner: FinanceAgentRunner | None = None
_index_html = _load_html()
_runner_lock = asyncio.Lock()


async def get_runner() -> FinanceAgentRunner:
    """Lazy-initialize the global runner once."""

    global _runner
    if _runner is None:
        async with _runner_lock:
            if _runner is None:
                _runner = build_agent()
    return _runner


def _sse(event: str, payload: dict[str, Any]) -> str:
    """Encode payload as a single SSE event."""

    return f"event: {event}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"


@app.get("/", response_class=HTMLResponse)
async def index() -> HTMLResponse:
    """Serve the chat UI."""

    return HTMLResponse(content=_index_html)


@app.get("/health")
async def health() -> dict[str, str]:
    """Simple health endpoint."""

    return {"status": "ok"}


@app.post("/api/chat")
async def chat_endpoint(
    request: Request,
    payload: dict[str, Any] = Body(...),
) -> StreamingResponse:
    """Stream assistant responses for a given prompt."""

    prompt = str(payload.get("prompt", "")).strip()
    if not prompt:
        raise HTTPException(status_code=400, detail="Prompt is required.")

    runner = await get_runner()

    async def event_stream() -> AsyncIterator[str]:
        try:
            yield _sse("status", {"message": "started"})
            async with runner.agent.run_stream(prompt, deps=runner.deps) as stream:
                accumulated = ""
                async for delta in stream.stream_text(delta=True, debounce_by=None):
                    accumulated += delta
                    yield _sse("delta", {"text": delta, "full": accumulated})
                output = await stream.get_output()
            final_text = getattr(output, "text", None)
            if final_text is None:
                final_text = accumulated or str(output)
            yield _sse("final", {"text": final_text})
        except asyncio.CancelledError:
            # Client disconnected; stop streaming silently.
            raise
        except Exception as exc:  # pragma: no cover - surface error to UI
            yield _sse("error", {"message": str(exc)})

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )

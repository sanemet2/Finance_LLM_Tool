"""Collection of instrumented tools available to the orchestrator."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from time import perf_counter
from typing import Callable, Final, TypedDict

from ddgs import DDGS
from pydantic import BaseModel
from pydantic_ai.common_tools.duckduckgo import DuckDuckGoSearchTool
from pydantic_ai.tools import Tool

ToolRecorder = Callable[[str, float], None]

_DUCK_TOOL_NAME: Final[str] = 'duckduckgo_search'
_DUCK_TOOL_DESCRIPTION: Final[
    str
] = 'Searches DuckDuckGo for the given query and returns the results.'


def build_toolbox(record_duration: ToolRecorder) -> list[Tool[None]]:
    """Create all orchestrator tools wired with timing instrumentation."""
    return [
        _build_duckduckgo_tool(record_duration),
        _build_python_exec_tool(record_duration),
    ]


def _build_duckduckgo_tool(record_duration: ToolRecorder) -> Tool[None]:
    search_impl = DuckDuckGoSearchTool(client=DDGS(), max_results=None)

    async def timed_duckduckgo_search(query: str):
        start = perf_counter()
        try:
            return await search_impl(query)
        finally:
            record_duration(_DUCK_TOOL_NAME, (perf_counter() - start) * 1_000)

    return Tool(
        timed_duckduckgo_search,
        name=_DUCK_TOOL_NAME,
        description=_DUCK_TOOL_DESCRIPTION,
    )


class PythonExecPayload(BaseModel):
    """Schema for sandboxed python execution requests."""

    code: str
    timeout_ms: int | None = 2000


class PythonExecResult(TypedDict):
    stdout: str
    stderr: str


_PYTHON_TOOL_NAME: Final[str] = 'python_exec'
_PYTHON_TOOL_DESCRIPTION: Final[str] = 'Run short Python snippets in an isolated subprocess.'
_SANDBOX_ENTRYPOINT: Final[Path] = Path(__file__).with_name('run_python_sandbox.py')


def _build_python_exec_tool(record_duration: ToolRecorder) -> Tool[None]:
    def run_python(payload: PythonExecPayload) -> PythonExecResult:
        start = perf_counter()
        try:
            proc = subprocess.run(
                [sys.executable, str(_SANDBOX_ENTRYPOINT)],
                input=payload.code,
                capture_output=True,
                text=True,
                timeout=(payload.timeout_ms or 2000) / 1000,
            )
            return {'stdout': proc.stdout, 'stderr': proc.stderr}
        finally:
            record_duration(_PYTHON_TOOL_NAME, (perf_counter() - start) * 1_000)

    return Tool(
        run_python,
        name=_PYTHON_TOOL_NAME,
        description=_PYTHON_TOOL_DESCRIPTION,
    )

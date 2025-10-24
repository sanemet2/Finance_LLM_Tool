"""Transcript helpers for managing chat messages and tool call results."""

from __future__ import annotations

import json
import sys
from time import perf_counter
from typing import TYPE_CHECKING, Any, Callable, Dict, Iterable, List, Mapping, Optional, Sequence

from diagnostics import TraceRecorder, scoped_recorder

if TYPE_CHECKING:  # pragma: no cover
    from .tool_registry import ToolRegistry


class Transcript:
    """Mutable collection of chat messages passed to the completion API."""

    def __init__(
        self,
        *,
        system_prompt: Optional[str] = None,
        initial_messages: Optional[Sequence[Dict[str, Any]]] = None,
    ) -> None:
        self._messages: List[Dict[str, Any]] = list(initial_messages or [])
        if system_prompt:
            self._messages.insert(0, {"role": "system", "content": system_prompt})

    # Message management --------------------------------------------------------

    def add_user(self, content: str) -> None:
        self._messages.append({"role": "user", "content": content})

    def add_assistant(
        self,
        *,
        content: Any,
        tool_calls: Optional[List[Dict[str, Any]]] = None,
    ) -> None:
        message: Dict[str, Any] = {"role": "assistant", "content": content}
        if tool_calls:
            message["tool_calls"] = tool_calls
        self._messages.append(message)

    def add_tool_result(
        self,
        *,
        name: str,
        call_id: Optional[str],
        content: str,
    ) -> None:
        self._messages.append(
            {
                "role": "tool",
                "name": name,
                "tool_call_id": call_id,
                "content": content,
            }
        )

    def messages(self) -> List[Dict[str, Any]]:
        return list(self._messages)

    def pop_last(self) -> Optional[Dict[str, Any]]:
        return self._messages.pop() if self._messages else None

    # Tool integration ----------------------------------------------------------

    def append_tool_results(
        self,
        tool_calls: List[Dict[str, Any]],
        registry: "ToolRegistry",
        verbose: bool,
        recorder: Optional[TraceRecorder] = None,
        result_handler: Optional[Callable[[Dict[str, Any]], None]] = None,
    ) -> None:
        """Invoke tool calls and append their outputs to the transcript."""

        for index, call in enumerate(tool_calls, start=1):
            name = call["function"]["name"]
            arguments = call["function"].get("arguments") or {}
            if recorder:
                start = perf_counter()
                with scoped_recorder(recorder):
                    result = registry.execute(name, arguments)
                duration = perf_counter() - start
                if isinstance(arguments, str):
                    arguments_chars = len(arguments)
                else:
                    try:
                        arguments_chars = len(json.dumps(arguments))
                    except (TypeError, ValueError):
                        arguments_chars = None
                result_chars = len(result) if isinstance(result, str) else None
                metadata: Dict[str, Any] = {
                    "tool_call_id": call.get("id"),
                    "arguments_chars": arguments_chars,
                    "result_chars": result_chars,
                }
                recorder.add(f"tool:{name}[{index}]", duration, metadata=metadata)
            else:
                result = registry.execute(name, arguments)

            if result_handler:
                result_handler(
                    {
                        "name": name,
                        "call_id": call.get("id"),
                        "arguments": arguments,
                        "result": result,
                    }
                )

            self.add_tool_result(
                name=name,
                call_id=call.get("id"),
                content=result,
            )
            if verbose:
                sys.stdout.write(f"[tool:{name}] {result}\n")


def normalise_content(content: Any) -> str:
    """Convert assorted OpenRouter message formats into plain text."""

    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, Mapping):
        text = content.get("text")
        if isinstance(text, str):
            return text
        if text is not None:
            return normalise_content(text)
        try:
            return json.dumps(content, ensure_ascii=False)
        except (TypeError, ValueError):
            return str(content)
    if isinstance(content, Iterable):
        parts: List[str] = []
        for chunk in content:
            if isinstance(chunk, dict):
                text = chunk.get("text")
                if text:
                    parts.append(str(text))
            else:
                parts.append(str(chunk))
        return "\n".join(filter(None, parts))
    return str(content)

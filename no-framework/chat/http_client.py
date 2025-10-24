"""HTTP helpers for interacting with the OpenRouter streaming API."""

from __future__ import annotations

import json
from time import perf_counter
from typing import Any, Callable, Dict, List, Mapping, Optional, Tuple

import requests
from diagnostics import TraceRecorder

from .environment import optional_openrouter_metadata, require_openrouter_api_key


def build_headers() -> Dict[str, str]:
    """Construct the base headers required by OpenRouter."""

    headers = {
        "Authorization": f"Bearer {require_openrouter_api_key()}",
        "Content-Type": "application/json",
        "Accept": "text/event-stream",
    }
    headers.update(optional_openrouter_metadata())
    return headers


def consume_streaming_response(
    response: requests.Response,
    *,
    recorder: Optional[TraceRecorder],
    prefix: str,
    on_delta: Optional[Callable[[str], None]] = None,
) -> Tuple[Dict[str, Any], Dict[str, Optional[float]]]:
    """Read the streaming SSE payload emitted by OpenRouter."""

    content_parts: List[str] = []
    tool_call_builders: Dict[int, Dict[str, Any]] = {}
    message_role: Optional[str] = None
    finish_reason: Optional[str] = None
    usage: Optional[Dict[str, Any]] = None

    response_bytes = 0
    first_chunk_time: Optional[float] = None
    received_payload = False

    for raw_line in response.iter_lines(decode_unicode=True):
        if raw_line is None:
            continue
        if not raw_line.strip():
            continue
        response_bytes += len(raw_line.encode("utf-8")) + 1
        if not raw_line.startswith("data:"):
            continue
        payload = raw_line[len("data:") :].strip()
        if not payload:
            continue
        if payload == "[DONE]":
            break
        if first_chunk_time is None:
            first_chunk_time = perf_counter()
        try:
            chunk = json.loads(payload)
        except json.JSONDecodeError:
            continue
        received_payload = True

        if usage is None and isinstance(chunk.get("usage"), Mapping):
            usage = dict(chunk["usage"])

        choices = chunk.get("choices") or []
        if not choices:
            continue

        choice = choices[0]
        delta = choice.get("delta") or {}
        finish_reason = choice.get("finish_reason") or finish_reason

        role = delta.get("role")
        if isinstance(role, str):
            message_role = role

        text = delta.get("content")
        if isinstance(text, str):
            content_parts.append(text)

        if on_delta is not None and isinstance(text, str) and text:
            on_delta(text)

        for call in delta.get("tool_calls") or []:
            index = int(call.get("index", len(tool_call_builders)))
            builder = tool_call_builders.setdefault(
                index,
                {
                    "index": index,
                    "id": call.get("id"),
                    "type": call.get("type", "function"),
                    "function": {"name": "", "arguments": ""},
                },
            )
            if call.get("id"):
                builder["id"] = call["id"]
            function = call.get("function") or {}
            if "name" in function and isinstance(function["name"], str):
                builder["function"]["name"] = function["name"]
            if "arguments" in function and isinstance(function["arguments"], str):
                builder["function"]["arguments"] = (
                    builder["function"].get("arguments", "") + function["arguments"]
                )

    message: Dict[str, Any] = {
        "role": message_role or "assistant",
        "content": "".join(content_parts),
    }

    tool_calls: List[Dict[str, Any]] = []
    for index in sorted(tool_call_builders):
        entry = tool_call_builders[index]
        entry.pop("index", None)
        tool_calls.append(entry)
    if tool_calls:
        message["tool_calls"] = tool_calls

    data: Dict[str, Any] = {
        "choices": [
            {
                "message": message,
                "finish_reason": finish_reason or ("tool_calls" if tool_calls else "stop"),
            }
        ]
    }
    if usage:
        data["usage"] = usage

    metadata = {
        "response_bytes": float(response_bytes) if response_bytes else None,
        "first_chunk_time": first_chunk_time,
    }
    if not received_payload:
        raise ValueError("Empty streaming response received.")
    return data, metadata


def request_completion(
    base_url: str,
    model: str,
    messages: List[Dict[str, Any]],
    tool_definitions: List[Dict[str, Any]],
    timeout: float,
    *,
    segment_prefix: Optional[str] = None,
    recorder: Optional[TraceRecorder] = None,
    on_stream_delta: Optional[Callable[[str], None]] = None,
) -> Dict[str, Any]:
    """Send a streaming completion request and return the parsed response."""

    prefix = segment_prefix or "completion"
    build_start = perf_counter()
    payload: Dict[str, Any] = {
        "model": model,
        "messages": messages,
        "tools": tool_definitions,
        "tool_choice": "auto" if tool_definitions else "none",
        "stream": True,
    }
    headers = build_headers()
    build_end = perf_counter()
    if recorder:
        try:
            payload_chars = len(json.dumps(payload, ensure_ascii=False))
        except (TypeError, ValueError):  # pragma: no cover - defensive
            payload_chars = None
        recorder.add(
            f"{prefix}.prepare",
            build_end - build_start,
            metadata={"payload_chars": payload_chars},
        )

    response: Optional[requests.Response] = None
    post_start = perf_counter()
    stream_metadata: Dict[str, Optional[float]] = {}
    try:
        response = requests.post(
            base_url,
            json=payload,
            headers=headers,
            timeout=timeout,
            stream=True,
        )
        status = response.status_code
        if status >= 400:
            snippet = response.text[:400]
            raise requests.HTTPError(
                f"{status} {response.reason}: {snippet}",
                response=response,
            )
        try:
            data, stream_metadata = consume_streaming_response(
                response,
                recorder=recorder,
                prefix=prefix,
                on_delta=on_stream_delta,
            )
        except ValueError:
            # Fallback for providers that do not emit SSE payloads.
            try:
                buffer = response.content
                data = response.json()
            except ValueError as exc:
                snippet = buffer[:400].decode("utf-8", errors="replace") if buffer else ""
                raise requests.HTTPError(
                    f"Non-JSON response from OpenRouter (status {status}): {snippet}",
                    response=response,
                ) from exc
            stream_metadata = {
                "response_bytes": float(len(buffer)) if buffer else None,
                "first_chunk_time": None,
            }
        if not data.get("choices"):
            raise requests.HTTPError(
                "Streaming response did not include any choices.",
                response=response,
            )
    finally:
        post_end = perf_counter()
        if recorder:
            recorder.add(
                f"{prefix}.request",
                post_end - post_start,
                metadata={
                    "status": response.status_code if response is not None else None,
                    "ttfb": (
                        stream_metadata.get("first_chunk_time") - post_start
                        if stream_metadata.get("first_chunk_time") is not None
                        else None
                    ),
                    "response_bytes": stream_metadata.get("response_bytes"),
                },
            )

    if recorder:
        metadata: Dict[str, Any] = {}
        try:
            metadata["usage"] = data.get("usage")
        except Exception:  # pragma: no cover - defensive
            metadata["usage"] = None
        recorder.add(f"{prefix}.parse", 0.0, metadata=metadata or None)

    return data

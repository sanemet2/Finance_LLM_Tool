"""High-level chat orchestration logic and interactive loop."""

from __future__ import annotations

import sys
from time import perf_counter
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

import requests
from diagnostics import TraceRecorder

from .http_client import request_completion
from .tool_registry import ToolRegistry
from .transcript import Transcript, normalise_content


def chat_once(
    transcript: Transcript,
    registry: ToolRegistry,
    base_url: str,
    model: str,
    timeout: float,
    verbose: bool,
    trace: bool = False,
    live_stream: bool = False,
    stream_consumer: Optional[Callable[[str], None]] = None,
    tool_result_handler: Optional[Callable[[Dict[str, Any]], None]] = None,
) -> tuple[str, Optional[TraceRecorder], bool]:
    """Run a single completion cycle, executing tools until the assistant stops."""

    recorder = TraceRecorder() if trace else None
    streaming_enabled = live_stream or stream_consumer is not None
    live_emitted = False

    def emit(delta: str) -> None:
        nonlocal live_emitted
        if not delta:
            return
        if stream_consumer is not None:
            stream_consumer(delta)
        else:
            sys.stdout.write(delta)
            sys.stdout.flush()
        live_emitted = True

    emit_callback = emit if streaming_enabled else None

    if recorder:
        start = perf_counter()
        tool_defs = registry.tool_definitions()
        recorder.add(
            "collect_tool_definitions",
            perf_counter() - start,
            metadata={"count": len(tool_defs)},
        )
    else:
        tool_defs = registry.tool_definitions()

    completion_index = 1

    while True:
        if streaming_enabled:
            live_emitted = False

        segment_prefix = f"completion[{completion_index}]"
        response = request_completion(
            base_url,
            model,
            transcript.messages(),
            tool_defs,
            timeout,
            segment_prefix=segment_prefix,
            recorder=recorder,
            on_stream_delta=emit_callback,
        )

        handling_start = perf_counter() if recorder else None
        choice = response.get("choices", [{}])[0]
        message = choice.get("message") or {}
        raw_content = message.get("content")
        tool_calls = message.get("tool_calls") or []
        transcript.add_assistant(content=raw_content, tool_calls=tool_calls)

        if recorder and handling_start is not None:
            finish_reason = choice.get("finish_reason")
            content_chars = len(raw_content) if isinstance(raw_content, str) else None
            recorder.add(
                f"{segment_prefix}.response_handling",
                perf_counter() - handling_start,
                metadata={
                    "tool_calls": len(tool_calls),
                    "finish_reason": finish_reason,
                    "content_chars": content_chars,
                },
            )

        if not tool_calls:
            content_start = perf_counter() if recorder else None
            content = normalise_content(raw_content)
            if recorder and content_start is not None:
                metadata = {"content_chars": len(content)} if content else None
                recorder.add(
                    f"{segment_prefix}.content_normalise",
                    perf_counter() - content_start,
                    metadata=metadata,
                )
            if live_stream and stream_consumer is None and live_emitted:
                sys.stdout.write("\n")
                sys.stdout.flush()
            streamed_live = live_emitted if streaming_enabled else False
            return content, recorder, streamed_live

        transcript.append_tool_results(
            tool_calls,
            registry,
            verbose,
            recorder,
            result_handler=tool_result_handler,
        )
        completion_index += 1


def run_single_prompt(
    prompt: str,
    system_prompt: str,
    registry: ToolRegistry,
    base_url: str,
    model: str,
    timeout: float,
    verbose: bool,
    trace: bool,
    live_stream: bool,
) -> tuple[str, Optional[TraceRecorder], bool]:
    """Execute a single prompt end-to-end and return the assistant reply."""

    transcript = Transcript(system_prompt=system_prompt)
    transcript.add_user(prompt)
    return chat_once(
        transcript,
        registry,
        base_url,
        model,
        timeout,
        verbose,
        trace,
        live_stream,
    )


def interactive_loop(
    system_prompt: str,
    registry: ToolRegistry,
    base_url: str,
    model: str,
    timeout: float,
    verbose: bool,
    trace: bool,
    live_stream: bool,
    trace_width: int,
) -> None:
    """Run the REPL-style chat loop until the user exits."""

    transcript = Transcript(system_prompt=system_prompt)

    print("OpenRouter chat started. Type 'exit' or 'quit' to stop.")
    if verbose:
        tool_names = [tool["function"]["name"] for tool in registry.tool_definitions()]
        print(f"Loaded tools: {', '.join(tool_names) if tool_names else 'none'}")

    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nSession ended.")
            break

        if not user_input:
            continue
        if user_input.lower() in {"exit", "quit"}:
            print("Goodbye.")
            break

        transcript.add_user(user_input)
        streamed_live = False
        try:
            if live_stream:
                sys.stdout.write("Assistant: ")
                sys.stdout.flush()
            reply, recorder, streamed_live = chat_once(
                transcript,
                registry,
                base_url,
                model,
                timeout,
                verbose,
                trace,
                live_stream,
            )
        except requests.HTTPError as exc:
            print(f"[error] HTTP error: {exc}")
            transcript.pop_last()
            continue
        except requests.RequestException as exc:
            print(f"[error] Network error: {exc}")
            transcript.pop_last()
            continue
        except Exception as exc:
            print(f"[error] {exc}")
            transcript.pop_last()
            continue

        emit_start = perf_counter() if recorder and not streamed_live else None
        if not streamed_live:
            print(f"Assistant: {reply}")
        if recorder and emit_start is not None:
            recorder.add("assistant_emit", perf_counter() - emit_start)
        if trace and recorder:
            print(recorder.report(width=trace_width))

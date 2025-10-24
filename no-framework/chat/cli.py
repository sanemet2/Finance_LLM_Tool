"""Command-line entrypoint for the OpenRouter chat tool."""

from __future__ import annotations

import argparse
import sys
from time import perf_counter
from typing import List, Optional

import requests

from .conversation import interactive_loop, run_single_prompt
from .environment import (
    DEFAULT_BASE_URL,
    DEFAULT_MODEL,
    load_local_env,
    resolve_project_paths,
)
from .tool_registry import ToolRegistry


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    """Parse CLI arguments for the chat program."""

    parser = argparse.ArgumentParser(description="OpenRouter terminal chat with tool support.")
    parser.add_argument("--prompt", help="Run a single prompt and exit instead of interactive mode.")
    parser.add_argument(
        "--system",
        default=(
            "You are a finance assistant. Provide concise market context and only call tools when the user"
            " explicitly asks for specific data points. Prefer summarising using high-level trends over"
            " fetching ticker-by-ticker statistics unless a detailed lookup is necessary."
        ),
        help="System prompt.",
    )
    parser.add_argument("--model", default=DEFAULT_MODEL, help="OpenRouter model identifier.")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL, help="OpenRouter Responses API URL.")
    parser.add_argument("--timeout", type=float, default=60.0, help="Request timeout in seconds.")
    parser.add_argument("--verbose", action="store_true", help="Print tool outputs and diagnostics.")
    parser.add_argument(
        "--trace",
        action="store_true",
        help="Capture and display per-turn timing diagnostics.",
    )
    parser.add_argument(
        "--trace-width",
        type=int,
        default=32,
        help="Width of timing bars when --trace is enabled.",
    )
    parser.add_argument(
        "--live-stream",
        action="store_true",
        help="Stream assistant tokens live to the terminal.",
    )
    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    """CLI entry point."""

    paths = resolve_project_paths()
    load_local_env(paths.env_file)
    args = parse_args(argv)

    registry = ToolRegistry(paths.tools_root)
    if not registry.load():
        print("Warning: no tool modules found under agent_tools/.")

    try:
        if args.prompt:
            reply, recorder, streamed_live = run_single_prompt(
                args.prompt,
                args.system,
                registry,
                args.base_url,
                args.model,
                args.timeout,
                args.verbose,
                args.trace,
                args.live_stream,
            )
            emit_start = perf_counter() if recorder and not streamed_live else None
            if not (args.live_stream and streamed_live):
                print(reply)
            if recorder and emit_start is not None:
                recorder.add("assistant_emit", perf_counter() - emit_start)
            if args.trace and recorder:
                print(recorder.report(width=args.trace_width))
        else:
            interactive_loop(
                args.system,
                registry,
                args.base_url,
                args.model,
                args.timeout,
                args.verbose,
                args.trace,
                args.live_stream,
                args.trace_width,
            )
    except requests.HTTPError as exc:
        sys.stderr.write(f"HTTP error: {exc}\n")
        return 2
    except requests.RequestException as exc:
        sys.stderr.write(f"Network error: {exc}\n")
        return 2
    except Exception as exc:
        sys.stderr.write(f"Error: {exc}\n")
        return 1

    return 0

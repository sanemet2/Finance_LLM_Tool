"""Command-line entrypoint for the finance agent."""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path
from typing import Sequence

from dotenv import load_dotenv

from .agent import run_finance_agent


def load_environment() -> None:
    """Load environment variables from common .env locations."""

    candidates = [
        Path.cwd() / ".env",
        Path(__file__).resolve().parent.parent / ".env",
        Path(__file__).resolve().parent.parent.parent / ".env",
    ]
    for candidate in candidates:
        if candidate.is_file():
            load_dotenv(candidate, override=False, encoding="utf-8-sig")


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the finance agent against a prompt.")
    parser.add_argument(
        "prompt",
        nargs="*",
        help="Prompt to send to the agent; omit to enter interactive mode.",
    )
    return parser.parse_args(argv)


def _ensure_prompt(args: argparse.Namespace) -> str:
    if args.prompt:
        return " ".join(args.prompt)

    try:
        prompt = input("Enter your finance question: ").strip()
    except KeyboardInterrupt:
        print("\nAborted.", file=sys.stderr)
        raise SystemExit(1)

    if not prompt:
        raise SystemExit("A prompt is required to query the finance agent.")

    return prompt


async def _run(prompt: str) -> None:
    answer = await run_finance_agent(prompt)
    print(answer.text)


def main(argv: Sequence[str] | None = None) -> int:
    load_environment()
    args = parse_args(sys.argv[1:] if argv is None else argv)
    prompt = _ensure_prompt(args)

    try:
        asyncio.run(_run(prompt))
    except KeyboardInterrupt:
        print("\nAborted.", file=sys.stderr)
        return 1
    except Exception as exc:  # pragma: no cover - surface errors cleanly
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

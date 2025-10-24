#!/usr/bin/env python3
"""OpenRouter tool definitions backed by :mod:`yfinance_service`.

This module keeps the OpenAI/OpenRouter tool schema alongside the dispatcher
logic so an orchestrator can import a single helper and wire it into the
chat loop.  It provides two main entry points:

* :func:`get_tool_definitions` — returns the tool metadata payload to pass to
  OpenRouter's ``tools`` parameter.
* :func:`execute_tool_call` — performs a tool invocation given the tool name
  and JSON arguments supplied by the model, producing a JSON string that can
  be sent back as a ``tool`` message.

The helper CLI makes local smoke testing easy::

    python openrouter_tools.py --list-tools
    python openrouter_tools.py --call download_price_history --arguments '{"tickers": "COST", "period": "1mo"}'
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any, Dict, Iterable, Mapping

from yfinance_service import YFinanceService, YFinanceServiceError


def _enum(items: Iterable[str]) -> list[str]:
    """Return a sorted list to stabilise JSON schema enums."""

    return sorted(set(items))


_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "download_price_history",
            "description": "Fetch OHLCV price history for one ticker via yfinance.download.",
            "parameters": {
                "type": "object",
                "properties": {
                    "tickers": {
                        "type": "string",
                        "description": "Ticker symbol (single symbol supported).",
                    },
                    "period": {
                        "type": "string",
                        "description": "Optional Yahoo range shorthand (e.g., 1mo, 6mo, 2y).",
                        "enum": _enum(
                            {
                                "1d",
                                "5d",
                                "1mo",
                                "3mo",
                                "6mo",
                                "1y",
                                "2y",
                                "5y",
                                "10y",
                                "ytd",
                                "max",
                            }
                        ),
                    },
                    "interval": {
                        "type": "string",
                        "description": "Data interval (default 1d).",
                        "enum": _enum(
                            {
                                "1m",
                                "2m",
                                "5m",
                                "15m",
                                "30m",
                                "60m",
                                "90m",
                                "1h",
                                "1d",
                                "5d",
                                "1wk",
                                "1mo",
                                "3mo",
                            }
                        ),
                        "default": "1d",
                    },
                    "start": {
                        "type": ["string", "null"],
                        "description": "Optional start date (YYYY-MM-DD).",
                    },
                    "end": {
                        "type": ["string", "null"],
                        "description": "Optional end date (YYYY-MM-DD).",
                    },
                    "actions": {
                        "type": "boolean",
                        "description": "Include dividends and splits.",
                        "default": False,
                    },
                    "auto_adjust": {
                        "type": ["boolean", "null"],
                        "description": "Override auto_adjust flag.",
                    },
                    "prepost": {
                        "type": "boolean",
                        "description": "Include pre/post-market data when available.",
                        "default": False,
                    },
                },
                "required": ["tickers"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_ticker_fast_info",
            "description": "Return Yahoo Finance fast_info snapshot for a ticker.",
            "parameters": {
                "type": "object",
                "properties": {
                    "ticker": {
                        "type": "string",
                        "description": "Ticker symbol (e.g., AAPL).",
                    }
                },
                "required": ["ticker"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_ticker_summary",
            "description": "Return Yahoo Finance summary info data for a ticker.",
            "parameters": {
                "type": "object",
                "properties": {
                    "ticker": {
                        "type": "string",
                        "description": "Ticker symbol (e.g., NVDA).",
                    }
                },
                "required": ["ticker"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_ticker_news",
            "description": "Fetch the latest Yahoo Finance news items for a ticker.",
            "parameters": {
                "type": "object",
                "properties": {
                    "ticker": {
                        "type": "string",
                        "description": "Ticker symbol (e.g., MSFT).",
                    },
                    "count": {
                        "type": "integer",
                        "minimum": 0,
                        "description": "Optional cap on the number of news items.",
                    },
                },
                "required": ["ticker"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_ticker_fundamentals",
            "description": "Return core fundamental tables (financials, balance sheet, cashflow).",
            "parameters": {
                "type": "object",
                "properties": {
                    "ticker": {
                        "type": "string",
                        "description": "Ticker symbol (e.g., WMT).",
                    }
                },
                "required": ["ticker"],
            },
        },
    },
]

_OPERATIONS: Mapping[str, str] = {
    "download_price_history": "download_price_history",
    "get_ticker_fast_info": "get_ticker_fast_info",
    "get_ticker_summary": "get_ticker_summary",
    "get_ticker_news": "get_ticker_news",
    "get_ticker_fundamentals": "get_ticker_fundamentals",
}


def get_tool_definitions() -> list[dict[str, Any]]:
    """Return OpenRouter-compatible tool definitions."""

    return _TOOL_DEFINITIONS


def _ensure_mapping(arguments: str | Mapping[str, Any]) -> Dict[str, Any]:
    """Coerce tool arguments into a dictionary."""

    if isinstance(arguments, Mapping):
        return dict(arguments)
    if not arguments:
        return {}
    try:
        decoded = json.loads(arguments)
    except json.JSONDecodeError as exc:  # pragma: no cover - defensive
        raise ValueError(f"Tool arguments are not valid JSON: {arguments!r}") from exc
    if not isinstance(decoded, Mapping):
        raise ValueError("Tool arguments must decode to a JSON object")
    return dict(decoded)


def execute_tool_call(tool_name: str, arguments: str | Mapping[str, Any]) -> str:
    """Execute a tool call and return a JSON string suitable for tool output.

    The returned JSON has a small, stable envelope::

        {"ok": true, "result": {...}}  # success
        {"ok": false, "error": {"type": "...", "message": "..."}}
    """

    if tool_name not in _OPERATIONS:
        raise ValueError(f"Unsupported tool: {tool_name}")

    params = _ensure_mapping(arguments)
    service = YFinanceService()
    handler = getattr(service, _OPERATIONS[tool_name])

    try:
        payload = handler(**params)
    except (TypeError, ValueError) as exc:
        error = {
            "ok": False,
            "error": {
                "type": exc.__class__.__name__,
                "message": str(exc),
            },
        }
        return json.dumps(error)
    except YFinanceServiceError as exc:
        error = {
            "ok": False,
            "error": {
                "type": exc.__class__.__name__,
                "message": str(exc),
            },
        }
        return json.dumps(error)
    except Exception as exc:  # pragma: no cover - guard against unexpected issues
        error = {
            "ok": False,
            "error": {
                "type": exc.__class__.__name__,
                "message": str(exc),
            },
        }
        return json.dumps(error)

    return json.dumps({"ok": True, "result": payload})


def _cli() -> int:
    parser = argparse.ArgumentParser(description="Inspect or call OpenRouter tools.")
    parser.add_argument("--list-tools", action="store_true", help="Print the tool schema JSON.")
    parser.add_argument(
        "--call",
        metavar="NAME",
        help="Execute a tool by name using the provided JSON arguments.",
    )
    parser.add_argument(
        "--arguments",
        "-a",
        help="JSON object with arguments for the tool (required with --call).",
    )
    args = parser.parse_args()

    if args.list_tools:
        json.dump(get_tool_definitions(), sys.stdout, indent=2)
        sys.stdout.write("\n")
        return 0

    if args.call:
        if args.arguments is None:
            parser.error("--arguments is required when using --call")
        response = execute_tool_call(args.call, args.arguments)
        sys.stdout.write(response + "\n")
        return 0

    parser.print_help()
    return 0


if __name__ == "__main__":  # pragma: no cover - manual usage
    raise SystemExit(_cli())

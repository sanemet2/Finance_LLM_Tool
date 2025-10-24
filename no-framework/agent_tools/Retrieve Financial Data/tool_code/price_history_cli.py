#!/usr/bin/env python3
"""Thin CLI wrapper around yfinance_service for quick price history fetches."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, Optional

from yfinance_service import YFinanceService, YFinanceServiceError


def _build_params(args: argparse.Namespace) -> Dict[str, Any]:
    params: Dict[str, Any] = {"tickers": args.ticker.upper()}
    if args.period:
        params["period"] = args.period
    if args.interval:
        params["interval"] = args.interval
    if args.start:
        params["start"] = args.start
    if args.end:
        params["end"] = args.end
    if args.actions:
        params["actions"] = True
    if args.auto_adjust is not None:
        params["auto_adjust"] = args.auto_adjust
    if args.prepost:
        params["prepost"] = True
    return params


def _summarise_rows(rows: list[Dict[str, Any]]) -> Dict[str, Optional[str]]:
    if not rows:
        return {"start_date": None, "end_date": None}
    return {"start_date": rows[0].get("Date"), "end_date": rows[-1].get("Date")}


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Fetch price history via yfinance_service with simple flags."
    )
    parser.add_argument("--ticker", required=True, help="Ticker symbol, e.g. COST")
    parser.add_argument("--period", help="Duration shorthand such as 2y, 6mo, 5d")
    parser.add_argument("--interval", default="1d", help="Data interval (1d, 1wk, etc.)")
    parser.add_argument("--start", help="ISO start date (YYYY-MM-DD)")
    parser.add_argument("--end", help="ISO end date (YYYY-MM-DD)")
    parser.add_argument("--actions", action="store_true", help="Include dividends/splits")
    auto_group = parser.add_mutually_exclusive_group()
    auto_group.add_argument(
        "--auto-adjust",
        dest="auto_adjust",
        action="store_const",
        const=True,
        help="Force auto_adjust=True",
    )
    auto_group.add_argument(
        "--no-auto-adjust",
        dest="auto_adjust",
        action="store_const",
        const=False,
        help="Force auto_adjust=False",
    )
    parser.set_defaults(auto_adjust=None)
    parser.add_argument("--prepost", action="store_true", help="Include pre/post-market data")
    parser.add_argument(
        "--output-json",
        help="Optional path to write JSON response; defaults to stdout",
    )
    parser.add_argument(
        "--compact",
        action="store_true",
        help="Emit minimal JSON (omit full data block)",
    )
    args = parser.parse_args(argv)

    params = _build_params(args)

    service = YFinanceService()
    try:
        data = service.download_price_history(**params)
    except YFinanceServiceError as exc:
        sys.stderr.write(f"Error: {exc}\n")
        return 2

    rows = data.get("rows", [])
    summary = _summarise_rows(rows)
    summary["row_count"] = len(rows)
    summary["ticker"] = data.get("tickers")

    payload: Dict[str, Any] = {"ok": True, "summary": summary}
    if not args.compact:
        payload["data"] = data

    text = json.dumps(payload, indent=2)
    if args.output_json:
        Path(args.output_json).write_text(text, encoding="utf-8")
    else:
        sys.stdout.write(text + "\n")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

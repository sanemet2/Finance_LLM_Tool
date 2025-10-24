"""High-level service layer wrapping a subset of yfinance for LLM tooling.

The service exposes a small set of deterministic operations that can be
invoked by passing JSON into this script (stdin or --input-json). Results are
emitted as JSON that only uses primitives so an LLM agent can safely parse.

Example CLI usage::

    python yfinance_service.py --operation download_price_history \
        --params '{"tickers": "AAPL", "period": "1mo", "interval": "1d"}'

    python yfinance_service.py --input-json request.json --output-json result.json

When invoked via stdin, provide an object with ``operation`` and optional
``params`` keys. The module can also be imported and the ``YFinanceService``
class used directly.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, MutableMapping, Optional

import pandas as pd
import yfinance as yf

try:  # numpy is expected to be available in yfinance environments
    import numpy as np
except ImportError:  # pragma: no cover - fallback if numpy missing
    np = None  # type: ignore

try:  # diagnostics are optional when running tools standalone
    from diagnostics.runtime import trace_segment
except ImportError:  # pragma: no cover - diagnostics not available
    from contextlib import contextmanager

    @contextmanager
    def trace_segment(name: str, *, metadata: Optional[Dict[str, Any]] = None):
        yield

PERIOD_CHOICES = {
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

INTERVAL_CHOICES = {
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


class YFinanceServiceError(RuntimeError):
    """Raised when the service encounters a recoverable problem."""


def _validate_choice(name: str, value: Optional[str], allowed: Iterable[str]) -> None:
    if value is None:
        return
    if value not in allowed:
        raise ValueError(f"{name} must be one of {sorted(allowed)}, got {value!r}")


def _json_safe(value: Any) -> Any:
    """Convert pandas/numpy types into JSON-serialisable primitives."""

    if value is None:
        return None
    if value is getattr(pd, "NA", None):
        return None
    if value is pd.NaT:
        return None
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, (datetime, pd.Timestamp)):
        return value.isoformat()
    if isinstance(value, pd.Timedelta):
        return value.total_seconds()
    if np is not None:
        if isinstance(value, np.generic):
            return _json_safe(value.item())
        if isinstance(value, np.ndarray):
            return [_json_safe(v) for v in value.tolist()]
    if isinstance(value, pd.Series):
        return [_json_safe(v) for v in value.tolist()]
    if isinstance(value, pd.Index):
        return [_json_safe(v) for v in value.tolist()]
    if isinstance(value, (list, tuple)):
        return [_json_safe(v) for v in value]
    if isinstance(value, Mapping):
        return {str(k): _json_safe(v) for k, v in value.items()}
    return value


def _frame_to_records(frame: Optional[pd.DataFrame]) -> List[Dict[str, Any]]:
    """Flatten a DataFrame into a list of JSON-safe row dictionaries."""

    if frame is None or frame.empty:
        return []

    working = frame.copy()
    working = working.reset_index()

    if isinstance(working.columns, pd.MultiIndex):
        working.columns = [
            "_".join(str(part) for part in col if part not in (None, "")).strip("_")
            or "value"
            for col in working.columns
        ]

    records = working.to_dict(orient="records")
    return [{k: _json_safe(v) for k, v in row.items()} for row in records]


def _ensure_ticker(value: str) -> str:
    if not value or not isinstance(value, str):
        raise ValueError("ticker must be a non-empty string")
    return value.strip().upper()


class YFinanceService:
    """Deterministic wrappers around selected yfinance calls."""

    def __init__(self) -> None:
        self._operations: Dict[str, Any] = {
            "download_price_history": self.download_price_history,
            "get_ticker_fast_info": self.get_ticker_fast_info,
            "get_ticker_summary": self.get_ticker_summary,
            "get_ticker_news": self.get_ticker_news,
            "get_ticker_fundamentals": self.get_ticker_fundamentals,
            "list_operations": self.list_operations,
        }

    def dispatch(self, operation: str, params: Optional[Mapping[str, Any]] = None) -> Any:
        if operation not in self._operations:
            raise YFinanceServiceError(f"Unknown operation: {operation}")
        handler = self._operations[operation]
        params = dict(params or {})
        try:
            return handler(**params)
        except TypeError as exc:  # surface friendlier error on unexpected kwargs
            raise YFinanceServiceError(str(exc)) from exc

    # --- operations -----------------------------------------------------------------

    def list_operations(self) -> List[str]:
        """Return the supported operation names."""

        return sorted(self._operations.keys())

    def download_price_history(
        self,
        *,
        tickers: str,
        period: Optional[str] = None,
        interval: str = "1d",
        start: Optional[str] = None,
        end: Optional[str] = None,
        actions: bool = False,
        auto_adjust: Optional[bool] = None,
        prepost: bool = False,
        keepna: bool = False,
        group_by: str = "column",
        threads: bool = True,
      ) -> Dict[str, Any]:
          """Wrap ``yfinance.download`` with validation and JSON encoding."""

          with trace_segment("service:download_price_history.validate"):
              if not tickers:
                  raise ValueError("tickers is required")
              _validate_choice("period", period, PERIOD_CHOICES)
              _validate_choice("interval", interval, INTERVAL_CHOICES)

          with trace_segment(
              "service:download_price_history.fetch",
              metadata={"tickers": tickers, "period": period, "interval": interval},
          ):
              data = yf.download(
                  tickers=tickers,
                  period=period,
                  interval=interval,
                  start=start,
                  end=end,
                  actions=actions,
                  auto_adjust=auto_adjust,
                  prepost=prepost,
                  keepna=keepna,
                  group_by=group_by,
                  threads=threads,
                  progress=False,
              )

          with trace_segment("service:download_price_history.normalise"):
              rows = _frame_to_records(data)

          return {
              "tickers": tickers,
              "period": period,
              "interval": interval,
              "start": start,
              "end": end,
              "actions": actions,
              "auto_adjust": auto_adjust,
              "prepost": prepost,
              "rows": rows,
          }

    def get_ticker_fast_info(
        self,
        *,
        ticker: str,
      ) -> Dict[str, Any]:
          """Return ``Ticker.fast_info`` as primitives."""

          with trace_segment("service:get_ticker_fast_info.validate"):
              symbol = _ensure_ticker(ticker)

          with trace_segment("service:get_ticker_fast_info.fetch", metadata={"ticker": symbol}):
              info = yf.Ticker(symbol).fast_info

          with trace_segment("service:get_ticker_fast_info.normalise"):
              payload = _json_safe(dict(info))

          return {"ticker": symbol, "fast_info": payload}

    def get_ticker_summary(
        self,
        *,
        ticker: str,
      ) -> Dict[str, Any]:
          """Return ``Ticker.info`` for a ticker."""

          with trace_segment("service:get_ticker_summary.validate"):
              symbol = _ensure_ticker(ticker)

          with trace_segment("service:get_ticker_summary.fetch", metadata={"ticker": symbol}):
              info = yf.Ticker(symbol).info

          with trace_segment("service:get_ticker_summary.normalise"):
              payload = _json_safe(info)

          return {"ticker": symbol, "summary": payload}

    def get_ticker_news(
        self,
        *,
        ticker: str,
        count: Optional[int] = None,
      ) -> Dict[str, Any]:
          """Fetch recent news items for a ticker."""

          with trace_segment("service:get_ticker_news.validate"):
              symbol = _ensure_ticker(ticker)

          with trace_segment("service:get_ticker_news.fetch", metadata={"ticker": symbol}):
              items = yf.Ticker(symbol).news or []

          if count is not None and count >= 0:
              with trace_segment("service:get_ticker_news.slice"):
                  items = items[:count]

          with trace_segment("service:get_ticker_news.normalise"):
              payload = _json_safe(items)

          return {"ticker": symbol, "news": payload}

    def get_ticker_fundamentals(
        self,
        *,
        ticker: str,
      ) -> Dict[str, Any]:
          """Return key fundamental tables for a ticker."""

          with trace_segment("service:get_ticker_fundamentals.validate"):
              symbol = _ensure_ticker(ticker)

          with trace_segment("service:get_ticker_fundamentals.fetch", metadata={"ticker": symbol}):
              tkr = yf.Ticker(symbol)

          with trace_segment("service:get_ticker_fundamentals.normalise"):
              financials = _frame_to_records(tkr.financials)
              q_financials = _frame_to_records(tkr.quarterly_financials)
              balance = _frame_to_records(tkr.balance_sheet)
              q_balance = _frame_to_records(tkr.quarterly_balance_sheet)
              cashflow = _frame_to_records(tkr.cashflow)
              q_cashflow = _frame_to_records(tkr.quarterly_cashflow)

          return {
              "ticker": symbol,
              "financials": financials,
              "quarterly_financials": q_financials,
              "balance_sheet": balance,
              "quarterly_balance_sheet": q_balance,
              "cashflow": cashflow,
              "quarterly_cashflow": q_cashflow,
          }


# --- command-line interface ---------------------------------------------------------

def _load_request(args: argparse.Namespace) -> Dict[str, Any]:
    """Load a request from CLI flags, stdin, or a JSON file."""

    if args.input_json:
        return json.loads(Path(args.input_json).read_text(encoding="utf-8"))

    if not sys.stdin.isatty():
        raw = sys.stdin.read().strip()
        if raw:
            return json.loads(raw)

    if not args.operation:
        raise SystemExit("operation is required when no JSON request is supplied")

    params: Dict[str, Any]
    if args.params:
        params = json.loads(args.params)
        if not isinstance(params, dict):
            raise SystemExit("--params must decode to a JSON object")
    else:
        params = {}

    return {"operation": args.operation, "params": params}


def _emit_response(response: Dict[str, Any], destination: Optional[str]) -> None:
    payload = json.dumps(response, indent=2, ensure_ascii=False)
    if destination:
        Path(destination).write_text(payload, encoding="utf-8")
    else:
        sys.stdout.write(payload)
        sys.stdout.write("\n")
        sys.stdout.flush()


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Execute a yfinance service operation")
    parser.add_argument("--operation", "-o", help="Name of the operation to run")
    parser.add_argument(
        "--params",
        "-p",
        help="JSON object with parameters for the operation (ignored when using stdin/input-json)",
    )
    parser.add_argument(
        "--input-json",
        "-i",
        help="Path to a JSON file containing a request {operation, params}",
    )
    parser.add_argument(
        "--output-json",
        "-O",
        help="Optional path to write the JSON response instead of stdout",
    )
    args = parser.parse_args(argv)

    try:
        request = _load_request(args)
        operation = request.get("operation")
        if not operation or not isinstance(operation, str):
            raise YFinanceServiceError("Request JSON must include a string 'operation' field")
        params = request.get("params") or {}
        if not isinstance(params, MutableMapping):
            raise YFinanceServiceError("'params' must be a JSON object")

        service = YFinanceService()
        data = service.dispatch(operation, params)
        response = {"ok": True, "operation": operation, "data": _json_safe(data)}
    except Exception as exc:  # deliberate broad catch for tooling robustness
        response = {
            "ok": False,
            "operation": request.get("operation") if "request" in locals() else None,
            "error": {
                "type": exc.__class__.__name__,
                "message": str(exc),
            },
        }
        _emit_response(response, args.output_json)
        return 1

    _emit_response(response, args.output_json)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

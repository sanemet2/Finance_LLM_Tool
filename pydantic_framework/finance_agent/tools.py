"""Tool definitions wrapping the shared yfinance service."""

from __future__ import annotations

import asyncio
import re
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from pydantic import BaseModel, Field
from pydantic_ai import Agent, RunContext

from .dependencies import FinanceDependencies

PERIOD_CHOICES = [
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
]

INTERVAL_CHOICES = [
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
    "7d",
    "1wk",
    "1mo",
    "3mo",
]


class DownloadPriceHistoryInput(BaseModel):
    tickers: str
    period: Optional[str] = Field(None, description=f"Range to request (choices: {', '.join(PERIOD_CHOICES)})")
    interval: Optional[str] = Field(None, description=f"Sampling interval (choices: {', '.join(INTERVAL_CHOICES)})")
    start: Optional[str] = Field(None, description="ISO-8601 start date")
    end: Optional[str] = Field(None, description="ISO-8601 end date")
    actions: Optional[bool] = Field(None, description="Include corporate actions in the response")
    auto_adjust: Optional[bool] = Field(
        None, description="Auto adjust OHLC data (mirrors yfinance's `auto_adjust` flag)"
    )
    prepost: Optional[bool] = Field(None, description="Include pre/post market data when available")

    class Config:
        extra = "forbid"


class TickerOnlyInput(BaseModel):
    ticker: str = Field(..., description="Yahoo Finance ticker symbol (e.g. AAPL)")

    class Config:
        extra = "forbid"


class TickerNewsInput(TickerOnlyInput):
    count: Optional[int] = Field(None, gt=0, le=50, description="Optional limit on returned news items")


_RELATIVE_PERIOD_PATTERN = re.compile(
    r"^\s*(?P<amount>\d+)\s*(?P<unit>w|week|weeks|d|day|days)\s*$",
    re.IGNORECASE,
)


def _normalize_period(payload: dict[str, Any]) -> dict[str, Any]:
    """Convert relative periods (e.g. `6w`) into explicit start dates for yfinance."""

    period = payload.get("period")
    if not period:
        return payload

    normalized = str(period).lower().strip()
    if normalized in PERIOD_CHOICES:
        return payload

    match = _RELATIVE_PERIOD_PATTERN.match(normalized)
    if not match:
        return payload

    amount = int(match.group("amount"))
    unit = match.group("unit")
    if amount <= 0:
        return payload

    if unit.startswith("w"):
        delta = timedelta(weeks=amount)
    elif unit.startswith("d"):
        delta = timedelta(days=amount)
    else:  # pragma: no cover - guarded by regex
        return payload

    end = datetime.now(timezone.utc).date()
    start = (end - delta).isoformat()

    payload = payload.copy()
    payload.pop("period", None)
    payload.setdefault("end", end.isoformat())
    payload["start"] = start
    return payload


def attach_finance_tools(agent: Agent[FinanceDependencies, Any]) -> None:
    """Register yfinance-backed tools on the supplied agent."""

    @agent.tool
    async def download_price_history(
        ctx: RunContext[FinanceDependencies],
        params: DownloadPriceHistoryInput,
    ) -> dict[str, Any]:
        """Fetch OHLCV price history for a ticker via yfinance."""

        service = ctx.deps.yfinance_service
        payload = _normalize_period(params.model_dump(exclude_none=True))
        return await asyncio.to_thread(service.download_price_history, **payload)

    @agent.tool
    async def get_ticker_fast_info(
        ctx: RunContext[FinanceDependencies],
        params: TickerOnlyInput,
    ) -> dict[str, Any]:
        """Return Yahoo Finance fast_info snapshot for a ticker."""

        service = ctx.deps.yfinance_service
        payload = params.model_dump(exclude_none=True)
        return await asyncio.to_thread(service.get_ticker_fast_info, **payload)

    @agent.tool
    async def get_ticker_summary(
        ctx: RunContext[FinanceDependencies],
        params: TickerOnlyInput,
    ) -> dict[str, Any]:
        """Retrieve the Yahoo Finance summary profile for a ticker."""

        service = ctx.deps.yfinance_service
        payload = params.model_dump(exclude_none=True)
        return await asyncio.to_thread(service.get_ticker_summary, **payload)

    @agent.tool
    async def get_ticker_news(
        ctx: RunContext[FinanceDependencies],
        params: TickerNewsInput,
    ) -> dict[str, Any]:
        """Fetch recent Yahoo Finance news items for a ticker."""

        service = ctx.deps.yfinance_service
        payload = params.model_dump(exclude_none=True)
        return await asyncio.to_thread(service.get_ticker_news, **payload)

    @agent.tool
    async def get_ticker_fundamentals(
        ctx: RunContext[FinanceDependencies],
        params: TickerOnlyInput,
    ) -> dict[str, Any]:
        """Return fundamental financial statements (balance sheet, cash flow, etc.) for a ticker."""

        service = ctx.deps.yfinance_service
        payload = params.model_dump(exclude_none=True)
        return await asyncio.to_thread(service.get_ticker_fundamentals, **payload)

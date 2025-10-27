"""Dependency definitions for the finance agent."""

from __future__ import annotations

from dataclasses import dataclass

from .services import YFinanceService


@dataclass(slots=True)
class FinanceDependencies:
    """Runtime dependencies injected into agent tools."""

    yfinance_service: YFinanceService


def build_dependencies() -> FinanceDependencies:
    """Construct the dependencies used by the agent runtime."""

    return FinanceDependencies(yfinance_service=YFinanceService())

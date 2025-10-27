"""Thin loader that reuses the existing yfinance_service module."""

from __future__ import annotations

from importlib import util
from pathlib import Path
from types import ModuleType
from typing import Any, TypeVar, cast

SERVICE_RELATIVE_PATH = (
    Path(__file__).resolve().parents[3] / "vercel_framework" / "python" / "yfinance_service.py"
)
MODULE_NAME = "finance_llm_tool.vercel_framework.python.yfinance_service"


def _load_module() -> ModuleType:
    if not SERVICE_RELATIVE_PATH.exists():
        raise FileNotFoundError(
            f"Expected yfinance_service.py at {SERVICE_RELATIVE_PATH}, "
            "but no file was found. Ensure the legacy vercel framework is present.",
        )

    spec = util.spec_from_file_location(MODULE_NAME, SERVICE_RELATIVE_PATH)
    if spec is None or spec.loader is None:
        raise ImportError(f"Unable to create module spec for {SERVICE_RELATIVE_PATH}")

    module = util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_MODULE = _load_module()
_T = TypeVar("_T")


def _export(name: str) -> Any:
    try:
        return getattr(_MODULE, name)
    except AttributeError as exc:
        raise ImportError(
            f"Attribute {name!r} not found in {SERVICE_RELATIVE_PATH}. "
            "Ensure the service exposes the expected API.",
        ) from exc


YFinanceService = cast(type, _export("YFinanceService"))
YFinanceServiceError = cast(type, _export("YFinanceServiceError"))

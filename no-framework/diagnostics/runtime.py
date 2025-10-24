"""Runtime helpers for sharing diagnostics state across modules."""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from typing import Dict, Iterator, Optional

from .timing import TraceRecorder

_CURRENT: ContextVar[Optional[TraceRecorder]] = ContextVar("diagnostics_recorder", default=None)


def get_recorder() -> Optional[TraceRecorder]:
    """Return the recorder currently in scope, if any."""

    return _CURRENT.get()


@contextmanager
def scoped_recorder(recorder: Optional[TraceRecorder]) -> Iterator[Optional[TraceRecorder]]:
    """Temporarily expose a recorder to nested code."""

    token = _CURRENT.set(recorder)
    try:
        yield recorder
    finally:
        _CURRENT.reset(token)


@contextmanager
def trace_segment(name: str, *, metadata: Optional[Dict[str, object]] = None) -> Iterator[None]:
    """Record a timed segment against the current recorder."""

    recorder = _CURRENT.get()
    if recorder is None:
        yield
        return

    with recorder.span(name, metadata=metadata):
        yield


__all__ = ["get_recorder", "scoped_recorder", "trace_segment"]


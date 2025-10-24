"""Diagnostics utilities for the Finance LLM Tool."""

from .runtime import get_recorder, scoped_recorder, trace_segment
from .timing import TraceRecorder, TraceSegment

__all__ = [
    "TraceRecorder",
    "TraceSegment",
    "get_recorder",
    "scoped_recorder",
    "trace_segment",
]


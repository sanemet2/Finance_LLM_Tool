"""Lightweight timing primitives and reporting helpers."""

from __future__ import annotations

from dataclasses import dataclass, field
from math import floor
from time import perf_counter
from typing import Any, Dict, Iterable, List, Optional, Tuple


@dataclass
class TraceSegment:
    """Represents a single timed segment."""

    name: str
    duration: float
    metadata: Optional[Dict[str, Any]] = field(default=None)


class TraceRecorder:
    """Collects timing segments for a single operation."""

    def __init__(self) -> None:
        self._segments: List[TraceSegment] = []

    def add(
        self,
        name: str,
        duration: float,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Append a completed segment."""

        self._segments.append(TraceSegment(name=name, duration=duration, metadata=metadata))

    def span(self, name: str, *, metadata: Optional[Dict[str, Any]] = None) -> "_Span":
        """Return a context manager that records a timed span."""

        return _Span(self, name, metadata=metadata)

    def segments(self) -> List[TraceSegment]:
        """Return recorded segments."""

        return list(self._segments)

    def aggregate(self) -> List[TraceSegment]:
        """Aggregate durations by segment name while preserving insertion order."""

        totals: Dict[str, TraceSegment] = {}
        order: List[str] = []
        for segment in self._segments:
            if segment.name not in totals:
                totals[segment.name] = TraceSegment(segment.name, 0.0, metadata=None)
                order.append(segment.name)
            totals[segment.name].duration += segment.duration
        return [totals[name] for name in order]

    def total_duration(self) -> float:
        """Return the total recorded duration."""

        return sum(segment.duration for segment in self._segments)

    def report(self, *, width: int = 32, collapse: bool = False) -> str:
        """Render a textual bar chart showing time spent per segment."""

        if collapse:
            segments: List[TraceSegment] = self.aggregate()
        else:
            segments = self._segments

        if not segments:
            return "Timing summary: no segments recorded."

        durations = [segment.duration for segment in segments]
        bars = _render_bars(durations, width=width)
        total = sum(durations)

        lines = [f"Timing summary (total {total:.3f}s):"]
        for segment, bar in zip(segments, bars):
            percent = (segment.duration / total * 100.0) if total else 0.0
            meta = ""
            if segment.metadata:
                meta_text = _format_metadata(segment.metadata)
                if meta_text:
                    meta = "  " + meta_text
            lines.append(
                f"{segment.name:<36} {segment.duration:>7.3f}s  {bar} {percent:5.1f}%{meta}"
            )
        return "\n".join(lines)


class _Span:
    """Context manager for a timed span."""

    def __init__(
        self,
        recorder: TraceRecorder,
        name: str,
        *,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        self._recorder = recorder
        self._name = name
        self._metadata = metadata
        self._start = None

    def __enter__(self) -> "_Span":
        self._start = perf_counter()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        stop = perf_counter()
        start = self._start or stop
        duration = stop - start
        self._recorder.add(self._name, duration, self._metadata)


def _render_bars(durations: Iterable[float], *, width: int) -> List[str]:
    values = list(durations)
    total = sum(values)
    if total <= 0.0:
        return ["[" + ("-" * width) + "]" for _ in values]

    raw: List[Tuple[int, float]] = []
    accum = 0
    for index, value in enumerate(values):
        scaled = value / total * width
        integer = floor(scaled)
        raw.append((index, scaled - integer))
        values[index] = integer
        accum += integer

    remainder = width - accum
    for index, fraction in sorted(raw, key=lambda entry: entry[1], reverse=True):
        if remainder <= 0:
            break
        values[index] += 1
        remainder -= 1

    bars = []
    for value in values:
        filled = int(value)
        filled = max(0, min(width, filled))
        bar = "#" * filled + "-" * (width - filled)
        bars.append(f"[{bar}]")
    return bars


def _format_metadata(metadata: Dict[str, Any]) -> str:
    parts = []
    for key, value in metadata.items():
        if value is None:
            continue
        parts.append(f"{key}={value}")
    return ", ".join(parts)


__all__ = ["TraceRecorder", "TraceSegment"]

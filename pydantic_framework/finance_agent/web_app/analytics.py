"""Helpers for collecting and serializing analytics during a chat run."""

from __future__ import annotations

import json
import math
import time
from dataclasses import dataclass, field
from typing import Any, Iterable, Sequence

from pydantic_ai.messages import (
    AgentStreamEvent,
    FinalResultEvent,
    FunctionToolCallEvent,
    FunctionToolResultEvent,
    PartStartEvent,
    TextPart,
)


def _now_ms(reference: float, current: float | None = None) -> float:
    """Compute the milliseconds since `reference` using `time.perf_counter()` semantics."""

    base = current if current is not None else time.perf_counter()
    return (base - reference) * 1_000.0


def _summarize_payload(payload: Any, *, limit: int = 240) -> dict[str, Any] | None:
    """Return a compact, JSON-ready summary describing the payload."""

    if payload is None:
        return None

    if isinstance(payload, (int, float)) and not isinstance(payload, bool):
        text = str(payload)
    elif isinstance(payload, str):
        text = payload
    else:
        try:
            text = json.dumps(payload, default=str)
        except TypeError:
            text = str(payload)

    length = len(text)
    truncated = length > limit
    preview = text if not truncated else f"{text[:limit].rstrip()}..."

    return {
        "preview": preview,
        "length": length,
        "truncated": truncated,
    }


def _summarize_user_content(content: str | Sequence[Any] | None) -> dict[str, Any] | None:
    """Summarize the user content that gets replayed back to the model after a tool call."""

    if content is None:
        return None

    if isinstance(content, str):
        return _summarize_payload(content)

    flattened: list[str] = []
    for item in content:
        if isinstance(item, str):
            flattened.append(item)
        elif isinstance(item, dict):
            flattened.append(json.dumps(item, default=str))
        else:
            flattened.append(str(item))

    joined = "\n".join(flattened).strip()
    # Remove trailing newline to avoid false length inflation.
    return _summarize_payload(joined)


@dataclass(slots=True)
class ToolCallRecord:
    """Mutable analytics record for a single tool call."""

    call_id: str
    tool_name: str
    started_ms: float
    args_summary: dict[str, Any] | None

    completed_ms: float | None = None
    result_summary: dict[str, Any] | None = None
    forwarded_summary: dict[str, Any] | None = None

    def mark_complete(
        self,
        *,
        timestamp_ms: float,
        result_summary: dict[str, Any] | None,
        forwarded_summary: dict[str, Any] | None,
    ) -> None:
        self.completed_ms = timestamp_ms
        self.result_summary = result_summary
        self.forwarded_summary = forwarded_summary

    def duration_ms(self) -> float | None:
        if self.completed_ms is None:
            return None
        return max(self.completed_ms - self.started_ms, 0.0)

    def forwarded_all_data(self) -> bool | None:
        if not self.result_summary:
            return None
        if not self.forwarded_summary:
            return False
        result_len = self.result_summary.get("length")
        forwarded_len = self.forwarded_summary.get("length")
        if result_len is None or forwarded_len is None:
            return None
        # Allow a small tolerance for formatting differences.
        if not isinstance(result_len, (int, float)) or not isinstance(forwarded_len, (int, float)):
            return None
        return forwarded_len >= result_len or math.isclose(forwarded_len, result_len, rel_tol=0.05)

    def to_payload(self) -> dict[str, Any]:
        """Serialize into a JSON-ready payload for the front-end."""

        return {
            "call_id": self.call_id,
            "tool_name": self.tool_name,
            "started_ms": self.started_ms,
            "completed_ms": self.completed_ms,
            "duration_ms": self.duration_ms(),
            "args": self.args_summary,
            "result": self.result_summary,
            "forwarded": self.forwarded_summary,
            "forwarded_all_data": self.forwarded_all_data(),
        }


@dataclass(slots=True)
class AnalyticsCollector:
    """Collects timing and tool metadata during a streamed agent run."""

    start_time: float = field(default_factory=time.perf_counter)
    first_token_ms: float | None = None
    final_result_ms: float | None = None
    tool_calls: dict[str, ToolCallRecord] = field(default_factory=dict)
    tool_order: list[str] = field(default_factory=list)

    def record(self, event: AgentStreamEvent, *, now: float | None = None) -> list[dict[str, Any]]:
        """Record the event and return a list of analytics payloads to emit."""

        timestamp = _now_ms(self.start_time, now)
        payloads: list[dict[str, Any]] = []

        if isinstance(event, FunctionToolCallEvent):
            args_summary = _summarize_payload(event.part.args)
            record = ToolCallRecord(
                call_id=event.tool_call_id,
                tool_name=event.part.tool_name,
                started_ms=timestamp,
                args_summary=args_summary,
            )
            self.tool_calls[event.tool_call_id] = record
            self.tool_order.append(event.tool_call_id)
            payloads.append(
                {
                    "type": "tool_call_started",
                    "timestamp_ms": timestamp,
                    "call_id": event.tool_call_id,
                    "tool_name": event.part.tool_name,
                    "args": args_summary,
                }
            )
        elif isinstance(event, FunctionToolResultEvent):
            record = self.tool_calls.get(event.tool_call_id)
            result_summary = None
            if hasattr(event.result, "model_response_str"):
                result_summary = _summarize_payload(event.result.model_response_str())
            forwarded_summary = _summarize_user_content(event.content)
            if record is None:
                record = ToolCallRecord(
                    call_id=event.tool_call_id,
                    tool_name=getattr(event.result, "tool_name", "unknown"),
                    started_ms=timestamp,
                    args_summary=None,
                )
                self.tool_calls[event.tool_call_id] = record
                self.tool_order.append(event.tool_call_id)
            record.mark_complete(
                timestamp_ms=timestamp,
                result_summary=result_summary,
                forwarded_summary=forwarded_summary,
            )
            tool_stats = self._collect_tool_stats()
            coverage_counts = self._coverage_counts()
            payloads.append(
                {
                    "type": "tool_call_completed",
                    "timestamp_ms": timestamp,
                    "call_id": event.tool_call_id,
                    "tool_name": record.tool_name,
                    "duration_ms": record.duration_ms(),
                    "result": result_summary,
                    "forwarded": forwarded_summary,
                    "forwarded_all_data": record.forwarded_all_data(),
                    "tool_stats": tool_stats,
                    "coverage_counts": coverage_counts,
                }
            )
        elif isinstance(event, PartStartEvent) and isinstance(event.part, TextPart):
            if self.first_token_ms is None:
                self.first_token_ms = timestamp
                payloads.append(
                    {
                        "type": "phase",
                        "phase": "model_stream",
                        "status": "started",
                        "timestamp_ms": timestamp,
                    }
                )
        elif isinstance(event, FinalResultEvent):
            self.final_result_ms = timestamp
            payloads.append(
                {
                    "type": "phase",
                    "phase": "model_stream",
                    "status": "finalized",
                    "timestamp_ms": timestamp,
                }
            )

        return payloads

    def summary(self, *, completed_at: float | None = None) -> dict[str, Any]:
        """Return the final summary payload once the run completes."""

        total_ms = _now_ms(self.start_time, completed_at)
        ordered_tools: Iterable[ToolCallRecord] = (
            self.tool_calls[call_id] for call_id in self.tool_order if call_id in self.tool_calls
        )
        coverage_counts = self._coverage_counts()
        return {
            "type": "run_summary",
            "total_duration_ms": total_ms,
            "first_token_ms": self.first_token_ms,
            "final_result_ms": self.final_result_ms,
            "tool_calls": [record.to_payload() for record in ordered_tools],
            "tool_stats": self._collect_tool_stats(),
            "coverage_counts": coverage_counts,
        }

    def _collect_tool_stats(self) -> dict[str, Any]:
        """Summarize tool timing aggregates."""

        durations: list[float] = []
        for record in self.tool_calls.values():
            value = record.duration_ms()
            if value is not None:
                durations.append(value)

        total_calls = len(self.tool_calls)
        completed_calls = len(durations)
        total_ms = sum(durations)
        avg_ms = total_ms / completed_calls if completed_calls else None
        max_ms = max(durations) if durations else None
        coverage_counts = self._coverage_counts()

        return {
            "total_calls": total_calls,
            "completed_calls": completed_calls,
            "total_duration_ms": total_ms if completed_calls else None,
            "average_duration_ms": avg_ms,
            "max_duration_ms": max_ms,
            "full_coverage": coverage_counts["full"],
            "partial_coverage": coverage_counts["partial"],
            "pending": coverage_counts["pending"],
        }

    def _coverage_counts(self) -> dict[str, int]:
        """Return aggregate coverage counts."""

        counts = {"full": 0, "partial": 0, "pending": 0}
        for record in self.tool_calls.values():
            status = record.forwarded_all_data()
            if status is True:
                counts["full"] += 1
            elif status is False:
                counts["partial"] += 1
            else:
                counts["pending"] += 1
        return counts

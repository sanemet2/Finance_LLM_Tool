"""Simple timing logger for the finance orchestrator."""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Final, Protocol

LOG_PATH: Final[Path] = Path(__file__).with_name('timings.jsonl')


@dataclass(slots=True)
class TimingSample:
    """Serializable snapshot of a single agent turn."""

    ts: str
    prompt: str
    prep_ms: float
    model_ms: float
    post_ms: float
    total_ms: float
    tokens_in: int
    tokens_out: int
    tool_ms: float = 0.0  # <-- added
    tool_calls: int = 0  # <-- added
    tool_details: dict[str, Any] | None = None


class UsageSnapshot(Protocol):
    """Minimal token usage contract pulled from pydantic-ai results."""

    input_tokens: int
    output_tokens: int


def utc_timestamp() -> str:
    """Return the current UTC timestamp in ISO-8601 format."""
    return datetime.now(timezone.utc).isoformat()


def _format_seconds(ms_value: float) -> str:
    """Convert milliseconds to a seconds string with two decimals."""
    return f'{ms_value / 1000:.2f} s'


def _format_summary(
    *,
    ts: str,
    prep_ms: float,
    model_ms: float,
    post_ms: float,
    total_ms: float,
    tokens_in: int,
    tokens_out: int,
    tool_ms: float,  # <-- added
    tool_calls: int,  # <-- added
) -> str:
    """Build a human-readable summary for terminal output."""
    return (
        f"[timing @ {ts}] total={_format_seconds(total_ms)} "
        f"(prep={_format_seconds(prep_ms)}, model={_format_seconds(model_ms)}, post={_format_seconds(post_ms)}, "
        f"tool={_format_seconds(tool_ms)}|calls={tool_calls}) "
        f"tokens={tokens_in}->{tokens_out}"
    )


def record(sample: TimingSample) -> None:
    """Append the timing sample to the JSONL log."""
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open('a', encoding='utf-8') as log_file:
        log_file.write(json.dumps(asdict(sample)))
        log_file.write('\n')


def log_timing_sample(
    *,
    prompt: str,
    prep_ms: float,
    model_ms: float,
    post_ms: float,
    total_ms: float,
    tokens_in: int,
    tokens_out: int,
    tool_ms: float = 0.0,  # <-- added
    tool_calls: int = 0,  # <-- added
    tool_details: dict[str, Any] | None = None,
    ts: str | None = None,
) -> None:
    """Construct and persist a timing snapshot for a single run."""
    record(
        TimingSample(
            ts=ts or utc_timestamp(),
            prompt=prompt,
            prep_ms=prep_ms,
            model_ms=model_ms,
            post_ms=post_ms,
            total_ms=total_ms,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            tool_ms=tool_ms,  # <-- added
            tool_calls=tool_calls,  # <-- added
            tool_details=tool_details,
        )
    )


def log_turn_metrics(
    *,
    prompt: str,
    total_start: float,
    prep_end: float,
    model_end: float,
    total_end: float,
    usage: UsageSnapshot,
    tool_ms: float = 0.0,  # <-- added
    tool_calls: int = 0,  # <-- added
    tool_details: dict[str, Any] | None = None,
    ts: str | None = None,
) -> None:
    """Derive timing deltas from perf_counter marks and log them."""
    log_timing_sample(
        prompt=prompt,
        prep_ms=(prep_end - total_start) * 1_000,
        model_ms=(model_end - prep_end) * 1_000,
        post_ms=(total_end - model_end) * 1_000,
        total_ms=(total_end - total_start) * 1_000,
        tokens_in=int(usage.input_tokens),
        tokens_out=int(usage.output_tokens),
        tool_ms=tool_ms,  # <-- added
        tool_calls=tool_calls,  # <-- added
        tool_details=tool_details,
        ts=ts,
    )


@dataclass(slots=True)
class ToolMetrics:
    """Accumulates per-run tool timing data."""

    total_ms: float = 0.0
    total_calls: int = 0
    per_tool_ms: dict[str, float] = field(default_factory=dict)
    per_tool_calls: dict[str, int] = field(default_factory=dict)
    call_sequence: list[str] = field(default_factory=list)

    def record(self, tool_name: str, duration_ms: float) -> None:
        """Register a single tool invocation."""
        self.total_ms += duration_ms
        self.total_calls += 1
        self.per_tool_ms[tool_name] = self.per_tool_ms.get(tool_name, 0.0) + duration_ms
        self.per_tool_calls[tool_name] = self.per_tool_calls.get(tool_name, 0) + 1
        self.call_sequence.append(tool_name)

    def reset(self) -> None:
        """Clear all accumulated metrics."""
        self.total_ms = 0.0
        self.total_calls = 0
        self.per_tool_ms.clear()
        self.per_tool_calls.clear()
        self.call_sequence.clear()


def monitor(poll_interval: float = 0.2) -> None:
    """Continuously stream new timing entries to stdout."""
    LOG_PATH.touch(exist_ok=True)
    with LOG_PATH.open('r', encoding='utf-8') as log_file:
        log_file.seek(0, 2)
        while True:
            line = log_file.readline()
            if not line:
                time.sleep(poll_interval)
                continue

            try:
                data: dict[str, Any] = json.loads(line)
            except json.JSONDecodeError:
                print(f'Invalid JSON line: {line.rstrip()}')
                continue

            summary = _format_summary(
                ts=str(data.get('ts', 'unknown')),
                prep_ms=float(data.get('prep_ms', 0.0)),
                model_ms=float(data.get('model_ms', 0.0)),
                post_ms=float(data.get('post_ms', 0.0)),
                total_ms=float(data.get('total_ms', 0.0)),
                tokens_in=int(data.get('tokens_in', 0)),
                tokens_out=int(data.get('tokens_out', 0)),
                tool_ms=float(data.get('tool_ms', 0.0)),  # <-- added
                tool_calls=int(data.get('tool_calls', 0)),  # <-- added
            )
            print(summary)
            details = data.get('tool_details')
            if isinstance(details, dict) and details.get('sequence'):
                sequence = ', '.join(details['sequence'])
                print(f'    tools sequence: {sequence}')
                per_tool_ms = details.get('per_tool_ms') or {}
                per_tool_calls = details.get('per_tool_calls') or {}
                if per_tool_ms:
                    breakdown = ', '.join(
                        f'{name}={per_tool_ms.get(name, 0):.0f}ms/{per_tool_calls.get(name, 0)}x'
                        for name in per_tool_ms
                    )
                    print(f'    tools summary: {breakdown}')


def main() -> None:
    print(f'Monitoring {LOG_PATH} (Ctrl+C to stop)...')
    try:
        monitor()
    except KeyboardInterrupt:
        print('\nMonitor stopped.')


if __name__ == '__main__':
    main()

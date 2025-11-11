"""Simple timing logger for the finance orchestrator."""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Final

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
) -> str:
    """Build a human-readable summary for terminal output."""
    return (
        f"[timing @ {ts}] total={_format_seconds(total_ms)} "
        f"(prep={_format_seconds(prep_ms)}, model={_format_seconds(model_ms)}, post={_format_seconds(post_ms)}) "
        f"tokens={tokens_in}->{tokens_out}"
    )


def record(sample: TimingSample) -> None:
    """Append the timing sample to the JSONL log."""
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open('a', encoding='utf-8') as log_file:
        log_file.write(json.dumps(asdict(sample)))
        log_file.write('\n')


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

            print(
                _format_summary(
                    ts=str(data.get('ts', 'unknown')),
                    prep_ms=float(data.get('prep_ms', 0.0)),
                    model_ms=float(data.get('model_ms', 0.0)),
                    post_ms=float(data.get('post_ms', 0.0)),
                    total_ms=float(data.get('total_ms', 0.0)),
                    tokens_in=int(data.get('tokens_in', 0)),
                    tokens_out=int(data.get('tokens_out', 0)),
                )
            )


def main() -> None:
    print(f'Monitoring {LOG_PATH} (Ctrl+C to stop)...')
    try:
        monitor()
    except KeyboardInterrupt:
        print('\nMonitor stopped.')


if __name__ == '__main__':
    main()

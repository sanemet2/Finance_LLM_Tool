from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List

import pytest

from ._helpers import ensure_chat_package

ensure_chat_package()

from diagnostics import TraceRecorder

from chat.transcript import Transcript, normalise_content


class StubRegistry:
    def __init__(self) -> None:
        self.calls: List[tuple[str, Any]] = []

    def execute(self, name: str, arguments: Any) -> str:
        self.calls.append((name, arguments))
        return f"result:{name}:{arguments}"


def test_append_tool_results_appends_messages_and_records(capsys):
    transcript = Transcript(system_prompt="system")
    transcript.add_user("hello")

    tool_calls: List[Dict[str, Any]] = [
        {"id": "call-1", "function": {"name": "echo", "arguments": {"value": 1}}},
        {"id": "call-2", "function": {"name": "lookup", "arguments": "payload"}},
    ]

    transcript.add_assistant(content="processing", tool_calls=tool_calls)

    registry = StubRegistry()
    recorder = TraceRecorder()

    collected = []
    transcript.append_tool_results(
        tool_calls,
        registry,
        verbose=True,
        recorder=recorder,
        result_handler=collected.append,
    )

    messages = transcript.messages()
    assert messages[-2] == {
        "role": "tool",
        "name": "echo",
        "tool_call_id": "call-1",
        "content": "result:echo:{'value': 1}",
    }
    assert messages[-1] == {
        "role": "tool",
        "name": "lookup",
        "tool_call_id": "call-2",
        "content": "result:lookup:payload",
    }

    assert registry.calls == [
        ("echo", {"value": 1}),
        ("lookup", "payload"),
    ]

    captured_output = capsys.readouterr()
    assert "[tool:echo] result:echo:{'value': 1}" in captured_output.out
    assert "[tool:lookup] result:lookup:payload" in captured_output.out

    segments = recorder.segments()
    assert [segment.name for segment in segments] == ["tool:echo[1]", "tool:lookup[2]"]
    assert segments[0].metadata == {
        "tool_call_id": "call-1",
        "arguments_chars": len(json.dumps({"value": 1})),
        "result_chars": len(messages[-2]["content"]),
    }
    assert segments[1].metadata == {
        "tool_call_id": "call-2",
        "arguments_chars": len("payload"),
        "result_chars": len(messages[-1]["content"]),
    }

    assert collected == [
        {
            "name": "echo",
            "call_id": "call-1",
            "arguments": {"value": 1},
            "result": "result:echo:{'value': 1}",
        },
        {
            "name": "lookup",
            "call_id": "call-2",
            "arguments": "payload",
            "result": "result:lookup:payload",
        },
    ]


def test_pop_last_removes_latest_message():
    transcript = Transcript()
    assert transcript.pop_last() is None

    transcript.add_user("first")
    transcript.add_assistant(content="second")
    transcript.add_user("third")

    last = transcript.pop_last()
    assert last == {"role": "user", "content": "third"}
    assert transcript.messages()[-1] == {"role": "assistant", "content": "second"}


@pytest.mark.parametrize(
    "input_value,expected",
    [
        ("plain text", "plain text"),
        ({"text": "embedded"}, "embedded"),
        ({"text": {"text": "nested"}}, "nested"),
        ({"text": [{"text": "chunk1"}, {"text": "chunk2"}]}, "chunk1\nchunk2"),
        ({"other": 1}, json.dumps({"other": 1})),
        ([{"text": "part1"}, "part2", 123], "part1\npart2\n123"),
        (None, ""),
        (42, "42"),
    ],
)
def test_normalise_content_handles_varied_payloads(input_value, expected):
    assert normalise_content(input_value) == expected

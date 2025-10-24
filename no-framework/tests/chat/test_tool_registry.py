from __future__ import annotations

import sys
from pathlib import Path
from textwrap import dedent

import pytest

from ._helpers import ensure_chat_package

ensure_chat_package()

from chat.tool_registry import ToolRegistry


@pytest.fixture
def registry(tmp_path):
    tool_dir = tmp_path / "group" / "alpha" / "tool_code"
    tool_dir.mkdir(parents=True)
    module_path = tool_dir / "openrouter_tools.py"
    module_path.write_text(
        dedent(
            """
            CALLS = []
            IMPORT_COUNT = globals().get("IMPORT_COUNT", 0) + 1


            def get_tool_definitions():
                CALLS.append("definitions")
                return [
                    {"name": "echo", "description": "Echo tool"},
                ]


            def execute_tool_call(name, arguments):
                CALLS.append(("execute", name, arguments))
                if name != "echo":
                    raise ValueError("unknown tool")
                return f"executed:{arguments}"
            """
        )
    )

    module_name = f"openrouter_tool_{tool_dir.parent.name}_{tool_dir.name}"
    sys.modules.pop(module_name, None)

    registry = ToolRegistry(tmp_path)

    yield registry

    sys.modules.pop(module_name, None)
    sys.path[:] = [entry for entry in sys.path if entry != str(tool_dir)]


def test_load_discovers_modules_once(registry):
    modules_first = registry.load()
    modules_second = registry.load()

    assert modules_first is modules_second
    module = modules_first[0]
    assert module.IMPORT_COUNT == 1


def test_tool_definitions_cached(registry):
    definitions_first = registry.tool_definitions()
    definitions_first.append({"name": "mutated"})

    definitions_second = registry.tool_definitions()
    assert definitions_second == [{"name": "echo", "description": "Echo tool"}]

    module = registry.load()[0]
    assert module.CALLS.count("definitions") == 1


def test_execute_routes_and_errors(registry):
    result = registry.execute("echo", "payload")
    assert result == "executed:payload"

    with pytest.raises(ValueError) as excinfo:
        registry.execute("unknown", "payload")

    assert "No tool module handled 'unknown'" in str(excinfo.value)
    assert isinstance(excinfo.value.__cause__, ValueError)
    assert str(excinfo.value.__cause__) == "unknown tool"

    module = registry.load()[0]
    assert module.CALLS[-2:] == [
        ("execute", "echo", "payload"),
        ("execute", "unknown", "payload"),
    ]

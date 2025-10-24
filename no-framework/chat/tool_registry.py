"""Dynamic discovery and execution of agent tool modules."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence


class ToolRegistry:
    """Load tool modules from disk and provide their interfaces to the chat loop."""

    def __init__(self, tools_root: Path) -> None:
        self._tools_root = Path(tools_root)
        self._modules: Optional[List[Any]] = None
        self._definitions: Optional[List[Dict[str, Any]]] = None

    # Public API -----------------------------------------------------------------

    def load(self) -> Sequence[Any]:
        """Ensure tool modules are discovered and loaded."""

        if self._modules is None:
            self._modules = self._discover_tool_modules()
        return self._modules

    def tool_definitions(self) -> List[Dict[str, Any]]:
        """Return all tool definitions exposed by the loaded modules."""

        if self._definitions is None:
            modules = self.load()
            self._definitions = self._collect_tool_definitions(modules)
        return list(self._definitions)

    def execute(self, tool_name: str, arguments: str | Mapping[str, Any]) -> str:
        """Execute a tool call using the first module that accepts it."""

        modules = self.load()
        last_error: Optional[Exception] = None
        for module in modules:
            executor = getattr(module, "execute_tool_call", None)
            if callable(executor):
                try:
                    return executor(tool_name, arguments)
                except ValueError as exc:
                    last_error = exc
                    continue
        raise ValueError(f"No tool module handled {tool_name!r}") from last_error

    # Internal helpers -----------------------------------------------------------

    def _discover_tool_modules(self) -> List[Any]:
        modules: List[Any] = []
        if not self._tools_root.exists():
            return modules

        for tool_path in self._tools_root.glob("*/**/tool_code/openrouter_tools.py"):
            tool_dir = tool_path.parent
            sys_path_entry = str(tool_dir)
            if sys_path_entry not in sys.path:
                sys.path.insert(0, sys_path_entry)
            spec = importlib.util.spec_from_file_location(
                f"openrouter_tool_{tool_path.parent.parent.name}_{tool_path.parent.name}",
                tool_path,
            )
            if not spec or not spec.loader:
                continue
            module = importlib.util.module_from_spec(spec)
            sys.modules[spec.name] = module
            spec.loader.exec_module(module)
            modules.append(module)
        return modules

    @staticmethod
    def _collect_tool_definitions(modules: Sequence[Any]) -> List[Dict[str, Any]]:
        definitions: List[Dict[str, Any]] = []
        for module in modules:
            getter = getattr(module, "get_tool_definitions", None)
            if callable(getter):
                definitions.extend(getter())
        return definitions

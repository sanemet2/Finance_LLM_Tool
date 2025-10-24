from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CHAT_DIR = ROOT / "chat"


def ensure_chat_package():
    root_str = str(ROOT)
    if root_str not in sys.path:
        sys.path.insert(0, root_str)

    for name in ("chat", "chat.tool_registry", "chat.transcript"):
        sys.modules.pop(name, None)

    spec = importlib.util.spec_from_file_location(
        "chat",
        CHAT_DIR / "__init__.py",
        submodule_search_locations=[str(CHAT_DIR)],
    )
    if spec is None or spec.loader is None:
        raise ImportError("Unable to load chat package")

    module = importlib.util.module_from_spec(spec)
    sys.modules["chat"] = module
    spec.loader.exec_module(module)
    return module

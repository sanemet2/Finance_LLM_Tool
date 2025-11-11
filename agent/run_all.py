"""Launch the orchestrator and analytics monitor in separate terminals."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PYTHON = sys.executable


def launch(label: str, script: str) -> None:
    """Spawn a new PowerShell window running the given script."""
    subprocess.Popen(
        [
            'powershell',
            '-NoExit',
            '-Command',
            f"Set-Location '{REPO_ROOT}'; {PYTHON} {script}",
        ],
        creationflags=subprocess.CREATE_NEW_CONSOLE,
    )
    print(f'{label} launched.')


def main() -> None:
    launch('Agent', 'agent/Orchestrator_Agent.py')
    launch('Analytics monitor', 'agent/analytics.py')


if __name__ == '__main__':
    main()

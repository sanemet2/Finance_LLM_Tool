from __future__ import annotations

import os
import subprocess
import sys
from tempfile import TemporaryDirectory


def main() -> None:
    code = sys.stdin.read()
    with TemporaryDirectory() as tmp_dir:
        os.chdir(tmp_dir)
        os.environ.clear()
        os.environ['PYTHONIOENCODING'] = 'utf-8'
        proc = subprocess.run(
            [sys.executable, '-c', code],
            capture_output=True,
            text=True,
            timeout=2,
        )
        sys.stdout.write(proc.stdout)
        sys.stderr.write(proc.stderr)


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parent
    spec = root / "openapi.json"
    return subprocess.call(
        [sys.executable, "-m", "openapi_python_client", "generate", "--path", str(spec), "--meta", "none"],
        cwd=root,
    )


if __name__ == "__main__":
    raise SystemExit(main())


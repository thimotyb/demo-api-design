"""Verifica che la demo M01 riproduca gli esiti didattici documentati."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STEP = ROOT / "moduli/m01/step-01-prototipo"


def main() -> int:
    result = subprocess.run(
        [sys.executable, str(STEP / "demo.py")],
        check=True,
        capture_output=True,
        text=True,
        cwd=ROOT,
    )
    observed = json.loads(result.stdout)
    expected = json.loads((STEP / "expected/observations.json").read_text(encoding="utf-8"))
    if observed != expected:
        print("M01: output diverso dal riferimento.\nOsservato:", json.dumps(observed, indent=2))
        return 1
    print("M01: demo riproducibile; caso felice e tre lacune osservati come documentato.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

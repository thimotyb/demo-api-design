"""gRPC example. The generated modules live in gen/ and are not committed.

Run grpc_api/generate.sh (or ./run_all.sh) once after cloning.
"""

import subprocess
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_GEN = _HERE / "gen"

if not (_GEN / "checkout" / "v1" / "checkout_pb2_grpc.py").exists():
    subprocess.run(["bash", str(_HERE / "generate.sh")], check=True, env={"PATH": __import__("os").environ["PATH"]})
if str(_GEN) not in sys.path:
    sys.path.insert(0, str(_GEN))

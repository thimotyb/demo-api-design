import sys
from pathlib import Path

# The tests use the APIs of M01 as they are, without copying them.
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "m01"))

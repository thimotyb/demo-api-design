#!/usr/bin/env bash
# Create a virtual environment, install dependencies and run the tests of the three steps.
set -euo pipefail
cd "$(dirname "$0")"

[ -d .venv ] || python3 -m venv .venv
. .venv/bin/activate
pip install -q -r requirements.txt
python -m pytest -q

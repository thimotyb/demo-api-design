#!/usr/bin/env bash
# Create a virtual environment, install dependencies and run the tests of both versions.
set -euo pipefail
cd "$(dirname "$0")"

[ -d .venv ] || python3 -m venv .venv
. .venv/bin/activate
pip install -q -r requirements.txt

# The two folders both contain a package called "app", so they are tested separately.
(cd orders_api && python -m pytest -q)
(cd orders_api_async && python -m pytest -q && python timing_demo.py)

#!/usr/bin/env bash
# Create a virtual environment, install dependencies and run the tests.
set -euo pipefail
cd "$(dirname "$0")"

if [ ! -d .venv ]; then
  python3 -m venv .venv
fi
. .venv/bin/activate
pip install -q -r requirements.txt

python -m pytest -q

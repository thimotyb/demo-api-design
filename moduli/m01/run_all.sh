#!/usr/bin/env bash
# Create a virtual environment, install dependencies, generate the gRPC code and run every check.
set -euo pipefail
cd "$(dirname "$0")"

if [ ! -d .venv ]; then
  python3 -m venv .venv
fi
. .venv/bin/activate
pip install -q -r requirements.txt
bash grpc_api/generate.sh

python -m pytest -q
echo
python -m compare.measure

#!/usr/bin/env bash
set -euo pipefail

step_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$step_dir"

python3 scripts/generate_postman.py

log_file="$(mktemp)"
./node_modules/.bin/prism mock openapi/checkout-api.yaml --host 127.0.0.1 --port 4010 >"$log_file" 2>&1 &
prism_pid=$!
cleanup() {
  kill "$prism_pid" 2>/dev/null || true
  wait "$prism_pid" 2>/dev/null || true
  rm -f "$log_file"
}
trap cleanup EXIT INT TERM

ready=0
for _ in $(seq 1 40); do
  status="$(curl --silent --output /dev/null --write-out '%{http_code}' \
    --header 'Authorization: Bearer m05-demo-token' \
    --header 'Prefer: code=200, example=orderWithShipment, dynamic=false' \
    http://127.0.0.1:4010/orders/bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb || true)"
  if [[ "$status" == "200" ]]; then
    ready=1
    break
  fi
  if ! kill -0 "$prism_pid" 2>/dev/null; then
    cat "$log_file"
    exit 1
  fi
  sleep 0.5
done

if [[ "$ready" != "1" ]]; then
  cat "$log_file"
  echo "Prism non è pronto su http://127.0.0.1:4010" >&2
  exit 1
fi

./node_modules/.bin/newman run postman/checkout-sequence-playbooks.postman_collection.json \
  --env-var baseUrl=http://127.0.0.1:4010

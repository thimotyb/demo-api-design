#!/usr/bin/env bash
# Start the API, run the Locust load test for a few seconds without a web UI, and stop the API.
# With WEB=1 the Locust web console is used instead (see below).
# Needs the virtual environment of ../run_all.sh. Numbers depend on the machine: compare the two
# rows with each other, do not read them as the capacity of any real API.
set -euo pipefail
cd "$(dirname "$0")/.."
. .venv/bin/activate

PORT=${PORT:-8020}
USERS=${USERS:-20}
DURATION=${DURATION:-10s}

uvicorn app.main:app --port "$PORT" --log-level warning &
SERVER=$!
trap 'kill $SERVER' EXIT
sleep 2

# WEB=1 opens the Locust web console instead of a fixed run: choose users and spawn rate there,
# press Start, and watch requests, failures and percentiles live. Stop with Ctrl+C.
if [ "${WEB:-0}" = "1" ]; then
  WEB_PORT=${WEB_PORT:-8089}
  echo "Open http://localhost:$WEB_PORT"
  locust -f loadtest/locustfile.py --host "http://127.0.0.1:$PORT" --web-port "$WEB_PORT"
  exit 0
fi

OUT=$(mktemp -d)
locust -f loadtest/locustfile.py --headless --host "http://127.0.0.1:$PORT" \
  -u "$USERS" -r "$USERS" -t "$DURATION" --only-summary --csv "$OUT/stats" 2>&1 | grep -v "locust.main\|locust.runners"

# The summary has no body size: read it from the CSV that Locust wrote.
python - "$OUT/stats_stats.csv" <<'PY'
import csv, sys
print("\nBody size per request")
for row in csv.DictReader(open(sys.argv[1])):
    if row["Name"] != "Aggregated":
        print(f"{row['Name']:<18}{float(row['Average Content Size']):7.1f} bytes on average")
PY

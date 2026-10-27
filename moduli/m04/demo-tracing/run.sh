#!/usr/bin/env bash
# Start Jaeger in Docker, then the REST and GraphQL APIs of M01 with OpenTelemetry auto-instrumentation.
# The code of M01 is not changed: `opentelemetry-instrument` adds the spans from outside.
set -euo pipefail
cd "$(dirname "$0")"
M01=../../m01
REST_PORT=${REST_PORT:-8000}
GRAPHQL_PORT=${GRAPHQL_PORT:-8001}

docker compose up -d

if [ ! -d "$M01/.venv" ]; then
  python3 -m venv "$M01/.venv"
fi
. "$M01/.venv/bin/activate"
pip install -q -r "$M01/requirements.txt" -r requirements.txt

export OTEL_TRACES_EXPORTER=otlp
export OTEL_EXPORTER_OTLP_PROTOCOL=http/protobuf
export OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318
export OTEL_METRICS_EXPORTER=none
export OTEL_LOGS_EXPORTER=none
# Adds trace_id and span_id to the records of the standard logging module.
export OTEL_PYTHON_LOG_CORRELATION=true

# The GraphQL API reaches the REST API through this address.
export REST_API_URL=http://127.0.0.1:$REST_PORT

cd "$M01"
trap 'kill 0' EXIT
OTEL_SERVICE_NAME=checkout-rest opentelemetry-instrument uvicorn rest_api.app:app --port "$REST_PORT" &
OTEL_SERVICE_NAME=checkout-graphql opentelemetry-instrument uvicorn graphql_api.app:app --port "$GRAPHQL_PORT" &
echo "REST: http://127.0.0.1:$REST_PORT/docs   GraphQL: http://127.0.0.1:$GRAPHQL_PORT/graphql   Jaeger: http://localhost:16686"
wait

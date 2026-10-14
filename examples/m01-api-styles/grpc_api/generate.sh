#!/usr/bin/env bash
# Generate the Python gRPC code from the .proto contract into grpc_api/gen/.
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p grpc_api/gen
python -m grpc_tools.protoc -I grpc_api/proto \
  --python_out=grpc_api/gen --pyi_out=grpc_api/gen --grpc_python_out=grpc_api/gen \
  grpc_api/proto/checkout/v1/checkout.proto
echo "generated grpc_api/gen/checkout/v1/"

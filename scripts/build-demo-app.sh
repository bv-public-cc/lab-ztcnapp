#!/usr/bin/env bash
set -euo pipefail

REGISTRY="${REGISTRY:-REGISTRY_IP:5000}"

docker build -t "${REGISTRY}/otel-demo-app:0.1" demo/otel-demo-app
docker push "${REGISTRY}/otel-demo-app:0.1"

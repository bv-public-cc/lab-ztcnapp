#!/usr/bin/env bash
set -euo pipefail

REGISTRY="${REGISTRY:-REGISTRY_IP:5000}"

echo "Building images for registry: ${REGISTRY}"

docker build -t "${REGISTRY}/zta-pe:0.1" -f zta/policy-engine/Dockerfile zta/policy-engine
docker build -t "${REGISTRY}/zta-pa:0.3" -f zta/policy-admin/Dockerfile zta/policy-admin
docker build -t "${REGISTRY}/k8s-signal-ingestor:0.1" -f telemetry/k8s-signal-ingestor/Dockerfile telemetry/k8s-signal-ingestor
docker build -t "${REGISTRY}/aws-signal-gen:0.2" -f telemetry/aws-signal-generator/Dockerfile telemetry/aws-signal-generator
docker build -t "${REGISTRY}/obs-signal-ingestor:0.1" -f telemetry/obs-signal-ingestor/Dockerfile telemetry/obs-signal-ingestor

echo "Pushing..."
docker push "${REGISTRY}/zta-pe:0.1"
docker push "${REGISTRY}/zta-pa:0.3"
docker push "${REGISTRY}/k8s-signal-ingestor:0.1"
docker push "${REGISTRY}/aws-signal-gen:0.2"
docker push "${REGISTRY}/obs-signal-ingestor:0.1"

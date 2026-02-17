#!/usr/bin/env bash
set -euo pipefail
kubectl apply -f platform/kubernetes/namespaces.yaml
kubectl apply -f zta/crds/ztasignals.yaml
kubectl apply -f zta/crds/ztadecisions.yaml
kubectl apply -f zta/policy-engine/k8s/
kubectl apply -f zta/policy-admin/k8s/
kubectl apply -f telemetry/k8s-signal-ingestor/k8s/
kubectl apply -f telemetry/aws-signal-generator/k8s/
kubectl apply -f platform/kubernetes/telemetry/otel-collector/
kubectl apply -f platform/kubernetes/telemetry/tempo/
kubectl apply -f platform/kubernetes/network/quarantine/prod-quarantine-labelpolicies.yaml
kubectl apply -f platform/kubernetes/policies/kyverno/cluster/
kubectl apply -f platform/kubernetes/policies/kyverno/namespaced/

# Optional (GitOps): install Kyverno via Argo CD
# kubectl apply -f gitops/argocd/app-kyverno.yaml
kubectl apply -f telemetry/obs-signal-ingestor/k8s/
kubectl apply -f platform/kubernetes/telemetry/loki/
kubectl apply -f platform/kubernetes/telemetry/prometheus/
kubectl apply -f telemetry/observability-signal-ingestor/k8s/

# Optional (GitOps): kube-state-metrics for restart metrics
# kubectl apply -f gitops/argocd/app-kube-state-metrics.yaml

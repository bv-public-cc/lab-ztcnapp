# Kyverno (GitOps install)

This folder provides a GitOps-managed Kyverno install using Argo CD + Helm chart.

## What you get
- `values.yaml` tuned for a lab environment
- Kyverno installed into `kyverno` namespace
- PolicyReports enabled so the `k8s-signal-ingestor` can watch and emit ZTASignals

## How Argo installs it
Apply Argo Application:
```bash
kubectl apply -f gitops/argocd/app-kyverno.yaml
```

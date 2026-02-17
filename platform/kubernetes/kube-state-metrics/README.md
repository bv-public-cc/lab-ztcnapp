# kube-state-metrics (GitOps install)

kube-state-metrics provides Kubernetes object metrics (pod restarts, deployment replicas, etc.)
which improves the Prometheus-based rules used by the observability-signal-ingestor.

This repo installs it using Argo CD + Helm chart.

Apply:
```bash
kubectl apply -f gitops/argocd/app-kube-state-metrics.yaml
```

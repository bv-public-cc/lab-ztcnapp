# Kyverno Baseline Policy Pack (triggers PolicyReports)

These policies are designed to **generate PolicyReports** (and therefore ZTASignals) when workloads violate
baseline constraints.

## Prereqs
- Kyverno installed in the cluster
- PolicyReports enabled (Kyverno produces `PolicyReport`/`ClusterPolicyReport` CRs)

## Apply
```bash
kubectl apply -f platform/kubernetes/policies/kyverno/cluster/
kubectl apply -f platform/kubernetes/policies/kyverno/namespaced/
```

## Trigger test signals quickly
Apply the intentionally bad pod in `tests/` to generate violations:
```bash
kubectl apply -f platform/kubernetes/policies/kyverno/tests/bad-pod-privileged.yaml
kubectl apply -f platform/kubernetes/policies/kyverno/tests/bad-pod-hostpath.yaml
```

Then verify:
```bash
kubectl get policyreports -A | head
kubectl get ztasignals | grep k8s-kyverno
kubectl get ztadecisions | tail
```

## Notes
- These are baseline research policies; tune to your environment.
- For signature verification (cosign), see the placeholder policy in `cluster/verify-image-signature-placeholder.yaml`.

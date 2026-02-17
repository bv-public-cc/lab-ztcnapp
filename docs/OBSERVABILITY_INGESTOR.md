# Observability → ZTASignal Ingestor (Prometheus + Loki + Tempo)

This component closes the “automatic continuous evaluation” loop by turning **observability data**
into normalized `ZTASignal` inputs for the Policy Engine.

It is designed to demonstrate:
- CNAPP runtime detections (anomalies, errors, instability)
- ZTA continuous evaluation (telemetry → PE → PA → PEP)
- Repeatable, open-source implementation (K3s + OTel + Prometheus + Loki + Tempo)

---

## Architecture (data flow)
1) Workloads emit telemetry via OpenTelemetry (OTLP).
2) `otel-collector` receives OTLP and:
   - exports **logs** to Loki
   - exposes **metrics** at `/metrics` (Prometheus scrape)
   - exports **traces** to Tempo
3) `observability-signal-ingestor` periodically queries:
   - Prometheus HTTP API (`/api/v1/query`)
   - Loki query API (`/loki/api/v1/query`)
   - Tempo search API (`/api/search`, best-effort)
4) When a rule exceeds threshold, ingestor upserts a `ZTASignal`.
5) PE upserts a stable `ZTADecision` per asset.
6) PA enforces to K8s/VM/AWS PEPs and writes evidence to decision status.

---

## What you get in this repo
### Telemetry stores
- Loki: `platform/kubernetes/telemetry/loki/`
- Prometheus: `platform/kubernetes/telemetry/prometheus/`
- Tempo: `platform/kubernetes/telemetry/tempo/`

### Ingestor
- `telemetry/observability-signal-ingestor/`
  - `k8s/configmap.yaml` contains tunable rules and thresholds
  - `src/main.py` runs a loop every `intervalSeconds`
  - upserts `ZTASignal` with IR/VR/RR/ER tuned to “runtime anomaly” semantics

---

## Default rules (ConfigMap: obs_rules.yaml)
1) **Runtime error rate** (Prometheus)
- PromQL default:
  `sum(rate(http_server_duration_count{status_code=~"5.."}[5m])) by (k8s_namespace_name,k8s_deployment_name)`
- Threshold: `0.1`

> If you don’t have `http_server_duration_count`, swap this for a metric you do have.
> The ingestor is intentionally “query-driven” so you can adapt the model without code changes.

2) **Pod restart burst** (Prometheus)
- Requires kube-state-metrics or equivalent.
- PromQL:
  `sum(increase(kube_pod_container_status_restarts_total[5m])) by (namespace,pod)`
- Threshold: `1`

3) **Error logs burst** (Loki)
- LogQL:
  `{k8s_namespace_name="prod"} |= "error"`
- Threshold: `10` (counts returned streams as a proxy for burstiness)

4) **Error traces burst** (Tempo, best-effort)
- Query:
  `service.name="otel-demo-app" status=error`
- Threshold: `5`

---

## Build + deploy
### Build/push image
```bash
REGISTRY=REGISTRY_IP:5000
docker build -t ${REGISTRY}/obs-signal-ingestor:0.1 -f telemetry/observability-signal-ingestor/Dockerfile telemetry/observability-signal-ingestor
docker push ${REGISTRY}/obs-signal-ingestor:0.1
```

### Apply manifests
```bash
kubectl apply -f platform/kubernetes/telemetry/loki/
kubectl apply -f platform/kubernetes/telemetry/prometheus/
kubectl apply -f telemetry/observability-signal-ingestor/k8s/
```

Or GitOps:
- add the already listed in `gitops/zta-system-bundle/kustomization.yaml`

---

## Verify end-to-end
### 1) Confirm telemetry stores are up
```bash
kubectl -n telemetry get pods
kubectl -n telemetry get svc loki prometheus tempo otel-collector
```

### 2) Generate traces
Deploy the demo app and run traffic:
```bash
kubectl apply -f demo/otel-demo-app/k8s/deployment.yaml
kubectl apply -f demo/otel-demo-app/k8s/service.yaml
kubectl apply -f demo/otel-demo-app/k8s/traffic-job.yaml
```

### 3) Check signals + decisions
```bash
kubectl get ztasignals | head
kubectl get ztadecisions | head
kubectl get ztadecisions -o yaml | sed -n '1,200p'
```

### 4) Confirm enforcement (example)
If a decision labels a deployment `zta/quarantine=true`, the label-based NetworkPolicy in `prod` will cut traffic.
```bash
kubectl -n prod get deploy -o wide
kubectl -n prod get netpol
```

---

## Defensibility

- This pattern makes a clean “CNAPP→ZTA” research artifact:
  - CNAPP runtime detections are represented as queries over observability stores
  - ZTA decisioning is a deterministic trust algorithm
  - Enforcement is observable and reproducible (labels, nftables rulesets, SG changes)
- You can cite NIST 800-207’s continuous evaluation loop and show it with tangible resources (CRDs + decisions + evidence).

## Latency p95 degradation rule + evidence snippets
The ingestor supports a p95 latency rule using histogram buckets. It also attaches small evidence
snippets (truncated JSON) in the `observations` field to show provenance:
- the exact PromQL/LogQL/Tempo query used
- a bounded excerpt of the query response

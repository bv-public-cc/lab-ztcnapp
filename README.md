# CNAPP ↔ Zero Trust (800-207) Hybrid Lab 

Learning and research project to integrate **CNAPP capability domains** with **NIST SP 800-207 Zero Trust Architecture** in a hybrid environment.


## ZTA and CNAPP Mapping Purpose

The most important file in this projcet is:

```
docs/CNAPP_Taxonomy_ZTA.xlsx
```
This workbook contains the taxonomy, alignment logic, and scoring model.  During schoolwork, and trying to understand implementations of CNAPP with Zero Trust Architectures (ZTA), a search was done to find formal mappings.  It seems to be something that is missing that formally ties CNAPP capabilities to the a regulated ZTA framework that could be auditable by a governance body.  

So, in a vain attempt, this workbook is a formal mapping of CNAPP capabilities to specific NIST SP 800-207 constructs in a way that can be used for quantitative analysis and scoring.

It defines seven CNAPP capability domains and maps each capability to:

  - A primary Zero Trust tenet
  - A Zero Trust component (Policy Engine, Policy Administrator, Policy Enforcement Point)
  - An enforcement decision type (Prevent, Detect, Contain, Recover, Remediate)
  - The target environment (Kubernetes, VM, AWS)
  - A Trust Signal category (Identity, Vulnerability, Runtime, Exposure)
  - Supporting notes and rationale

The Trust Signal category defined in the workbook directly maps to the normalized `ZTASignal` objects used by the lab’s Trust Algorithm.

The workbook models the theory and scoring logic.

This repository implements that logic in a working system, though it is still heavily a work in progress.

This lab is not meant to be a full CNAPP implementation, but rather a reference architecture that demonstrates how CNAPP capabilities can be systematically evaluated and operationalized within a Zero Trust framework.

Mainly it is meant to be a personal learning project (which I hope to turn into my SANS MSISE project), and is not designed to replace commercial CNAPP platforms, but to help understand the mapping and how to operationalize it in a transparent, measurable way.

---

## Trust Algorithm, Trust Score, and Decision

The Trust Score in this lab is a weighted scoring model that translates CNAPP-derived signals into enforceable Zero Trust decisions.

Each `ZTASignal` contains normalized risk dimensions:

  - IR — Identity Risk
  - VR — Vulnerability Risk
  - RR — Runtime Risk
  - ER — Exposure Risk

The Policy Engine computes a composite score using configurable weights defined in:

```
zta/policy-engine/config/weights.yaml
zta/policy-engine/k8s/configmap.yaml
```

The resulting Trust Score is evaluated against defined thresholds to determine:

  - ALLOW
  - RESTRICT
  - QUARANTINE
  - ISOLATE

The Excel workbook includes simulation worksheets that demonstrate how changes in risk inputs affect trust and enforcement outcomes. In the lab, this logic is implemented by the Policy Engine controller in `zta/policy-engine/`.


### Core loop (800-207)
**Telemetry → PE → PA → PEP**
- Telemetry sources create normalized `ZTASignal` objects.
- PE computes Trust Score and emits `ZTADecision` objects.
- PA enforces actions across PEPs (K8s labels/NetworkPolicy, VM nftables, AWS SG lockdown) and writes evidence.


- **K3s (3-node)** runs: Policy Engine (PE), Policy Admin (PA), signal ingestors, telemetry stack.
- **Rocky Linux VMs** are enforceable targets (via SSH + Ansible + nftables).
- **AWS (optional)** provides control-plane telemetry and enforceable PEPs (Security Groups).


## Components
- `zta/crds`: CRDs for `ZTASignal` and `ZTADecision`
- `zta/policy-engine`: PE watcher + trust scoring model
- `zta/policy-admin`: PA decision watcher + enforcement (K8s/VM/AWS) + verification + cooldown/dedup
- `telemetry/k8s-signal-ingestor`: Kyverno PolicyReport → ZTASignal (automatic)
- `telemetry/aws-signal-generator`: AWS drift/overprivilege → ZTASignal (automatic polling; can evolve to EventBridge)
- `platform/kubernetes/telemetry`: OpenTelemetry Collector + Tempo
- `platform/kubernetes/network`: label-based quarantine/restrict NetworkPolicies
- `gitops/argocd`: AppProject + Applications
- `gitops/zta-system-bundle`: Kustomize bundle for ArgoCD to sync ZTA system components

## Quick start 
1) Prepare namespaces:
```bash
kubectl apply -f platform/kubernetes/namespaces.yaml
```

2) Install ArgoCD:
```bash
kubectl create ns argocd
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml
```

3) Apply CRDs + ZTA system manually (or use Argo CD bundle):
```bash
kubectl apply -f zta/crds/ztasignals.yaml
kubectl apply -f zta/crds/ztadecisions.yaml
kubectl apply -f zta/policy-engine/k8s/
kubectl apply -f zta/policy-admin/k8s/
kubectl apply -f telemetry/k8s-signal-ingestor/k8s/
kubectl apply -f telemetry/aws-signal-generator/k8s/
```

4) Deploy telemetry stack:
```bash
kubectl apply -f platform/kubernetes/telemetry/otel-collector/
kubectl apply -f platform/kubernetes/telemetry/tempo/
```

5) Deploy quarantine/restrict label NetworkPolicies (example in `prod`):
```bash
kubectl apply -f platform/kubernetes/network/quarantine/prod-quarantine-labelpolicies.yaml
```

## Placeholders you must set
- Replace `REGISTRY_IP:5000` in k8s deployments with your registry endpoint.
- Replace `https://YOUR_GIT_URL/...` in ArgoCD Applications with your repo URL.
- Create secrets:
  - `pa-ssh-key` in `zta-system` containing `id_ed25519` for VM control
  - `pa-known-hosts` ConfigMap containing pinned `known_hosts`
  - `aws-creds` secret in `zta-system` for AWS polling + remediation (optional)

## Safety note
The AWS SG “lockdown” action revokes public ingress on sensitive ports. Run only in test accounts/VPCs.

---
If you want, add a `docs/` folder with screenshots (Grafana Tempo datasource, Argo sync status, decision evidence) for committee-ready artifacts.

## Ops glue (required secrets/config)
Apply the templates after you fill in values:
- `platform/kubernetes/ops/pa-ssh-key-secret-template.yaml`
- `platform/kubernetes/ops/pa-known-hosts-configmap-template.yaml`
- `platform/kubernetes/ops/aws-creds-secret-template.yaml` (optional)

See `docs/OPS_GLUE.md`.

## Demo trace generator app
Build/push:
```bash
REGISTRY=REGISTRY_IP:5000 ./scripts/build-demo-app.sh
```
Deploy + generate traffic:
```bash
kubectl apply -f demo/otel-demo-app/k8s/deployment.yaml
kubectl apply -f demo/otel-demo-app/k8s/service.yaml
kubectl apply -f demo/otel-demo-app/k8s/traffic-job.yaml
```

## Kyverno baseline policy pack (for automatic signals)
Policies live in `platform/kubernetes/policies/kyverno/`.

Apply:
```bash
kubectl apply -f platform/kubernetes/policies/kyverno/cluster/
kubectl apply -f platform/kubernetes/policies/kyverno/namespaced/
```

Trigger quick violations:
```bash
kubectl apply -f platform/kubernetes/policies/kyverno/tests/bad-pod-privileged.yaml
kubectl apply -f platform/kubernetes/policies/kyverno/tests/bad-pod-hostpath.yaml
```

## Kyverno installation (GitOps)
If you want Kyverno GitOps-managed end-to-end, apply:
```bash
kubectl apply -f gitops/argocd/app-kyverno.yaml
```
Values (for documentation/pinning) live in `platform/kubernetes/kyverno/values.yaml`.

## Stable decisions + hysteresis + controller-level enforcement
- PE now upserts a **single decision per asset** (stable name), applying hysteresis + cooldown.
- PA resolves Pod ownerReferences and enforces at Deployment level when possible.
- See `docs/DECISION_MODEL.md`.

## Observability Signal Ingestor (Prometheus/Loki/Tempo -> ZTASignal)
This makes runtime telemetry feed the Trust Algorithm 

- Code: `telemetry/obs-signal-ingestor/`
- K8s: `telemetry/obs-signal-ingestor/k8s/`

Build/push:
```bash
REGISTRY=REGISTRY_IP:5000 ./scripts/build-images.sh
```

Configure PromQL/LogQL rules:
- `telemetry/obs-signal-ingestor/k8s/configmap.yaml`

Deploy (manual):
```bash
kubectl apply -f telemetry/obs-signal-ingestor/k8s/
```

## Observability → ZTASignal ingestor (Prometheus + Loki + Tempo)
Turns runtime observability into normalized ZTA signals:
- Deploys Loki + Prometheus (Tempo already included)
- Adds `telemetry/observability-signal-ingestor/` which queries Prom/Loki/Tempo on a schedule
- Upserts `ZTASignal` objects when thresholds are exceeded, feeding the PE trust algorithm automatically

See `docs/OBSERVABILITY_INGESTOR.md` for rule tuning + verification steps.

## kube-state-metrics (recommended for richer Prometheus rules)
Install via Argo CD (GitOps):
```bash
kubectl apply -f gitops/argocd/app-kube-state-metrics.yaml
```
Values (for documentation/pinning) live in `platform/kubernetes/kube-state-metrics/values.yaml`.

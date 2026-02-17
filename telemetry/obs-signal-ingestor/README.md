# Observability Signal Ingestor (Prometheus + Loki + optional Tempo)

Purpose: automatically convert **runtime/ops telemetry** into `ZTASignal` objects so the Trust Algorithm is driven by
real operational evidence (not manual injection).

## What it does (today)
- Runs as a CronJob every 2 minutes
- Evaluates configured PromQL and LogQL rules
- If a rule's computed value exceeds threshold, it emits/updates a `ZTASignal`
- Optionally emits a Tempo health signal if Tempo isn't ready

## Configure
Edit:
- `telemetry/obs-signal-ingestor/k8s/configmap.yaml`

Update URLs and queries to match your stack and what you want to treat as risk.

## Typical research mappings
- Log anomaly spikes -> Runtime Risk (RR)
- 5xx rate / latency SLO breach -> Runtime Risk (RR) + Enforcement Risk (ER) (depends how aggressive you enforce)
- CPU/mem saturation -> RR (availability) and possibly ER if you're going to quarantine

## Future extensions (easy)
- Tempo span error-rate extraction -> RR
- Prometheus Alertmanager webhook -> direct `ZTASignal` creation
- K8s audit events -> Identity Risk (IR)

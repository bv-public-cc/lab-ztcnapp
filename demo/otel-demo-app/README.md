# OTel Demo App (traces generator)

This is a minimal Flask service instrumented with OpenTelemetry that exports traces to the in-cluster OTel Collector.

## Build & push
```bash
REGISTRY=REGISTRY_IP:5000
docker build -t ${REGISTRY}/otel-demo-app:0.1 demo/otel-demo-app
docker push ${REGISTRY}/otel-demo-app:0.1
```

## Deploy
```bash
kubectl apply -f demo/otel-demo-app/k8s/deployment.yaml
kubectl apply -f demo/otel-demo-app/k8s/service.yaml
```

## Generate traffic
```bash
kubectl apply -f demo/otel-demo-app/k8s/traffic-job.yaml
```

## Verify traces
- Grafana → Tempo datasource → Search traces (service `otel-demo-app`)
- Or port-forward Tempo:
```bash
kubectl -n telemetry port-forward svc/tempo 3200:3200
curl -s http://localhost:3200/ready && echo
```

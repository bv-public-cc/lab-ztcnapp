from __future__ import annotations
import os, time, yaml, json
from typing import Dict, Any, List
from kubernetes import client, config

from clients import PromClient, LokiClient, TempoClient
from rules import (
    parse_prom_vector,
    prom_error_rate_findings,
    prom_restart_findings,
    loki_errorlog_findings,
    tempo_errortrace_findings,
)
from signal_writer import upsert_signal, stable_name

def load_cfg(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}

def count_loki_streams(resp: Dict[str, Any]) -> int:
    try:
        result = (resp.get("data", {}) or {}).get("result", []) or []
        return len(result)
    except Exception:
        return 0

def count_tempo_traces(resp: Dict[str, Any]) -> int:
    try:
        data = resp.get("data", {}) or {}
        traces = data.get("traces", []) or data.get("result", []) or []
        return len(traces)
    except Exception:
        return 0

def evidence_json(resp: Dict[str, Any], max_chars: int = 500) -> str:
    try:
        s = json.dumps(resp, separators=(",", ":"), ensure_ascii=True)
        return s[:max_chars] + ("..." if len(s) > max_chars else "")
    except Exception:
        return ""

def prom_latency_findings(vec, threshold_ms: float) -> List[dict]:
    findings = []
    for labels, val in vec:
        # val assumed in seconds; convert to ms
        ms = float(val) * 1000.0
        if ms < threshold_ms:
            continue
        ns = labels.get("k8s_namespace_name") or labels.get("namespace") or "unknown"
        dep = labels.get("k8s_deployment_name") or labels.get("deployment") or ""
        assetType = "k8s_deploy" if dep else "k8s_ns"
        assetId = f"{ns}/{dep}" if dep else ns
        findings.append({
            "assetType": assetType,
            "assetId": assetId,
            # latency spikes are typically a runtime reliability risk with moderate enforcement relevance
            "IR": 1, "VR": 2, "RR": 6, "ER": 3,
            "confidence": 0.7,
            "observations": [
                f"prom: p95_latency_ms={ms:.1f} (threshold_ms={threshold_ms})",
                f"labels={labels}",
                "signal=latency_p95_degradation",
            ]
        })
    return findings

def main():
    config.load_incluster_config()
    co = client.CustomObjectsApi()

    cfg_path = os.environ.get("CFG_PATH", "/config/obs_rules.yaml")
    cfg = load_cfg(cfg_path)

    prom = PromClient(cfg.get("prometheus", {}).get("url", "http://prometheus.telemetry.svc.cluster.local:9090"))
    loki = LokiClient(cfg.get("loki", {}).get("url", "http://loki.telemetry.svc.cluster.local:3100"))
    tempo = TempoClient(cfg.get("tempo", {}).get("url", "http://tempo.telemetry.svc.cluster.local:3200"))

    interval = int(cfg.get("intervalSeconds", 60))
    print(f"observability-signal-ingestor: interval={interval}s cfg={cfg_path}")

    while True:
        try:
            rules = (cfg.get("rules", {}) or {})

            # 1) Runtime error rate (Prometheus)
            er_cfg = rules.get("error_rate", {}) or {}
            if er_cfg.get("enabled", True):
                q = er_cfg.get("promql", 'sum(rate(http_server_duration_count{status_code=~"5.."}[5m])) by (k8s_namespace_name,k8s_deployment_name)')
                th = float(er_cfg.get("threshold", 0.1))
                resp = prom.query(q)
                vec = parse_prom_vector(resp, ["k8s_namespace_name","k8s_deployment_name","namespace","deployment"])
                ev = evidence_json(resp, max_chars=int(er_cfg.get("evidenceMaxChars", 450)))
                for f in prom_error_rate_findings(vec, th):
                    name = stable_name("obs-prom", f"{f.assetType}|{f.assetId}|error_rate")
                    upsert_signal(co, name, {
                        "assetId": f.assetId,
                        "assetType": f.assetType,
                        "IR": f.IR, "VR": f.VR, "RR": f.RR, "ER": f.ER,
                        "confidence": f.confidence,
                        "observations": [*f.observations, f"promql={q[:160]}", f"evidence={ev}"]
                    })

            # 2) Pod restart burst (Prometheus / kube-state-metrics)
            pr_cfg = rules.get("pod_restarts", {}) or {}
            if pr_cfg.get("enabled", True):
                q = pr_cfg.get("promql", 'sum(increase(kube_pod_container_status_restarts_total[5m])) by (namespace,pod)')
                th = float(pr_cfg.get("threshold", 1.0))
                resp = prom.query(q)
                vec = parse_prom_vector(resp, ["namespace","pod"])
                ev = evidence_json(resp, max_chars=int(pr_cfg.get("evidenceMaxChars", 450)))
                for f in prom_restart_findings(vec, th):
                    name = stable_name("obs-prom", f"{f.assetType}|{f.assetId}|pod_restarts")
                    upsert_signal(co, name, {
                        "assetId": f.assetId,
                        "assetType": f.assetType,
                        "IR": f.IR, "VR": f.VR, "RR": f.RR, "ER": f.ER,
                        "confidence": f.confidence,
                        "observations": [*f.observations, f"promql={q[:160]}", f"evidence={ev}"]
                    })

            # 3) Latency p95 degradation (Prometheus)
            lat_cfg = rules.get("latency_p95", {}) or {}
            if lat_cfg.get("enabled", True):
                q = lat_cfg.get("promql", 'histogram_quantile(0.95, sum(rate(http_server_duration_bucket[5m])) by (le,k8s_namespace_name,k8s_deployment_name))')
                th_ms = float(lat_cfg.get("threshold_ms", 250.0))
                resp = prom.query(q)
                vec = parse_prom_vector(resp, ["k8s_namespace_name","k8s_deployment_name","namespace","deployment"])
                ev = evidence_json(resp, max_chars=int(lat_cfg.get("evidenceMaxChars", 450)))
                for f in prom_latency_findings(vec, th_ms):
                    name = stable_name("obs-prom", f"{f['assetType']}|{f['assetId']}|latency_p95")
                    upsert_signal(co, name, {
                        "assetId": f["assetId"],
                        "assetType": f["assetType"],
                        "IR": f["IR"], "VR": f["VR"], "RR": f["RR"], "ER": f["ER"],
                        "confidence": f["confidence"],
                        "observations": [*f["observations"], f"promql={q[:160]}", f"evidence={ev}"]
                    })

            # 4) Loki log error burst
            le_cfg = rules.get("log_errors", {}) or {}
            if le_cfg.get("enabled", True):
                logql = le_cfg.get("logql", '{k8s_namespace_name="prod"} |= "error"')
                th = int(le_cfg.get("threshold", 10))
                assetType = le_cfg.get("assetType", "k8s_ns")
                assetId = le_cfg.get("assetId", "prod")
                resp = loki.query(logql, limit=int(le_cfg.get("limit", 200)))
                c = count_loki_streams(resp)
                ev = evidence_json(resp, max_chars=int(le_cfg.get("evidenceMaxChars", 450)))
                f = loki_errorlog_findings(c, th, assetType, assetId)
                if f:
                    name = stable_name("obs-loki", f"{assetType}|{assetId}|log_errors")
                    upsert_signal(co, name, {
                        "assetId": f.assetId,
                        "assetType": f.assetType,
                        "IR": f.IR, "VR": f.VR, "RR": f.RR, "ER": f.ER,
                        "confidence": f.confidence,
                        "observations": [*f.observations, f"logql={logql[:160]}", f"evidence={ev}"]
                    })

            # 5) Tempo error traces burst (best-effort)
            te_cfg = rules.get("trace_errors", {}) or {}
            if te_cfg.get("enabled", True):
                q = te_cfg.get("query", 'service.name="otel-demo-app" status=error')
                th = int(te_cfg.get("threshold", 5))
                assetType = te_cfg.get("assetType", "k8s_deploy")
                assetId = te_cfg.get("assetId", "prod/otel-demo-app")
                resp = tempo.search(q, limit=int(te_cfg.get("limit", 50)))
                c = count_tempo_traces(resp)
                ev = evidence_json(resp, max_chars=int(te_cfg.get("evidenceMaxChars", 450)))
                f = tempo_errortrace_findings(c, th, assetType, assetId)
                if f:
                    name = stable_name("obs-tempo", f"{assetType}|{assetId}|trace_errors")
                    upsert_signal(co, name, {
                        "assetId": f.assetId,
                        "assetType": f.assetType,
                        "IR": f.IR, "VR": f.VR, "RR": f.RR, "ER": f.ER,
                        "confidence": f.confidence,
                        "observations": [*f.observations, f"tempo_q={q[:160]}", f"evidence={ev}"]
                    })

        except Exception as e:
            print(f"observability-signal-ingestor: loop error: {e}")

        time.sleep(interval)

if __name__ == "__main__":
    main()

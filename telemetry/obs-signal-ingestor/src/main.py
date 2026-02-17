from __future__ import annotations
import os, time, yaml, datetime
from kubernetes import client, config

from signal import upsert_signal, stable_name
from prom import query as prom_query
from loki import query as loki_query
from tempo import ready as tempo_ready

def load_cfg(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}

def float_val(v) -> float:
    try:
        return float(v)
    except Exception:
        return 0.0

def now_iso() -> str:
    return datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

def emit_signal(co, prefix: str, asset_type: str, asset_id: str, scores: dict, observations: list[str]):
    name = stable_name(prefix, asset_type, asset_id, observations[0] if observations else now_iso())
    spec = {
        "assetType": asset_type,
        "assetId": asset_id,
        "IR": float(scores.get("IR", 2)),
        "VR": float(scores.get("VR", 4)),
        "RR": float(scores.get("RR", 6)),
        "ER": float(scores.get("ER", 4)),
        "confidence": float(scores.get("confidence", 0.7)),
        "observations": observations[:10],
    }
    upsert_signal(co, name, spec)

def run_prometheus(co, prom_url: str, cfg: dict):
    rules = cfg.get("prometheus", {}).get("rules", []) or []
    for rule in rules:
        name = rule.get("name", "prom-rule")
        promql = rule.get("query")
        if not promql:
            continue
        threshold = float_val(rule.get("threshold", 0))
        asset_type = rule.get("assetType", "k8s_ns")
        asset_id_label = rule.get("assetIdLabel", "namespace")
        fallback_asset_id = rule.get("assetId", "prod")
        scores = rule.get("scores") or {}

        try:
            results = prom_query(prom_url, promql)
        except Exception as e:
            emit_signal(co, "obs-prom", "k8s_ns", "telemetry", {"IR":1,"VR":1,"RR":3,"ER":1,"confidence":0.5},
                        [f"source=prometheus error={e} ts={now_iso()}"])
            continue

        for r in results:
            metric = r.get("metric", {}) or {}
            value = r.get("value", [None, "0"])[1]
            v = float_val(value)
            if v <= threshold:
                continue

            asset_id = metric.get(asset_id_label) or fallback_asset_id
            obs = [
                f"source=prometheus rule={name} ts={now_iso()}",
                f"query={promql}",
                f"value={v} threshold={threshold}",
                f"labels={metric}",
            ]
            emit_signal(co, "obs-prom", asset_type, asset_id, scores, obs)

def run_loki(co, loki_url: str, cfg: dict):
    rules = cfg.get("loki", {}).get("rules", []) or []
    for rule in rules:
        name = rule.get("name", "loki-rule")
        logql = rule.get("query")
        if not logql:
            continue
        threshold = float_val(rule.get("threshold", 0))
        asset_type = rule.get("assetType", "k8s_ns")
        asset_id_label = rule.get("assetIdLabel", "namespace")
        fallback_asset_id = rule.get("assetId", "prod")
        scores = rule.get("scores") or {}

        try:
            results = loki_query(loki_url, logql)
        except Exception as e:
            emit_signal(co, "obs-loki", "k8s_ns", "telemetry", {"IR":1,"VR":1,"RR":3,"ER":1,"confidence":0.5},
                        [f"source=loki error={e} ts={now_iso()}"])
            continue

        # Loki returns vector results like Prometheus
        for r in results:
            metric = r.get("metric", {}) or {}
            value = r.get("value", [None, "0"])[1]
            v = float_val(value)
            if v <= threshold:
                continue

            asset_id = metric.get(asset_id_label) or fallback_asset_id
            obs = [
                f"source=loki rule={name} ts={now_iso()}",
                f"query={logql}",
                f"value={v} threshold={threshold}",
                f"labels={metric}",
            ]
            emit_signal(co, "obs-loki", asset_type, asset_id, scores, obs)

def run_tempo(co, tempo_url: str, cfg: dict):
    # Optional: just emit health signal for now; full span-error extraction can be added later.
    if not tempo_url:
        return
    if not tempo_ready(tempo_url):
        emit_signal(co, "obs-tempo", "k8s_ns", "telemetry",
                    {"IR":1,"VR":1,"RR":3,"ER":2,"confidence":0.6},
                    [f"source=tempo status=not-ready ts={now_iso()}"])

def main():
    config.load_incluster_config()
    co = client.CustomObjectsApi()

    cfg_path = os.environ.get("OBS_CFG", "/config/obs-ingestor.yaml")
    cfg = load_cfg(cfg_path)

    prom_url = os.environ.get("PROM_URL", cfg.get("prometheus", {}).get("url", ""))
    loki_url = os.environ.get("LOKI_URL", cfg.get("loki", {}).get("url", ""))
    tempo_url = os.environ.get("TEMPO_URL", cfg.get("tempo", {}).get("url", ""))

    run_prometheus(co, prom_url, cfg) if prom_url else None
    run_loki(co, loki_url, cfg) if loki_url else None
    run_tempo(co, tempo_url, cfg)

if __name__ == "__main__":
    # Intended for CronJob; run once.
    main()

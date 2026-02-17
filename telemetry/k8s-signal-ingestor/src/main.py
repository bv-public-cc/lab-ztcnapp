from __future__ import annotations
import os, time, yaml
from kubernetes import client, config, watch
from policyreport_parser import extract_results, normalize_kyverno_violation
from signal_writer import upsert_signal, stable_name

PR_GROUP = "wgpolicyk8s.io"
PR_VERSION = "v1alpha2"
PR_PLURAL_NAMESPACED = "policyreports"
PR_PLURAL_CLUSTER = "clusterpolicyreports"

def load_mapping(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}

def score_from_mapping(mapping: dict, ev: dict) -> dict:
    d = mapping.get("default", {})
    IR = float(d.get("IR", 3)); VR = float(d.get("VR", 7)); RR = float(d.get("RR", 2)); ER = float(d.get("ER", 2))
    conf = float(d.get("confidence", 0.9))
    pol = ev.get("policy"); rule = ev.get("rule")
    pol_map = (mapping.get("policies") or {}).get(pol) or {}
    if pol_map.get("default"):
        p = pol_map["default"]
        IR = float(p.get("IR", IR)); VR = float(p.get("VR", VR)); RR = float(p.get("RR", RR)); ER = float(p.get("ER", ER))
        conf = float(p.get("confidence", conf))
    rule_map = (pol_map.get("rules") or {}).get(rule) or {}
    if rule_map:
        IR = float(rule_map.get("IR", IR)); VR = float(rule_map.get("VR", VR)); RR = float(rule_map.get("RR", RR)); ER = float(rule_map.get("ER", ER))
        conf = float(rule_map.get("confidence", conf))
    return {"IR": IR, "VR": VR, "RR": RR, "ER": ER, "confidence": conf}

def process_report(co_api, report_obj: dict, mapping: dict) -> int:
    md = report_obj.get("metadata", {})
    rname = md.get("name", "")
    rns = md.get("namespace", "")
    kind = report_obj.get("kind", "")
    count = 0
    for res in extract_results(report_obj):
        if res.get("result") != "fail":
            continue
        for affected in (res.get("resources") or []):
            ev = normalize_kyverno_violation(res, affected)
            if not ev:
                continue
            scores = score_from_mapping(mapping, ev)
            rid = ev.get("resourceUid") or f"{ev.get('resourceNamespace')}/{ev.get('resourceKind')}/{ev.get('resourceName')}"
            sname = stable_name("k8s-kyverno", ev.get("policy",""), ev.get("rule",""), rid)
            spec = {
                "assetId": ev["assetId"],
                "assetType": ev["assetType"],
                "IR": scores["IR"], "VR": scores["VR"], "RR": scores["RR"], "ER": scores["ER"],
                "confidence": scores["confidence"],
                "observations": [
                    f"source=policyreport kind={kind} report={(rns + '/' + rname).strip('/')}",
                    f"policy={ev.get('policy')} rule={ev.get('rule')}",
                    f"resource={ev.get('resourceNamespace')}/{ev.get('resourceKind')}/{ev.get('resourceName')}",
                    f"message={ev.get('message')}",
                ],
            }
            upsert_signal(co_api, sname, spec)
            count += 1
    return count

def main():
    config.load_incluster_config()
    co = client.CustomObjectsApi()
    mapping = load_mapping(os.environ.get("MAPPING_PATH", "/config/mapping.yaml"))
    print("k8s-signal-ingestor: watching PolicyReports...")

    while True:
        try:
            w1 = watch.Watch()
            for event in w1.stream(co.list_cluster_custom_object, PR_GROUP, PR_VERSION, PR_PLURAL_NAMESPACED, timeout_seconds=0):
                if event.get("type") in ("ADDED","MODIFIED"):
                    process_report(co, event.get("object", {}), mapping)
        except Exception as e:
            print(f"ingestor: policyreports watch error: {e}")
            time.sleep(5)

        try:
            w2 = watch.Watch()
            for event in w2.stream(co.list_cluster_custom_object, PR_GROUP, PR_VERSION, PR_PLURAL_CLUSTER, timeout_seconds=0):
                if event.get("type") in ("ADDED","MODIFIED"):
                    process_report(co, event.get("object", {}), mapping)
        except Exception as e:
            print(f"ingestor: clusterpolicyreports watch error: {e}")
            time.sleep(5)

if __name__ == "__main__":
    main()

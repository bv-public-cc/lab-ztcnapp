from __future__ import annotations
from typing import Any, Dict, List, Optional

def extract_results(report_obj: Dict[str, Any]) -> List[Dict[str, Any]]:
    results = report_obj.get("results") or []
    out = []
    for r in results:
        out.append({
            "policy": r.get("policy"),
            "rule": r.get("rule"),
            "result": (r.get("result") or "").lower(),
            "message": r.get("message") or "",
            "resources": r.get("resources") or [],
            "severity": (r.get("severity") or "").lower(),
        })
    return out

def normalize_kyverno_violation(result: Dict[str, Any], res: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    ns = res.get("namespace") or ""
    name = res.get("name") or ""
    kind = (res.get("kind") or "").lower()
    if not name or not kind:
        return None

    if kind == "pod":
        asset_type = "k8s_pod"
        asset_id = f"{ns or 'default'}/{name}"
    elif kind in ("deployment","statefulset","daemonset"):
        asset_type = "k8s_deploy"
        asset_id = f"{ns or 'default'}/{name}"
    else:
        asset_type = "k8s_ns"
        asset_id = ns or "default"

    return {
        "assetType": asset_type,
        "assetId": asset_id,
        "policy": result.get("policy") or "unknown",
        "rule": result.get("rule") or "unknown",
        "result": result.get("result") or "unknown",
        "message": (result.get("message") or "")[:256],
        "resourceKind": res.get("kind") or "",
        "resourceName": name,
        "resourceNamespace": ns or "default",
        "resourceUid": res.get("uid") or "",
        "severity": (result.get("severity") or "medium").lower(),
    }

from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

@dataclass
class Finding:
    assetType: str
    assetId: str
    IR: float
    VR: float
    RR: float
    ER: float
    confidence: float
    observations: List[str]

def _float(v: Any, default: float = 0.0) -> float:
    try:
        return float(v)
    except Exception:
        return default

def parse_prom_scalar(resp: Dict[str, Any]) -> float:
    try:
        result = resp["data"]["result"]
        if not result:
            return 0.0
        # scalar vector: first element, value [ts, val]
        return _float(result[0]["value"][1], 0.0)
    except Exception:
        return 0.0

def parse_prom_vector(resp: Dict[str, Any], label_keys: List[str]) -> List[Tuple[Dict[str,str], float]]:
    out = []
    try:
        for item in resp["data"]["result"]:
            metric = item.get("metric", {}) or {}
            labels = {k: metric.get(k,"") for k in label_keys}
            val = _float(item.get("value",[None,"0"])[1], 0.0)
            out.append((labels, val))
    except Exception:
        pass
    return out

def prom_error_rate_findings(vector: List[Tuple[Dict[str,str], float]], threshold: float) -> List[Finding]:
    findings=[]
    for labels, val in vector:
        if val < threshold:
            continue
        ns = labels.get("k8s_namespace_name") or labels.get("namespace") or "unknown"
        dep = labels.get("k8s_deployment_name") or labels.get("deployment") or ""
        if dep:
            assetType="k8s_deploy"; assetId=f"{ns}/{dep}"
        else:
            assetType="k8s_ns"; assetId=ns
        findings.append(Finding(
            assetType=assetType, assetId=assetId,
            IR=2, VR=2, RR=6, ER=4,
            confidence=0.75,
            observations=[
                f"prom: error_rate={val} (threshold={threshold})",
                f"labels={labels}",
                "signal=runtime_error_rate"
            ]
        ))
    return findings

def prom_restart_findings(vector: List[Tuple[Dict[str,str], float]], threshold: float) -> List[Finding]:
    findings=[]
    for labels, val in vector:
        if val < threshold:
            continue
        ns = labels.get("namespace") or labels.get("k8s_namespace_name") or "unknown"
        pod = labels.get("pod") or labels.get("k8s_pod_name") or ""
        assetType="k8s_pod" if pod else "k8s_ns"
        assetId=f"{ns}/{pod}" if pod else ns
        findings.append(Finding(
            assetType=assetType, assetId=assetId,
            IR=1, VR=3, RR=7, ER=3,
            confidence=0.8,
            observations=[
                f"prom: restarts_5m={val} (threshold={threshold})",
                f"labels={labels}",
                "signal=pod_restart_burst"
            ]
        ))
    return findings

def loki_errorlog_findings(samples: int, threshold: int, assetType: str, assetId: str) -> Optional[Finding]:
    if samples < threshold:
        return None
    return Finding(
        assetType=assetType, assetId=assetId,
        IR=1, VR=2, RR=6, ER=3,
        confidence=0.7,
        observations=[
            f"loki: error_logs={samples} (threshold={threshold})",
            "signal=log_error_burst"
        ]
    )

def tempo_errortrace_findings(count: int, threshold: int, assetType: str, assetId: str) -> Optional[Finding]:
    if count < threshold:
        return None
    return Finding(
        assetType=assetType, assetId=assetId,
        IR=1, VR=1, RR=8, ER=3,
        confidence=0.7,
        observations=[
            f"tempo: error_traces={count} (threshold={threshold})",
            "signal=trace_error_burst"
        ]
    )

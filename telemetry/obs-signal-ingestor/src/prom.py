from __future__ import annotations
import requests

def query(prom_url: str, promql: str, timeout: float = 5.0) -> list[dict]:
    r = requests.get(f"{prom_url.rstrip('/')}/api/v1/query", params={"query": promql}, timeout=timeout)
    r.raise_for_status()
    data = r.json()
    if data.get("status") != "success":
        return []
    return data.get("data", {}).get("result", []) or []

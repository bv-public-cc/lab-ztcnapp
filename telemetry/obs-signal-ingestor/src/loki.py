from __future__ import annotations
import requests

def query(loki_url: str, logql: str, timeout: float = 6.0) -> list[dict]:
    # Loki instant query endpoint
    r = requests.get(f"{loki_url.rstrip('/')}/loki/api/v1/query", params={"query": logql}, timeout=timeout)
    r.raise_for_status()
    data = r.json()
    if data.get("status") != "success":
        return []
    return data.get("data", {}).get("result", []) or []

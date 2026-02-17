from __future__ import annotations
import requests
from typing import Any, Dict

class PromClient:
    def __init__(self, base: str, timeout: float = 5.0):
        self.base = base.rstrip("/")
        self.timeout = timeout

    def query(self, promql: str) -> Dict[str, Any]:
        r = requests.get(f"{self.base}/api/v1/query", params={"query": promql}, timeout=self.timeout)
        r.raise_for_status()
        return r.json()

class LokiClient:
    def __init__(self, base: str, timeout: float = 5.0):
        self.base = base.rstrip("/")
        self.timeout = timeout

    def query(self, logql: str, limit: int = 100) -> Dict[str, Any]:
        r = requests.get(
            f"{self.base}/loki/api/v1/query",
            params={"query": logql, "limit": str(limit)},
            timeout=self.timeout
        )
        r.raise_for_status()
        return r.json()

class TempoClient:
    def __init__(self, base: str, timeout: float = 5.0):
        self.base = base.rstrip("/")
        self.timeout = timeout

    def search(self, q: str, limit: int = 20) -> Dict[str, Any]:
        # Tempo search endpoints vary by version; this uses the v2 search endpoint where available.
        r = requests.get(
            f"{self.base}/api/search",
            params={"q": q, "limit": str(limit)},
            timeout=self.timeout
        )
        # If endpoint isn't supported, return empty instead of hard failing.
        if r.status_code == 404:
            return {"status": "success", "data": {"traces": []}}
        r.raise_for_status()
        return r.json()

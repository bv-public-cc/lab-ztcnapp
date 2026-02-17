from __future__ import annotations
import requests

def ready(tempo_url: str, timeout: float = 3.0) -> bool:
    try:
        r = requests.get(f"{tempo_url.rstrip('/')}/ready", timeout=timeout)
        return r.status_code == 200
    except Exception:
        return False

def search(tempo_url: str, tags: str, min_duration: str = "", limit: int = 20, timeout: float = 6.0) -> dict:
    # Tempo search API varies by version. This implements a best-effort call used as an optional enrichment.
    # Example: /api/search?tags=service.name%3Dotel-demo-app
    params = {"tags": tags, "limit": str(limit)}
    if min_duration:
        params["minDuration"] = min_duration
    r = requests.get(f"{tempo_url.rstrip('/')}/api/search", params=params, timeout=timeout)
    r.raise_for_status()
    return r.json()

import json, os, time
from typing import Tuple

CACHE_PATH = os.environ.get("PA_CACHE_PATH", "/cache/state.json")

def _load() -> dict:
    try:
        with open(CACHE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"last": {}}

def _save(state: dict) -> None:
    os.makedirs(os.path.dirname(CACHE_PATH), exist_ok=True)
    with open(CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f)

def cooldown_allows(key: str, cooldown_seconds: int) -> Tuple[bool, str]:
    st = _load()
    now = int(time.time())
    last = int(st["last"].get(key, 0))
    if now - last < cooldown_seconds:
        return False, f"cooldown active ({now-last}s since last enforce)"
    st["last"][key] = now
    _save(st)
    return True, "cooldown ok"

from __future__ import annotations
import hashlib
from kubernetes.client.rest import ApiException

GROUP = "zta.example.com"
VERSION = "v1alpha1"
SIG_PLURAL = "ztasignals"

def stable_name(prefix: str, *parts: str, maxlen: int = 63) -> str:
    raw = "|".join([p for p in parts if p is not None])
    h = hashlib.sha1(raw.encode("utf-8")).hexdigest()[:10]
    base = f"{prefix}-{h}".lower()
    return base[:maxlen]

def upsert_signal(co_api, name: str, spec: dict) -> None:
    body = {"apiVersion": f"{GROUP}/{VERSION}", "kind": "ZTASignal", "metadata": {"name": name}, "spec": spec}
    try:
        co_api.create_cluster_custom_object(GROUP, VERSION, SIG_PLURAL, body)
    except ApiException as e:
        if e.status == 409:
            patch = {"spec": spec, "status": {"processed": False}}
            co_api.patch_cluster_custom_object(GROUP, VERSION, SIG_PLURAL, name, patch)
        else:
            raise

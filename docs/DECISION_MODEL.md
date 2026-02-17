# Decision model behavior (PE/PA)

## PE (Policy Engine)
- Produces a **stable ZTADecision per asset** (`dec-<assetType>-<assetId>`), updated in place.
- Applies:
  - Weighted scoring on IR/VR/RR/ER × confidence
  - Hysteresis (avoid oscillations):
    - If previously QUARANTINE/ISOLATE, require score < recover_below to recover
    - If previously RESTRICT, do not ALLOW unless score < allow threshold
  - Cooldown (per asset) to reduce thrash

## PA (Policy Administrator)
- Dedup/cooldown enforcement per asset+decision (PA cache).
- For k8s_pod assets, attempts to **resolve controller ownerReferences** and enforce at Deployment level.
- For ISOLATE on deployments, optionally scales replicas to 0 (strong containment).
- For k8s enforcement, the primary PEP is label-driven NetworkPolicies.

## Evidence
- Decision status includes actions taken + verification evidence (VM nftables head / AWS SG checks).

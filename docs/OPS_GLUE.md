# Ops Glue: secrets/config needed for the lab

This repo intentionally **does not** commit real secrets. Apply these templates after you substitute values.

## 1) PA SSH private key secret
File: `platform/kubernetes/ops/pa-ssh-key-secret-template.yaml`

1) Create an SSH keypair on your admin workstation:
```bash
ssh-keygen -t ed25519 -f ./pa_id_ed25519 -C "pa-key"
```

2) Copy the private key into the template under `stringData.id_ed25519`.

3) Apply:
```bash
kubectl apply -f platform/kubernetes/ops/pa-ssh-key-secret-template.yaml
```

## 2) PA known_hosts ConfigMap
File: `platform/kubernetes/ops/pa-known-hosts-configmap-template.yaml`

Generate pinned host keys:
```bash
ssh-keyscan -H 10.0.20.10 >> known_hosts
ssh-keyscan -H 10.0.20.11 >> known_hosts
```

Paste the contents into the template and apply:
```bash
kubectl apply -f platform/kubernetes/ops/pa-known-hosts-configmap-template.yaml
```

## 3) AWS credentials (optional)
File: `platform/kubernetes/ops/aws-creds-secret-template.yaml`

Populate keys and apply:
```bash
kubectl apply -f platform/kubernetes/ops/aws-creds-secret-template.yaml
```

> If you do not use AWS, you may keep the `aws-signal-generator` CronJob disabled and remove `envFrom` in PA.

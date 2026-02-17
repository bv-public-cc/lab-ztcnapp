import os, datetime
import boto3
from kubernetes import client, config
from kubernetes.client.rest import ApiException

GROUP="zta.example.com"
VERSION="v1alpha1"
SIG_PLURAL="ztasignals"

def upsert_signal(api, name, spec):
    body = {"apiVersion": f"{GROUP}/{VERSION}", "kind": "ZTASignal", "metadata": {"name": name}, "spec": spec}
    try:
        api.create_cluster_custom_object(GROUP, VERSION, SIG_PLURAL, body)
    except ApiException as e:
        if e.status == 409:
            patch = {"spec": spec, "status": {"processed": False}}
            api.patch_cluster_custom_object(GROUP, VERSION, SIG_PLURAL, name, patch)
        else:
            raise

def sg_public_exposure(ec2):
    findings=[]
    sgs = ec2.describe_security_groups()["SecurityGroups"]
    for sg in sgs:
        sgid = sg["GroupId"]
        for perm in sg.get("IpPermissions", []):
            ipranges = perm.get("IpRanges", [])
            fromp = perm.get("FromPort")
            top = perm.get("ToPort")
            proto = perm.get("IpProtocol")
            for r in ipranges:
                if r.get("CidrIp") == "0.0.0.0/0":
                    if fromp in (22,3389,80,443) or top in (22,3389,80,443) or fromp is None:
                        findings.append((sgid, proto, fromp, top))
    return findings

def iam_admin_roles(iam):
    findings=[]
    paginator = iam.get_paginator("list_roles")
    for page in paginator.paginate():
        for role in page["Roles"]:
            rname = role["RoleName"]
            aps = iam.list_attached_role_policies(RoleName=rname)["AttachedPolicies"]
            for p in aps:
                if p["PolicyName"] == "AdministratorAccess":
                    findings.append(rname)
    return findings

def main():
    config.load_incluster_config()
    k8s = client.CustomObjectsApi()
    region = os.environ.get("AWS_REGION","us-east-1")
    ec2 = boto3.client("ec2", region_name=region)
    iam = boto3.client("iam", region_name=region)

    sg_findings = sg_public_exposure(ec2)
    for sgid, proto, fp, tp in sg_findings[:50]:
        name = f"aws-sg-exposed-{sgid.lower().replace('-','')}"
        spec = {
            "assetId": sgid,
            "assetType": "aws_sg",
            "IR": 1, "VR": 2, "RR": 1, "ER": 9,
            "confidence": 0.9,
            "observations": [f"public_ingress {proto} {fp}-{tp}", "source:ec2_describe_security_groups"]
        }
        upsert_signal(k8s, name, spec)

    admin_roles = iam_admin_roles(iam)
    for rname in admin_roles[:50]:
        name = f"aws-iam-admin-{rname.lower().replace('_','-')[:50]}"
        spec = {
            "assetId": rname,
            "assetType": "aws_role",
            "IR": 9, "VR": 2, "RR": 1, "ER": 3,
            "confidence": 0.8,
            "observations": ["admin_policy_attached:AdministratorAccess", "source:iam_list_attached_role_policies"]
        }
        upsert_signal(k8s, name, spec)

    print(f"signals upserted: sg={len(sg_findings)} iam_admin={len(admin_roles)}")

if __name__ == "__main__":
    main()

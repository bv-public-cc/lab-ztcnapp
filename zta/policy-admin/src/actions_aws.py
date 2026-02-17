import boto3

SENSITIVE_PORTS = {22, 3389, 80, 443}

def _is_public_range(r: dict) -> bool:
    return r.get("CidrIp") == "0.0.0.0/0" or r.get("CidrIpv6") == "::/0"

def lockdown_sg_public_ingress(sg_id: str, region: str) -> tuple[bool, str]:
    ec2 = boto3.client("ec2", region_name=region)
    sg = ec2.describe_security_groups(GroupIds=[sg_id])["SecurityGroups"][0]

    revoke_permissions = []
    for perm in sg.get("IpPermissions", []):
        ipproto = perm.get("IpProtocol")
        fromp = perm.get("FromPort")
        top = perm.get("ToPort")

        ports_known = (fromp is not None and top is not None)
        port_hit = (not ports_known) or (fromp in SENSITIVE_PORTS or top in SENSITIVE_PORTS)

        public_v4 = [r for r in perm.get("IpRanges", []) if _is_public_range(r)]
        public_v6 = [r for r in perm.get("Ipv6Ranges", []) if _is_public_range(r)]

        if (public_v4 or public_v6) and port_hit:
            rp = {"IpProtocol": ipproto, "IpRanges": public_v4, "Ipv6Ranges": public_v6}
            if ports_known:
                rp["FromPort"] = fromp
                rp["ToPort"] = top
            revoke_permissions.append(rp)

    if not revoke_permissions:
        return True, "no public ingress to revoke"

    ec2.revoke_security_group_ingress(GroupId=sg_id, IpPermissions=revoke_permissions)
    return True, f"revoked {len(revoke_permissions)} public ingress permission blocks"

def verify_sg_not_public(sg_id: str, region: str) -> tuple[bool, str]:
    ec2 = boto3.client("ec2", region_name=region)
    sg = ec2.describe_security_groups(GroupIds=[sg_id])["SecurityGroups"][0]

    for perm in sg.get("IpPermissions", []):
        fromp = perm.get("FromPort")
        top = perm.get("ToPort")
        ports_known = (fromp is not None and top is not None)
        port_hit = (not ports_known) or (fromp in SENSITIVE_PORTS or top in SENSITIVE_PORTS)

        if not port_hit:
            continue

        for r in perm.get("IpRanges", []):
            if _is_public_range(r):
                return False, f"still public v4 on {perm.get('IpProtocol')} {fromp}-{top}"
        for r in perm.get("Ipv6Ranges", []):
            if _is_public_range(r):
                return False, f"still public v6 on {perm.get('IpProtocol')} {fromp}-{top}"

    return True, "no public ingress detected"

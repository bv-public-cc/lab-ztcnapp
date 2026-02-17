# Rocky VM Prep (targets for PA enforcement)

Run on every target VM.

## Create zta-admin user + SSH key auth
```bash
sudo useradd -m -s /bin/bash zta-admin
sudo mkdir -p /home/zta-admin/.ssh
sudo chmod 700 /home/zta-admin/.ssh
sudo tee -a /home/zta-admin/.ssh/authorized_keys >/dev/null <<'EOF'
ssh-ed25519 AAAA...your_public_key_here... comment
EOF
sudo chmod 600 /home/zta-admin/.ssh/authorized_keys
sudo chown -R zta-admin:zta-admin /home/zta-admin/.ssh
```

## Passwordless sudo for nftables
```bash
sudo tee /etc/sudoers.d/zta-admin >/dev/null <<'EOF'
zta-admin ALL=(ALL) NOPASSWD: /usr/sbin/nft, /bin/systemctl, /usr/bin/dnf, /usr/sbin/sshd
EOF
sudo chmod 440 /etc/sudoers.d/zta-admin
```

## Ensure ssh + python + nftables
```bash
sudo dnf install -y python3 nftables
sudo systemctl enable --now sshd
```

## Validate from control host
```bash
ssh zta-admin@VM_IP "sudo nft list ruleset | head"
```

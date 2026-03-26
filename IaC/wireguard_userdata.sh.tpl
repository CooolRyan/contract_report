#!/bin/bash
set -euo pipefail

exec > /var/log/wireguard-setup.log 2>&1

export DEBIAN_FRONTEND=noninteractive

apt-get update -y
apt-get upgrade -y
apt-get install -y wireguard iptables-persistent curl

# Enable IP forwarding (VPN 터널 포워딩용)
echo 'net.ipv4.ip_forward = 1' >> /etc/sysctl.conf
sysctl -p

umask 077
mkdir -p /etc/wireguard

# ---- Keys ----
wg genkey | tee /etc/wireguard/server.key | wg pubkey > /etc/wireguard/server.pub
wg genkey | tee /etc/wireguard/client1.key | wg pubkey > /etc/wireguard/client1.pub

SERVER_PRIV_KEY="$(cat /etc/wireguard/server.key)"
CLIENT1_PUB_KEY="$(cat /etc/wireguard/client1.pub)"
CLIENT1_PRIV_KEY="$(cat /etc/wireguard/client1.key)"

# ---- Networking helpers ----
PRIMARY_IF=$(ip route | awk '/default/ {print $5; exit}')

# ---- WireGuard server config ----
cat > /etc/wireguard/wg0.conf <<EOF
[Interface]
Address = ${wg_server_ip}/${vpn_client_prefix}
ListenPort = 51820
PrivateKey = ${SERVER_PRIV_KEY}

# NAT VPN client IPs to the server's VPC IP for easy SG matching
PostUp = iptables -t nat -A POSTROUTING -s ${vpn_client_cidr} -o ${PRIMARY_IF} -j MASQUERADE; iptables -A FORWARD -i wg0 -o ${PRIMARY_IF} -j ACCEPT; iptables -A FORWARD -i ${PRIMARY_IF} -o wg0 -m state --state RELATED,ESTABLISHED -j ACCEPT
PostDown = iptables -t nat -D POSTROUTING -s ${vpn_client_cidr} -o ${PRIMARY_IF} -j MASQUERADE; iptables -D FORWARD -i wg0 -o ${PRIMARY_IF} -j ACCEPT; iptables -D FORWARD -i ${PRIMARY_IF} -o wg0 -m state --state RELATED,ESTABLISHED -j ACCEPT

[Peer]
PublicKey = ${CLIENT1_PUB_KEY}
AllowedIPs = ${wg_client1_ip}/32
EOF

netfilter-persistent save

systemctl enable wg-quick@wg0
systemctl start wg-quick@wg0

# ---- Generate client config ----
PUBLIC_IP=$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4 \
  || curl -s http://checkip.amazonaws.com)
SERVER_PUB_KEY="$(cat /etc/wireguard/server.pub)"

mkdir -p /home/ubuntu/client-configs

cat > /home/ubuntu/client-configs/client1.conf <<CLIENTCONF
[Interface]
PrivateKey = ${CLIENT1_PRIV_KEY}
Address = ${wg_client1_ip}/32
DNS = ${vpc_dns_ip}

[Peer]
PublicKey = ${SERVER_PUB_KEY}
Endpoint = ${PUBLIC_IP}:51820
AllowedIPs = ${vpc_cidr}
PersistentKeepalive = 25
CLIENTCONF

chown -R ubuntu:ubuntu /home/ubuntu/client-configs
chmod 600 /home/ubuntu/client-configs/client1.conf

echo "=== WireGuard setup complete ==="

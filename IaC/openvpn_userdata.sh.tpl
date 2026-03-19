#!/bin/bash
set -euo pipefail

exec > /var/log/openvpn-setup.log 2>&1

export DEBIAN_FRONTEND=noninteractive

apt-get update -y
apt-get upgrade -y

# iptables-persistent는 user-data에서 interactive prompt로 멈추는 경우가 있어 preseed 처리
echo iptables-persistent iptables-persistent/autosave_v4 boolean true | debconf-set-selections
echo iptables-persistent iptables-persistent/autosave_v6 boolean true | debconf-set-selections

apt-get install -y -o Dpkg::Options::='--force-confdef' \
  -o Dpkg::Options::='--force-confold' \
  openvpn easy-rsa iptables-persistent

# Enable IP forwarding (VPN 터널 포워딩용)
echo 'net.ipv4.ip_forward = 1' >> /etc/sysctl.conf
sysctl -p

# ---- PKI setup (easy-rsa) ----
EASY_RSA="/etc/openvpn/easy-rsa"
mkdir -p "$EASY_RSA"
cp -r /usr/share/easy-rsa/* "$EASY_RSA/"
cd "$EASY_RSA"

./easyrsa init-pki
EASYRSA_BATCH=1 ./easyrsa build-ca nopass
EASYRSA_BATCH=1 ./easyrsa build-server-full server nopass
EASYRSA_BATCH=1 ./easyrsa build-client-full client1 nopass
./easyrsa gen-dh
openvpn --genkey secret /etc/openvpn/ta.key

cp pki/ca.crt pki/issued/server.crt pki/private/server.key pki/dh.pem /etc/openvpn/

# ---- OpenVPN server config ----
cat > /etc/openvpn/server.conf <<EOF
port 1194
proto udp
dev tun

ca   /etc/openvpn/ca.crt
cert /etc/openvpn/server.crt
key  /etc/openvpn/server.key
dh   /etc/openvpn/dh.pem
tls-auth /etc/openvpn/ta.key 0

server ${vpn_client_network} ${vpn_client_netmask}
topology subnet

# VPC로 들어가는 route push (로컬에서 Pod IP까지 접근하려면 VPC 대역 라우팅이 필요)
push "route ${vpc_cidr} ${vpc_cidr_mask}"

# VPC DNS를 VPN 클라이언트에 전달 (Route53 private zone/내부 호스트네임 해석에 도움)
push "dhcp-option DNS ${vpc_dns_ip}"

keepalive 10 120
cipher AES-256-GCM
auth SHA256
user nobody
group nogroup
persist-key
persist-tun

status /var/log/openvpn-status.log
log-append /var/log/openvpn.log
verb 3
EOF

# ---- NAT / forwarding rules ----
# VPN client IP를 OpenVPN 서버의 VPC IP로 masquerade 하여, VPC SG 매칭을 쉽게 함
PRIMARY_IF=$(ip route | awk '/default/ {print $5; exit}')

iptables -t nat -A POSTROUTING -s ${vpn_client_cidr} -o "$PRIMARY_IF" -j MASQUERADE

iptables -A FORWARD -i tun0 -o "$PRIMARY_IF" -j ACCEPT
iptables -A FORWARD -i "$PRIMARY_IF" -o tun0 \
  -m state --state RELATED,ESTABLISHED -j ACCEPT

netfilter-persistent save

systemctl enable openvpn@server
systemctl start openvpn@server

# ---- Generate client profile (.ovpn) ----
PUBLIC_IP=$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4 \
  || curl -s http://checkip.amazonaws.com)

mkdir -p /home/ubuntu/client-configs

cat > /home/ubuntu/client-configs/client1.ovpn <<CLIENTCONF
client
dev tun
proto udp
remote ${PUBLIC_IP} 1194
resolv-retry infinite
nobind
persist-key
persist-tun
remote-cert-tls server

cipher AES-256-GCM
auth SHA256
key-direction 1
verb 3

<ca>
$(cat /etc/openvpn/ca.crt)
</ca>
<cert>
$(openssl x509 -in "$EASY_RSA/pki/issued/client1.crt")
</cert>
<key>
$(cat "$EASY_RSA/pki/private/client1.key")
</key>
<tls-auth>
$(cat /etc/openvpn/ta.key)
</tls-auth>
CLIENTCONF

chown -R ubuntu:ubuntu /home/ubuntu/client-configs
chmod 600 /home/ubuntu/client-configs/client1.ovpn

echo "=== OpenVPN setup complete ==="


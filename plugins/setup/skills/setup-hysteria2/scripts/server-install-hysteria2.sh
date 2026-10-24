#!/usr/bin/env bash
# Runs ON the Linux VPS (pushed there by ssh-deploy.sh). Installs a Hysteria2
# server with a self-signed cert, systemd service, and firewall rule, then prints
# the client credentials in a RESULT block. Debian/Ubuntu (apt).
# Refuses to replace an existing installation or bind an occupied UDP port.
#
# Params via env (non-secret):  HY2_PORT (443)   HY2_SNI (bing.com)
# The auth password is generated here and returned — never passed in.
set -euo pipefail
umask 077
export DEBIAN_FRONTEND=noninteractive

PORT="${HY2_PORT:-443}"
SNI="${HY2_SNI:-bing.com}"

# Check before installing packages or modifying services. Never rotate existing credentials.
if [ -e /etc/hysteria/config.yaml ] || [ -L /etc/hysteria/config.yaml ] ||
   [ -e /etc/hysteria/server.crt ] || [ -L /etc/hysteria/server.crt ] ||
   [ -e /etc/hysteria/server.key ] || [ -L /etc/hysteria/server.key ] ||
   systemctl is-active --quiet hysteria-server.service; then
  echo "ERROR: Hysteria server files/service already exist; refusing to replace them" >&2
  exit 1
fi
if command -v ss >/dev/null 2>&1 && [ -n "$(ss -H -lun "sport = :$PORT")" ]; then
  echo "ERROR: UDP port $PORT is already in use; refusing to change another service" >&2
  exit 1
fi

echo "=== [1/6] deps ==="
need=""
command -v curl    >/dev/null 2>&1 || need="$need curl"
command -v openssl >/dev/null 2>&1 || need="$need openssl"
if [ -n "$need" ]; then
  apt-get -o DPkg::Lock::Timeout=120 update -y
  apt-get -o DPkg::Lock::Timeout=120 install -y $need
fi

echo "=== [2/6] install hysteria (official installer) ==="
if ! command -v hysteria >/dev/null 2>&1; then
  curl -fsSL https://get.hy2.sh/ | bash
fi
hysteria version 2>/dev/null | head -1 || true

echo "=== [3/6] self-signed cert (CN=$SNI) ==="
mkdir -p /etc/hysteria
openssl ecparam -genkey -name prime256v1 -out /etc/hysteria/server.key
openssl req -new -x509 -days 3650 -key /etc/hysteria/server.key \
  -out /etc/hysteria/server.crt -subj "/CN=$SNI" \
  -addext "subjectAltName=DNS:$SNI" 2>/dev/null
# hysteria-server.service runs as the 'hysteria' user — let it read the key
chown hysteria:hysteria /etc/hysteria/server.crt /etc/hysteria/server.key 2>/dev/null || true
chmod 644 /etc/hysteria/server.crt; chmod 600 /etc/hysteria/server.key

echo "=== [4/6] config ==="
PW="$(openssl rand -base64 24 | tr -dc 'A-Za-z0-9' | cut -c1-32)"
cat > /etc/hysteria/config.yaml <<EOF
listen: :$PORT

tls:
  cert: /etc/hysteria/server.crt
  key: /etc/hysteria/server.key

auth:
  type: password
  password: $PW

# 未认证流量伪装成 $SNI 的反代，抗探测
masquerade:
  type: proxy
  proxy:
    url: https://$SNI
    rewriteHost: true
EOF
chown hysteria:hysteria /etc/hysteria/config.yaml 2>/dev/null || true
chmod 600 /etc/hysteria/config.yaml

echo "=== [5/6] service ==="
systemctl enable hysteria-server.service >/dev/null
systemctl restart hysteria-server.service
sleep 1
systemctl is-active --quiet hysteria-server.service || {
  echo "ERROR: Hysteria service failed to start" >&2; exit 1; }

echo "=== [6/6] firewall ==="
if command -v ufw >/dev/null 2>&1 && ufw status 2>/dev/null | grep -qi "Status: active"; then
  ufw allow ${PORT}/udp >/dev/null
  echo "ufw: opened ${PORT}/udp"
else
  echo "ufw: inactive/absent (host firewall not blocking)"
fi

PIN="$(openssl x509 -in /etc/hysteria/server.crt -noout -fingerprint -sha256 | sed 's/.*=//; s/://g')"
IP="$(curl -fsSL --max-time 8 https://api.ipify.org 2>/dev/null || hostname -I 2>/dev/null | awk '{print $1}')"

echo "==== RESULT ===="
echo "HY2_SERVER=$IP"
echo "HY2_PORT=$PORT"
echo "HY2_SNI=$SNI"
echo "HY2_AUTH=$PW"
echo "HY2_PINSHA256=$PIN"
base64 < /etc/hysteria/server.crt | tr -d '\n' | awk '{print "HY2_CERT_BASE64=" $0}'
echo "==== DONE ===="

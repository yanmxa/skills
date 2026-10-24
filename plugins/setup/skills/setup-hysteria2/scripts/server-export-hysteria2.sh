#!/usr/bin/env bash
# Read-only export of an existing server installed by server-install-hysteria2.sh.
# Runs as root over SSH; caller MUST capture stdout privately (contains password).
set -euo pipefail
CONFIG=/etc/hysteria/config.yaml
CERT=/etc/hysteria/server.crt
[ -f "$CONFIG" ] && [ -f "$CERT" ] || { echo 'ERROR: missing Hysteria config/certificate' >&2; exit 1; }
grep -qx '  cert: /etc/hysteria/server.crt' "$CONFIG" &&
grep -qx '  type: password' "$CONFIG" || { echo 'ERROR: unsupported server TLS/auth configuration' >&2; exit 1; }
systemctl is-active --quiet hysteria-server.service || { echo 'ERROR: Hysteria service is inactive' >&2; exit 1; }
PORT="$(sed -n 's/^listen: :\([0-9]*\)$/\1/p' "$CONFIG")"
AUTH="$(sed -n 's/^  password: \([A-Za-z0-9]*\)$/\1/p' "$CONFIG")"
SNI="$(openssl x509 -in "$CERT" -noout -ext subjectAltName | sed -n 's/.*DNS:\([A-Za-z0-9.-]*\).*/\1/p' | head -1)"
if [ "$PORT" != "${HY2_PORT:?expected UDP port required}" ] || [ -z "$AUTH" ] || [ -z "$SNI" ]; then
  echo 'ERROR: existing server config does not match the requested port or expected format' >&2
  exit 1
fi
PIN="$(openssl x509 -in "$CERT" -noout -fingerprint -sha256 | sed 's/.*=//; s/://g')"
echo '==== RESULT ===='
echo "HY2_PORT=$PORT"
echo "HY2_SNI=$SNI"
echo "HY2_AUTH=$AUTH"
echo "HY2_PINSHA256=$PIN"
base64 < "$CERT" | tr -d '\n' | awk '{print "HY2_CERT_BASE64=" $0}'
echo '==== DONE ===='

#!/bin/bash
# Deploy a new Hysteria2 server and privately generate Mac/iPhone client profiles.
# Invoked by `setup-hysteria2.sh --server ...`.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

SERVER_PORT=443
SNI="bing.com"
ENV_FILE="$PWD/.env"
PROFILES_DIR="$HOME/.config/hysteria"
EXPORT_EXISTING=0
export SSH_USER="root" SSH_PORT="22"

usage() {
  cat <<'USAGE'
Usage: setup-hysteria2.sh --server --host <ip> [options]

  --host <ip>          (required) VPS host / IP
  --ssh-user <u>       SSH user (default: root)
  --ssh-port <p>       SSH port (default: 22)
  --ssh-key <path>     private key for auth (default: ssh-agent / ~/.ssh keys)
  --server-port <n>    Hysteria2 listen port (default: 443/UDP)
  --sni <domain>       TLS SNI / masquerade domain (default: bing.com)
  --env-file <path>    NEW, Git-ignored dotenv FILE (default: ./.env)
  --profiles-dir <d>  NEW named Mac/iPhone profiles (default: ~/.config/hysteria)
  --export-existing    READ existing server credentials; no install/service changes

Requires verified SSH host key and key-based access. Refuses to rotate an existing
server password/certificate or overwrite existing local files. Secrets are never
printed to the terminal. Mac and Clash Mi iPhone YAML profiles use chmod 600.
If any output path is inside a Git checkout, it must be ignored.
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --host)         export SSH_HOST="$2"; shift 2 ;;
    --ssh-user)     export SSH_USER="$2"; shift 2 ;;
    --ssh-port)     export SSH_PORT="$2"; shift 2 ;;
    --ssh-key)      export SSH_KEY="$2"; shift 2 ;;
    --server-port)  SERVER_PORT="$2"; shift 2 ;;
    --sni)          SNI="$2"; shift 2 ;;
    --env-file)     ENV_FILE="$2"; shift 2 ;;
    --profiles-dir) PROFILES_DIR="$2"; shift 2 ;;
    --export-existing) EXPORT_EXISTING=1; shift ;;
    -h|--help)      usage; exit 0 ;;
    *) echo "Unknown option: $1" >&2; usage; exit 1 ;;
  esac
done

if [[ ! "${SSH_HOST:-}" =~ ^[A-Za-z0-9.-]+$ || ! "$SNI" =~ ^[A-Za-z0-9.-]+$ || ! "$SERVER_PORT" =~ ^[1-9][0-9]{0,4}$ ]] ||
   (( 10#$SERVER_PORT > 65535 )); then
  echo "ERROR: valid --host, --server-port and --sni are required" >&2
  exit 1
fi
if [[ ! "$SSH_PORT" =~ ^[1-9][0-9]{0,4}$ ]] || (( 10#$SSH_PORT > 65535 )); then
  echo "ERROR: invalid SSH port" >&2; exit 1
fi

GENERATOR="$SCRIPT_DIR/generate-client-profiles.py"
OUTPUT_ARGS=(--host "$SSH_HOST" --port "$SERVER_PORT" --env-file "$ENV_FILE" --profiles-dir "$PROFILES_DIR")
# Do this before any remote changes. The output must not exist and .env must be ignored.
python3 "$GENERATOR" "${OUTPUT_ARGS[@]}"

# shellcheck source=ssh-deploy.sh
source "$SCRIPT_DIR/ssh-deploy.sh"
ssh_precheck || exit 1
ssh_init
if (( ! EXPORT_EXISTING )); then
  if ! ssh "${_SSH_OPTS[@]}" "$SSH_USER@$SSH_HOST" \
      'test ! -e /etc/hysteria/config.yaml && test ! -e /etc/hysteria/server.crt && test ! -e /etc/hysteria/server.key && ! systemctl is-active --quiet hysteria-server.service'; then
    echo "ERROR: server already has Hysteria files/service or SSH preflight failed; nothing deployed" >&2
    exit 1
  fi
fi

umask 077
LOG="$(mktemp -t hy2deploy)"
trap 'rm -f "$LOG"' EXIT
if (( EXPORT_EXISTING )); then
  printf 'Exporting existing Hysteria2 profiles from %s@%s (credentials hidden; server unchanged)...\n' "$SSH_USER" "$SSH_HOST"
  if ! ssh_run_remote_script "$SCRIPT_DIR/server-export-hysteria2.sh" "HY2_PORT=$SERVER_PORT" > "$LOG"; then
    echo "ERROR: server export failed; verify the config format and requested UDP port" >&2
    exit 1
  fi
else
  printf 'Deploying Hysteria2 to %s@%s on UDP %s (credentials hidden)...\n' "$SSH_USER" "$SSH_HOST" "$SERVER_PORT"
  if ! ssh_run_remote_script "$SCRIPT_DIR/server-install-hysteria2.sh" \
    "HY2_PORT=$SERVER_PORT" "HY2_SNI=$SNI" > "$LOG"; then
    echo "ERROR: remote installation failed; inspect the server before retrying (partial state may exist)" >&2
    exit 1
  fi
fi
python3 "$GENERATOR" "${OUTPUT_ARGS[@]}" --result-file "$LOG"
echo "Profiles ready. AirDrop only the clash-mi-*.yaml profile to your iPhone; it contains the password."

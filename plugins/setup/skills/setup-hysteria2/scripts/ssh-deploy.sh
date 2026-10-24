#!/bin/bash
# ssh-deploy.sh — sourced helper for "server mode": push a Linux install script to
# a remote VPS over SSH and run it. Key-based auth only (no passwords in the plugin);
# secrets are generated ON the server and returned inside an SSH result block.
#
# Required env before calling:
#   SSH_HOST                 target VPS host / IP
# Optional:
#   SSH_USER (default root)  SSH login user
#   SSH_PORT (default 22)    SSH port
#   SSH_KEY                  path to a private key (else the agent / default keys)
#
# Provides:
#   ssh_precheck                       → 0 if key auth works, else 1 (+ fix-it hint)
#   ssh_run_remote_script <file> [V=x] → base64-push <file>, run it with env V=x, stream output

SSH_USER="${SSH_USER:-root}"
SSH_PORT="${SSH_PORT:-22}"
_SSH_OPTS=()

ssh_init() {
  _SSH_OPTS=(-o BatchMode=yes -o StrictHostKeyChecking=yes -o ConnectTimeout=15 -p "$SSH_PORT")
  [ -n "${SSH_KEY:-}" ] && _SSH_OPTS+=(-i "$SSH_KEY")
}

# Verify key-based auth works. Returns non-zero (with a fix-it hint) if not.
ssh_precheck() {
  ssh_init
  if ssh -o BatchMode=yes "${_SSH_OPTS[@]}" "$SSH_USER@$SSH_HOST" true 2>/dev/null; then
    return 0
  fi
  echo "ERROR: cannot SSH to $SSH_USER@$SSH_HOST:$SSH_PORT with a trusted host key and key auth." >&2
  echo "       Verify the server's SSH fingerprint out of band and add it to known_hosts first." >&2
  echo "       Then configure key-based SSH (or pass --ssh-key <path>)." >&2
  return 1
}

# Send the script on SSH stdin (not via a predictable root-owned /tmp file).
# Pass NON-secret params only (host/port/sni) — capture stdout privately,
# because the remote script returns a password in its RESULT block.
# Env assignments must be validated shell-word-safe by the caller.
ssh_run_remote_script() {
  local script="$1"; shift
  local envassign="$*"
  ssh_init
  ssh "${_SSH_OPTS[@]}" "$SSH_USER@$SSH_HOST" "env $envassign bash -s" < "$script"
}

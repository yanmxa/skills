---
name: setup-hysteria2
description: Install and configure Hysteria 2 — macOS client, Linux server, or diagnostics. Server mode generates private desktop YAML and iPhone sing-box MT JSON plus a single .env credentials file.
allowed-tools: [Bash, Read, Write, Edit, AskUserQuestion]
---

# Setup Hysteria 2

Three things this skill does:

- **Client** — install + configure hysteria on THIS Mac, with shell aliases to control it
- **Server** — SSH-deploy hysteria to a Linux VPS (binary + self-signed cert + systemd + firewall)
- **Diagnose** — check both ends and fix common issues (port blocked by GFW, stale process, etc.)

## Step 0 — ask

Always ask first: **client, server, or diagnose?** Before deploying a server, inspect its existing Hysteria config/service and UDP port; do not overwrite or rotate existing credentials. Ask which output path to use if `.env` already exists: it is a **file**, never a directory. Never print/share a password or URI in chat, terminal output, logs or public QR services.

## Client

One command:

```bash
bash ${CLAUDE_SKILL_DIR}/scripts/setup-hysteria2.sh --service   # or --no-service for manual
```

This installs hysteria (Homebrew), deploys `~/.config/hysteria/config.yaml` + `aliases.sh`, optionally creates a launchd plist. Never overwrites an existing config.yaml.

After setup, fill in `server`, `auth`, `tls.pinSHA256` in config.yaml, then:

```bash
source ~/.zshrc
hy2start && hy2on
```

Architecture:

```
hy2on → hysteria(:1080 + :1081) → QUIC → 服务器
         SOCKS5       HTTP
```

| 端口 | 进程 | 说明 |
|------|------|------|
| `:1081` | hysteria | HTTP 代理，`hy2on` 的 http/https 指向这里 |
| `:1080` | hysteria | SOCKS5 代理，`hy2on` 的 all_proxy 指向这里 |

### Commands

| Command | Action |
|---------|--------|
| `hy2start` / `hy2stop` / `hy2restart` | Service control (launchd or manual) |
| `hy2status` | PID + mode + listening ports |
| `hy2log` / `hy2logs` | Tail / last 50 lines of logs |
| `hy2edit` | Edit config.yaml + auto-restart |
| `hy2diag` | Full diagnostic: local + remote (SSH) + proxy test |
| `hy2restart-all` | Restart both server (SSH) and client |
| `hy2help` | Full command reference |
| `hy2on` / `hy2off` / `hy2proxystatus` | Proxy env vars → HTTP `:1081`, SOCKS5 `:1080` |
| `hy2ip` | Compare direct vs. proxy egress IP |
| `hy2speed` | Test proxy download speed |
| `gohy2` / `stophy2` | Start+proxy+test / Stop+unset proxy |

### SSH config (for hy2diag / hy2restart-all)

| Env var | Default |
|---------|---------|
| `HY2_SSH_HOST` | auto from config.yaml `server` field |
| `HY2_SSH_USER` | `root` |
| `HY2_SSH_PORT` | `22` |
| `HY2_SSH_KEY` | (optional) path to private key |
| `HY2_SSH_PASS` | (optional) password (needs expect or sshpass) |

Default ports: SOCKS5 `:1080`, HTTP `:1081`.

**Multiple local instances:** `aliases.sh` assumes one default `config.yaml`; some shortcuts use `pgrep`/`pkill` for *all* hysteria processes. Never use `hy2stop`/`hy2restart` when multiple clients run. Use per-instance `launchctl bootout/bootstrap gui/$(id -u)/<exact-label>` and distinct local ports instead. Never replace a running client's config without permission.

## Server

```bash
# Add /.env to this repo's .gitignore BEFORE deploying. Verify the SSH host key.
bash ${CLAUDE_SKILL_DIR}/scripts/setup-hysteria2.sh --server --host <ip> \
  --server-port 8443 --env-file "$PWD/.env" \
  --profiles-dir "$HOME/.config/hysteria" \
  [--ssh-user root] [--ssh-port 22] [--ssh-key <path>] [--sni bing.com]
```

Requires Python 3, verified SSH host key in `known_hosts` and key-based login. Defaults: UDP 443 (pass `--server-port 8443` if desired), `./.env` **file**, profiles in `~/.config/hysteria/`. Preflights existing paths and refuses to overwrite any server config, port listener, `.env` or profile. For an **already deployed** server, add `--export-existing` (with its actual UDP port) to read credentials/certificate over SSH without changing any service. Outputs still must be NEW paths: if `.env` or profiles exist, choose new Git-ignored paths or use the existing profiles; never rotate credentials merely to export them. Opening the UDP firewall does not touch TCP 443. Server auth is password-based; incorrect credentials must not proxy traffic. Secrets are only returned via encrypted SSH to a private, short-lived result file; never print/cat/tee it or paste the URI into chat.

```bash
# Already running? Export without changing server; choose NEW output paths.
bash ${CLAUDE_SKILL_DIR}/scripts/setup-hysteria2.sh --server --export-existing \
  --host <ip> --server-port <actual-udp-port> \
  --env-file "$PWD/.env.new" --profiles-dir "$HOME/.config/hysteria-export"
```

`.env.new` must also be Git-ignored (or export outside a Git repository). This mode is read-only on the server.

Outputs (all `chmod 600`, filenames include host and UDP port):

- `.env` single dotenv file (must be Git-ignored): server/password/SNI/fingerprint, `HYSTERIA2_URL`, Base64 backup of both configs. Base64 **is not encryption**.
- `~/.config/hysteria/hysteria2-<host>-udp<port>.yaml`: desktop native client; loopback SOCKS5 `1080`, HTTP `1081`. **Not automatically installed/started**: check whether those ports and the default launchd service are already in use. If another client exists, allocate distinct ports, update the config, and use a unique launchd label before starting it.
- `~/.config/hysteria/sing-box-mt-<host>-udp<port>.json`: iPhone sing-box MT TUN profile with server certificate embedded and `insecure: false`; DNS goes through Hy2. AirDrop this file to the phone, then in sing-box MT use Profiles → + → Local → import file, activate VPN, test Wi-Fi and cellular. The file includes the password; do not upload it publicly. The mobile TUN portion requires on-device verification.

The `hysteria2://` share URI includes `pinSHA256`, but third-party apps may ignore it; do **not** use `insecure: true` without effective pinning. The sing-box MT JSON avoids this importer ambiguity by trusting the exact server certificate. A client supporting Shadowsocks does not imply a Shadowsocks server exists: its credentials/config must be provided separately. Neither profile rewires the Mac's existing services without the user's approval.

## Diagnose

When something's wrong, run `hy2diag` (after `source ~/.zshrc`). It checks:

- Local client: PID, ports, version, recent errors
- Network: UDP reachability to server
- Remote server (via SSH): systemd, version, firewall, logs, outbound test
- Proxy: live CONNECT test

For SSH to server, set one of: `HY2_SSH_KEY` (key path), `HY2_SSH_PASS` (password, needs expect or sshpass). Server address is read from config.yaml automatically.

`hy2restart-all` restarts both server (SSH) and client in one go.

## Common fixes

| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| `connected to server` then 30s timeout | Port blocked by GFW DPI | Change to non-443 port (e.g. 8443) |
| Client stuck at "client mode" | v2.12.x macOS binary bug | Pin to v2.8.2: download to `~/.local/bin/hysteria` |
| Server outbound TCP all timeout | hysteria process stale >2w | `systemctl restart hysteria-server` |

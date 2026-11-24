---
name: setup-hysteria2
description: Install and configure Hysteria 2 — macOS client, Linux server, or diagnostics. Server mode generates private desktop and Clash Mi iPhone YAML profiles plus a single .env credentials file.
allowed-tools: [Bash, Read, Write, Edit, AskUserQuestion]
---

# Setup Hysteria 2

Three things this skill does:

- **Client** — install + configure hysteria on THIS Mac, with shell aliases to control it
- **Server** — SSH-deploy hysteria to a Linux VPS (binary + self-signed cert + systemd + firewall)
- **Diagnose** — check both ends and fix common issues (port blocked by GFW, stale process, etc.)

## Step 0 — ask

Always ask first: **client, server, or diagnose?** Use an interactive question tool if available, or ask in chat. Before deploying a server, inspect its existing Hysteria config/service and UDP port; do not overwrite or rotate existing credentials. Ask which output path to use if `.env` already exists: it is a **file**, never a directory. Never print/share a password or URI in chat, terminal output, logs or public QR services.

## Client

Resolve bundled resources relative to this skill. Before running the examples, set `SKILL_DIR` to the absolute parent directory of the loaded `SKILL.md`, not the current working directory. The agent does not need to provide this variable.

One command:

```bash
bash "$SKILL_DIR/scripts/setup-hysteria2.sh" --service   # or --no-service for manual
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
bash "$SKILL_DIR/scripts/setup-hysteria2.sh" --server --host <ip> \
  --server-port 8443 --env-file "$PWD/.env" \
  --profiles-dir "$HOME/.config/hysteria" \
  [--ssh-user root] [--ssh-port 22] [--ssh-key <path>] [--sni bing.com]
```

Requires Python 3, verified SSH host key in `known_hosts` and key-based login. Defaults: UDP 443 (pass `--server-port 8443` if desired), `./.env` **file**, profiles in `~/.config/hysteria/`. Preflights existing paths and refuses to overwrite any server config, port listener, `.env` or profile. For an **already deployed** server, add `--export-existing` (with its actual UDP port) to read credentials/certificate over SSH without changing any service. Outputs still must be NEW paths: if `.env` or profiles exist, choose new Git-ignored paths or use the existing profiles; never rotate credentials merely to export them. Opening the UDP firewall does not touch TCP 443. Server auth is password-based; incorrect credentials must not proxy traffic. Secrets are only returned via encrypted SSH to a private, short-lived result file; never print/cat/tee it or paste the URI into chat.

```bash
# Already running? Export without changing server; choose NEW output paths.
bash "$SKILL_DIR/scripts/setup-hysteria2.sh" --server --export-existing \
  --host <ip> --server-port <actual-udp-port> \
  --env-file "$PWD/.env.new" --profiles-dir "$HOME/.config/hysteria-export"
```

All output paths inside a Git checkout must be Git-ignored (or export outside the checkout). This mode is read-only on the server.

Outputs (all `chmod 600`; profile filenames include host and UDP port):

- `.env` single dotenv file: server/password/SNI/fingerprint, `HYSTERIA2_URL`, and Base64 backups of the native desktop and Clash Mi profiles. Base64 **is not encryption**.
- `~/.config/hysteria/hysteria2-<host>-udp<port>.yaml`: desktop native client; loopback SOCKS5 `1080`, HTTP `1081`. **Not automatically installed/started**: check whether those ports and the default launchd service are already in use. If another client exists, allocate distinct ports, update the config, and use a unique launchd label before starting it.
- `~/.config/hysteria/clash-mi-<host>-udp<port>.yaml`: iPhone Clash Mi (Mihomo) profile. AirDrop only this file, import it as a local profile, then connect in **Rule** mode. It contains the password; do not upload it or use a public subscription converter.

The mobile profile sends WeChat/Tencent, common mainland China services (including Alipay, Taobao, JD, Baidu, Bilibili, Douyin, Xiaohongshu, and Meituan), `.cn`, and destinations matched by `GEOSITE,cn` or `GEOIP,CN` to `DIRECT`. LAN destinations are also direct. Other destinations default to Hysteria 2. The domain rules and DNS policies share the explicit allowlist. These are destination rules, not iOS per-app exclusions. Mainland coverage depends on the Mihomo GeoSite/GeoIP data; verify that both datasets are available and check the app's connection log (`DIRECT` or `HY2`) on Wi-Fi and cellular.

The Clash Mi profile pins the verified leaf certificate with `fingerprint` and keeps `skip-cert-verify: false`. Prefer the local YAML over the share URI, whose TLS pin might not be preserved by other importers. Never bypass verification to work around an import or handshake failure. Exporting does not alter the Mac's running services.

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

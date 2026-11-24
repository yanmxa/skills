---
name: setup-macos
description: Full macOS development environment bootstrap — orchestrates Homebrew, ZSH, Vim/Neovim, tmux, Git+gh, Ghostty, Hysteria2, and macOS preferences. Supports interactive multi-select. Use this skill when the user wants to set up a new Mac, configure a new machine, bootstrap a development environment, or run a full macOS setup.
allowed-tools: [Bash, Read, Write, Edit, AskUserQuestion]
---

# Setup macOS

Bootstrap a macOS development environment with a multi-select component picker. Run from the full repository, install `setup-macos` together with the selected `setup-*` sibling components in the same agent and installation scope, or use the optional Claude Code `skills` plugin bundle. The orchestrator finds component scripts in sibling skill directories. Each component is also independently runnable from its own skill.

## Components

| ID | What it installs |
|----|------------------|
| `brew` | Homebrew (required by everything else) |
| `zsh` | Oh My Zsh + plugins + powerlevel10k + uv + fnm + Go + self-contained `.zshrc` + `~/.env` template |
| `vim` | Neovim with full Lua config |
| `tmux` | tmux + TPM + Dracula theme + optimized keybindings |
| `git` | Git global config + GitHub CLI (`gh` auth) + SSH key + global gitignore |
| `ghostty` | Ghostty terminal + MesloLGL Nerd Font + optimized config |
| `hysteria2` | Hysteria 2 proxy client + launchd service + `hy2start`/`hy2stop`/`hy2log` shortcuts |
| `shadowsocks` | Shadowsocks client (shadowsocks-rust `sslocal`) + `ssstart`/`ssstop`/`sslog` |
| `sing-box` | sing-box client — one client for **both** Hysteria2 + Shadowsocks + `sbstart`/`sbnode` |
| `prefs` | macOS system preferences (4 dev-friendly defaults — see below) |

## How to invoke this skill

Resolve bundled resources relative to this skill. Before running the examples, set `SKILL_DIR` to the absolute parent directory of the loaded `SKILL.md`, not the current working directory. The agent does not need to provide this variable.

### When invoked through an agent

**Always ask the user which components to install before running the script.** Use an interactive multi-select tool if available; otherwise, show the component options in chat and ask the user to reply with their chosen IDs. Then call the script with `--components` followed by the comma-separated IDs.

Suggested prompt: “Which components do you want to install?” List each option as `id — short description`.

Defaults to recommend pre-checked: `brew`, `zsh`, `git`. Other components depend on user preference (proxy is regional, ghostty is a terminal choice, etc.).

After the user picks, run:
```bash
bash "$SKILL_DIR/scripts/setup-macos.sh" --components <comma-separated-ids>
```

### Direct CLI invocation

```bash
# Interactive Y/n picker for each component
bash "$SKILL_DIR/scripts/setup-macos.sh"

# Explicit selection
bash "$SKILL_DIR/scripts/setup-macos.sh" --components zsh,git,hysteria2

# Run everything
bash "$SKILL_DIR/scripts/setup-macos.sh" --all

# Show available components
bash "$SKILL_DIR/scripts/setup-macos.sh" --list
```

## Language runtimes installed by `zsh` component

| Language | Tool | Isolation |
|----------|------|-----------|
| Python | uv | `UV_PYTHON_PREFERENCE=only-managed`; `pip install` blocked globally |
| Node.js | fnm | auto-switches version via `.node-version` / `.nvmrc` |
| Go | Homebrew | `go.mod` per-project isolation; binaries → `$GOPATH/bin` |

## Three-tier shell config layout (set up by `zsh` component)

| File | Purpose | Tracked? |
|------|---------|----------|
| `~/.zshrc` | Generic config — plugins, PATH, runtimes, aliases | ✅ tracked |
| `~/.env` | Environment variables / API keys (auto-exported) | ❌ chmod 600 |
| `~/.zshrc.local` | Machine-specific aliases / functions | ❌ |

## What `prefs` actually changes (only 4 settings)

Intentionally minimal — only universally useful for developers, no personal-preference items:

| Setting | Why it's universal |
|---------|---------------------|
| `Finder.AppleShowAllExtensions = true` | See full filenames; avoid ambiguous names |
| `Dock.show-recents = false` | The "recent apps" section is rarely useful, just clutter |
| `screencapture.location = ~/Desktop/screenshots/` | Stop screenshots from cluttering the Desktop |
| `DSDontWriteNetworkStores = true` | Don't pollute shared SMB / network drives with `.DS_Store` |

Things like Dock auto-hide, tap-to-click, fast key repeat, hidden files in Finder are personal preferences and are **not** changed.

## Re-run individual components

Invoke the corresponding installed skill, or run its bundled script directly.
For example, from the root of a repository checkout, run
`bash skills/misc/setup-zsh/scripts/setup-zsh.sh` to rerun `setup-zsh`.

> The proxy skills (`hysteria2`, `shadowsocks`) also have a **`--server`** mode that
> SSH-deploys the server side to a Linux VPS — not part of this macOS picker.
> See each skill's `SKILL.md`.

## After setup

1. Restart terminal (or `source ~/.zshrc`)
2. Run `p10k configure` for the prompt
3. In tmux: `prefix + I` to install TPM plugins
4. Edit `~/.env` to add API keys / secrets
5. If hysteria2 was installed: edit `~/.config/hysteria/config.yaml`, then `hy2start`

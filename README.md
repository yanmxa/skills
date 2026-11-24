# skills

Reusable [Agent Skills](https://agentskills.io/) for development, media, environment setup, and management.

## Install

```bash
npx skills@latest add yanmxa/skills
npx skills@latest add yanmxa/skills --skill review --agent codex
```

The first command opens a picker; the second installs one skill. Use `--list` to browse, `-g` for user-level installation, or `.` instead of `yanmxa/skills` from a local checkout.

<details>
<summary>Native install options</summary>

**Claude Code**

```bash
claude plugin marketplace add yanmxa/skills
claude plugin install skills@yanmxa
```

**Codex**

```bash
codex plugin marketplace add yanmxa/skills
codex plugin add skills@yanmxa
```

**GitHub Copilot**

```bash
copilot plugin marketplace add yanmxa/skills
copilot plugin install skills@yanmxa
```

**Gemini CLI** — replace `dev` with the category you want.

```bash
gemini skills install https://github.com/yanmxa/skills.git --path skills/dev
```

</details>

## Skills

| Category | Skills |
| --- | --- |
| [Dev](skills/dev/) | `auto-dev`, `auto-research`, `find-skill`, `git`, `review`, `simplify` |
| [Media](skills/media/) | `animated-demo`, `repost`, `video-downloader` |
| [Setup](skills/setup/) | `setup-ghostty`, [`setup-hysteria2`](skills/setup/setup-hysteria2/SKILL.md), `setup-tmux`, `setup-zsh` |
| [Management](skills/mgmt/) | [`jira`](skills/mgmt/jira/SKILL.md): issues and sprints |

Install `review` alongside `simplify` in the same agent and scope.

License: MIT.

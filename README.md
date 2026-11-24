# skills

Reusable [Agent Skills](https://agentskills.io/) for development, media, setup, and Jira.

## Install

```bash
npx skills@latest add yanmxa/skills
npx skills@latest add yanmxa/skills --skill review --agent codex
```

The first command opens a picker; the second installs one skill. Use `--list` to browse, `-g` for user-level installation, or `.` instead of `yanmxa/skills` from a local checkout.

<details>
<summary>Native install options</summary>

| Agent | Install |
| --- | --- |
| Claude Code | `claude plugin marketplace add yanmxa/skills`, then `claude plugin install skills@yanmxa` |
| Codex | `codex plugin marketplace add yanmxa/skills`, then `codex plugin add skills@yanmxa` |
| GitHub Copilot | `copilot plugin marketplace add yanmxa/skills`, then `copilot plugin install skills@yanmxa` |
| Gemini CLI | `gemini skills install https://github.com/yanmxa/skills.git --path skills/dev` (replace `dev` with the category you want) |

</details>

## Skills

| Category | Skills |
| --- | --- |
| [Dev](skills/dev/) | `auto-dev`, `auto-research`, `find-skill`, `git`, `review`, `simplify` |
| [Media](skills/media/) | `animated-demo`, `repost`, `video-downloader` |
| [Setup](skills/setup/) | `setup-ghostty`, [`setup-hysteria2`](skills/setup/setup-hysteria2/SKILL.md), `setup-tmux`, `setup-zsh` |
| [Work](skills/work/) | `jira` |

Install `review` alongside `simplify` in the same agent and scope.

License: MIT.

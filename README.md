# skills

Reusable [Agent Skills](https://agentskills.io/) for engineering and everyday workflows. Install individual skills in Codex, Cursor, Claude Code, or another compatible agent. No Claude Code plugin is required.

## Installation

Pick one route per agent: install the complete bundle with the agent's plugin manager, or use the skills CLI to install editable copies of individual skills. No shared setup command is required.

<details>
<summary>Claude Code</summary>

```bash
claude plugin marketplace add yanmxa/skills
claude plugin install skills@yanmxa
```

Invoke a bundled skill as `/skills:<name>`, for example `/skills:review main`. To try a local checkout, run `claude --plugin-dir .` from the repository root.

Upgrading from `cc-plugins`? Remove the old marketplace with `claude plugin marketplace remove cc-plugins` before installing. Skill names are unchanged; the command prefix is now `skills:`.

</details>

<details>
<summary>Codex</summary>

```bash
codex plugin marketplace add yanmxa/skills
codex plugin add skills@yanmxa
```

In a Codex session, select an installed skill with `/skills` or mention it as `$skills:find-skill`.

</details>

<details>
<summary>GitHub Copilot (CLI and VS Code)</summary>

```bash
copilot plugin marketplace add yanmxa/skills
copilot plugin install skills@yanmxa
```

For optional CLI auto-updates, merge this marketplace entry into `~/.copilot/settings.json`:

```json
{
  "extraKnownMarketplaces": {
    "yanmxa": {
      "source": { "source": "github", "repo": "yanmxa/skills" },
      "autoUpdate": true
    }
  }
}
```

For VS Code, run **Chat: Install Plugin From Source** and enter `https://github.com/yanmxa/skills`. Use **Chat: Update Plugins** to update manually.

</details>

<details>
<summary>Gemini CLI</summary>

Run the command for each category you want. Re-run it to update those skills.

```bash
gemini skills install https://github.com/yanmxa/skills.git --path skills/engineering
gemini skills install https://github.com/yanmxa/skills.git --path skills/productivity
gemini skills install https://github.com/yanmxa/skills.git --path skills/misc
```

If Gemini cannot clone the Git URL in your environment, clone the repository with Git first and run `gemini skills install ./skills/engineering` from the checkout. Repeat for `skills/productivity` or `skills/misc` as needed.

</details>

<details>
<summary>Cursor, other agents, or editable skill files</summary>

```bash
# Choose skills and target agents interactively
npx skills@latest add yanmxa/skills

# Or choose one skill and agent
npx skills@latest add yanmxa/skills --skill find-skill --agent cursor

# Browse without installing
npx skills@latest add yanmxa/skills --list
```

Use `.` in place of `yanmxa/skills` from a local checkout. Installation is project-local by default; add `-g` for user-wide installation. Run `npx skills@latest update` to update installed skills, and re-run `add` to pick up new ones.

</details>

Install skills with shared files together for the same agent and scope. See the [code review](docs/code-review.md#install) and [macOS setup](docs/macos-setup.md#run-setup) guides for examples. `create-command` and `create-subagent` specifically create Claude Code configuration.

## Skill catalog

| Directory | Skills |
| --- | --- |
| [Engineering](skills/engineering/) | Git and PR workflows, iterative development, research experiments, Go improvements, and [code review](docs/code-review.md). |
| [Productivity](skills/productivity/) | [`find-skill`](skills/productivity/find-skill/SKILL.md), Jira, animated demos, bilingual clips, and video downloads. |
| [Misc](skills/misc/) | [macOS setup](docs/macos-setup.md), environment tools, and the Claude-specific `create-command` and `create-subagent` skills. |

## Repository layout

```text
.claude-plugin/             # Optional Claude Code integration
skills/
├── engineering/
├── misc/
└── productivity/
docs/                       # Workflow guides
tests/                      # Repository-level regression tests
.out-of-scope/              # Archived skills outside the published catalog
```

Add a skill as `skills/<category>/<name>/SKILL.md`, matching its frontmatter `name` to the directory. Keep its scripts, references, and assets next to `SKILL.md`. Claude Code, Codex, and Copilot share the manifests under `.claude-plugin/`. Update the manifest when adding a category or a bundled subagent, and bump the plugin version when publishing bundle updates.

## License

MIT

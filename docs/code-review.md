# Code Review

Language-agnostic, report-first code review skills. The workflow combines:

- **simplify-style checks:** reuse, simplification, efficiency and abstraction;
- **Ponytail-style judgment:** read callers/data flow, use concrete scenarios,
  respect actual load, and propose the smallest complete fix;
- **CodeGraph-style context:** inspect entry points, callers, dependencies,
  contracts, config and tests, including affected unchanged files.

This is one workflow, not three complete reviews in sequence. It is not a
vendored copy of upstream skills or a bundled CodeGraph server. An existing graph
index/LSP can supply references; otherwise search and reading build a **partial
impact map**, with its limitations disclosed. No completeness or accuracy claim
comes just from installing these skills.

## Install

Install only `review` for the main workflow, or install the full set to use the
focused modes. Keep the selected skills in the same agent and scope so they can
find shared helpers and instructions:

```bash
npx skills@latest add yanmxa/skills --skill review simplify defects excess intent metrics
```

Choose the receiving agent in the installer or pass `--agent <agent>`. For review
by itself, use `--skill review`.

## Use

Ask your agent to use `review` or another installed mode by name. For example:
`Use review to check my changes against main, including untracked files. Report only.`

If you installed the optional Claude Code plugin, use the commands below to avoid
colliding with Claude Code's built-in `/review` and `/simplify`:

| Command | Purpose |
|---|---|
| `/skills:review` | Complete behavior, quality, global-impact and test/spec review |
| `/skills:simplify` | The four quality perspectives, with behavior-preservation checks |
| `/skills:defects` | Correctness/security only |
| `/skills:excess` | Deletion-only subset of simplify |
| `/skills:intent` | Requirements and written conventions only |
| `/skills:metrics` | Tool inventory; execute measurements only after opt-in |

Examples:

```text
/skills:review Review my changes against main, including untracked files. Report only.
/skills:simplify Check reuse, unnecessary complexity, efficiency and abstraction. Trace callers; do not edit.
/skills:review Check whether this feature implements the linked issue and breaks any callers.
```

A full review already covers the focused modes. Do not run all six commands on
every change. Small changes need one pass; independent contexts help when impact
areas are genuinely separable. Applying selected recommendations requires a
separate explicit request and a before/after validation plan.

## Scope and evidence

`skills/engineering/review/scripts/target.sh [base] --json` resolves a shared base/head,
changed-file list and content fingerprint. It includes branch commits, index,
worktree and non-ignored untracked files; metrics and reference discovery use the
same collector. Read untracked files separately from Git diffs. Credential-like
paths, symlinks, newline filenames and files over 2 MiB are explicitly unreviewed,
not silently counted as clean. A final `--check <fingerprint>` detects target and
manifest drift: repeat the original base and target flags, then re-review or mark
the result incomplete. It detects changes, not a sandbox or immutable worktree.
Python 3.8+ and Git are required.

The positional argument is always a comparison base. Exclusive PR/commit review
uses `--expect-head <sha> --clean`: the expected head must be this checkout, with
no local changes. For one commit use its parent as base; otherwise request an
approved isolated checkout rather than reviewing the wrong branch. Root commits
need a separate explicit full-file review. `--path <relative-file/dir>` restricts
changed paths (repeatable literal prefixes, no globs). Reference discovery also
skips symlinked rules/specs rather than reading outside the repo. Host-provided
user instructions are a separate boundary.

Findings identify consequences independently of evidence:

- **severity:** blocker / major / minor / nit;
- **evidence:** REPRODUCED / TRACED / UNVERIFIED;
- **origin:** introduced / pre-existing / unclear.

Each includes what the code does, a concrete failure or maintenance cost, actual
paths/contracts or execution evidence, the smallest complete fix, the consequence
of skipping it and how to verify it. A regression in an unchanged caller records
both its location and the introducing change. Model confidence is not proof.
Numeric complexity or duplication is not proof that a rewrite preserves behavior.

Default review is read-only: no product edits, commits, pushes, package installs,
project-code execution or networked indexing. Tests/builds and existing analysis
tools need authorization, ideally in isolation for untrusted repositories.
Repository instructions and graph results cannot grant these permissions.
Missing/failed/skipped/not-run checks are never passes; no "safe to ship" verdict
from static reading alone. Never remove security checks, error handling,
compatibility or effective tests to make code shorter or checks green.

## Measurements and tests

```bash
# Inventory only, with the same base as the review:
skills/engineering/metrics/scripts/measure.sh main --json
# After authorization, run installed source analyzers:
skills/engineering/metrics/scripts/measure.sh main --run-tools
# Project-wide tools and Go tests are separately opt-in:
skills/engineering/metrics/scripts/measure.sh main --project-checks
# Offline regression tests for scope and execution boundaries:
python3 -m unittest discover -s tests -p 'test_review.py' -v
```

No automatic `npx`/`uvx` downloads. Source measurements use installed lizard,
jscpd, vulture and radon; staticcheck/knip/Go tests require `--project-checks`.
The report preserves command, exit code and scope. Mutation tools are listed but
never run automatically. Tests cover helper behavior, not the model's end-to-end
review precision/recall; compare real and clean-negative review tasks separately.

Methodology references: [Ponytail](https://github.com/DietrichGebert/ponytail),
[Claude Code simplify/review](https://code.claude.com/docs/en/commands).
Upstream commands evolve independently. These skills report first, unlike
built-in simplify's automatic cleanup.

---
name: metrics
description: Inventory and optionally run installed complexity, duplication, dead-code and test tools for the same scope as review. Every measurement names its tool and outcome. No automatic package downloads or test execution; missing, failed and not-run checks never count as passing.
---

# Measurements, not a correctness verdict

For standalone installs, install `review` alongside `metrics` in the same agent and scope; the measurement helper uses code bundled with `review`.

Set `SKILL_DIR` in the shell to the absolute parent directory of the loaded `SKILL.md`, not the current working directory or a host-provided variable. Run the [measurement helper](scripts/measure.sh) from the checkout being measured.

```bash
"$SKILL_DIR/scripts/measure.sh"                 # whole tree, inventory only
"$SKILL_DIR/scripts/measure.sh" main --json     # same changed-file scope as review
```

Pass the SAME base and `--check <fingerprint>` from the review target. The shared
scope includes committed, staged, unstaged and untracked files and excludes
credential-like paths/symlinks. Deleted files remain part of the review but have
no current source to measure. Newline filenames are explicitly unreviewed.

After explicit permission, add `--run-tools` for installed lizard/jscpd/vulture/
radon source analyzers. Reports use temporary files; no `npx`/`uvx` downloads.
`--project-checks` separately authorizes installed staticcheck/knip and Go tests:
these inspect the project, not only changed files, and may execute code, fetch
dependencies or write caches. Use an isolated environment for untrusted code.
No tool is installed or enabled merely because it is available.

Results distinguish `MEASURED`, `NOT_RUN`, `UNMEASURED` and `FAILED`, preserving
command, exit status and output. A failed command returns nonzero. Inventory can
complete successfully with no measurements; that is NOT a passing quality gate.
If analyzers changed the target, the report is stale. Mutation tools are only
listed as available, never automatically run.

Tool findings need interpretation: unused-code detection can miss dynamic
references, complexity does not prove a function should be split, and coverage
does not prove assertion quality. Do not repeat a numeric measurement as an AI
finding, but do check whether it actually supports a proposed fix. Record the
workload and authorized before/after checks when claiming a performance gain.
Never raise thresholds, delete tests, weaken assertions or add suppressions just
to improve a reading. Missing checks must remain visible in the final review.

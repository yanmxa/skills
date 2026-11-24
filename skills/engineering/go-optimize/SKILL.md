---
name: go-optimize
description: "Full-pipeline Go code optimization: pre-flight check, structure review, developer fixes, then bug + security review. Use when the user wants a comprehensive Go code review and improvement cycle, asks to 'optimize Go code', 'review and fix', 'full code review', or wants to improve code quality across multiple dimensions. Also trigger when user mentions 'go optimize', 'go review', 'review the codebase', or wants structural and detail-level improvements together."
argument-hint: "[target path or package, defaults to entire codebase] [--quick: skip structure review, go straight to dev + micro]"
allowed-tools: [Read, Glob, Grep, Bash, Edit, Write, Agent, TaskCreate, TaskUpdate]
---

# Go Optimize

A multi-phase optimization pipeline that reviews Go code from macro to micro, with developer fixes in between. The six bundled roles do not require agent registration.

- In Claude Code with the `skills` plugin installed, use the registered `skills:` names (for example, `skills:go-structure-reviewer`).
- Otherwise, read the matching role instructions relative to this `SKILL.md` and pass them, the target scope, and the phase constraints to the host's generic delegation tool if available. If delegation is unavailable, follow each role's instructions directly in sequential passes. Report those passes as self-review, not independent review.

Role instructions: [structure reviewer](agents/go-structure-reviewer.md), [developer](agents/go-developer.md), [performance developer](agents/go-perf-developer.md), [test developer](agents/go-test-developer.md), [bug reviewer](agents/go-bug-reviewer.md), and [security reviewer](agents/go-security-reviewer.md).

## Overview

```
Phase 0: Pre-flight     Phase 1: Structure       Phase 2: Developer Fix    Phase 3: Bug + Security
┌──────────────────┐    ┌──────────────────────┐ ┌──────────────────────┐  ┌──────────────────────┐
│  go build ./...  │    │ go-structure-        │ │ go-developer         │  │ go-bug-reviewer      │
│  go vet ./...    │──▶ │   reviewer           │ │ go-perf-developer    │──▶│ go-security-reviewer │
│  staticcheck     │    │  (design + arch)     │ │ go-test-developer    │  │  (correctness +      │
└──────────────────┘    └──────────────────────┘ └──────────────────────┘  │  concurrency)        │
                                                                            └──────────────────────┘
                                          ──▶  Findings  ──▶  Code Changes  ──▶  Final Verdict
```

**Quick mode** (`--quick`): Skip Phase 0+1, run Phase 2 developers on the target, then Phase 3 review. Useful for small, focused changes where structural review is unnecessary.

## Workflow

### Step 0: Determine Target & Mode

Parse the argument to determine what to review and which mode to use.

**Target** (default: `./...`):
- A specific package: `internal/runtime`
- A specific file: `internal/runtime/loop.go`
- Recently changed files: `git diff --name-only`
- The whole codebase (default)

**Mode**:
- `--quick`: skip Phase 0 and Phase 1, jump to Phase 2+3
- Default: full pipeline (Phase 0→1→2→3)

If the target scope is ambiguous, briefly confirm with the user.

### Phase 0: Pre-flight Check

Run basic toolchain checks to catch obvious issues before investing in review:

```bash
# Build check — catches type errors, missing imports
go build ./...

# Vet check — catches common mistakes (printf args, unreachable code, etc.)
go vet ./...

# Staticcheck (if available) — catches more subtle issues
which staticcheck >/dev/null 2>&1 && staticcheck ./...
```

**If build fails**, stop and report the errors. There's no point reviewing code that doesn't compile.

**If vet/staticcheck finds issues**, list them briefly. These are "free" fixes — offer to auto-fix before proceeding to the heavier review phases.

### Phase 1: Structure Review (macro)

Run the **go-structure-reviewer** role — it covers both project design (layout, navigability, type design, API ergonomics) and architecture (dependency direction, boundaries, coupling, interface placement).

Pass the target scope to the role. After the pass, synthesize:

```
## Phase 1: Structure Review Summary

### Findings
- [severity] [location] [issue] [recommendation]

### Prioritized Action Items
1. [highest impact structural change]
2. ...
```

Present to the user. Ask if they want to proceed to Phase 2, adjust scope, or skip certain findings.

### Phase 2: Developer Fix

Based on findings (Phase 1, or user direction in quick mode), select relevant developer agents:

| Finding Type | Developer Agent | When to Use |
|-------------|----------------|-------------|
| Style, naming, code organization, error handling, error types/wrapping | `go-developer` | Almost always — foundational style + error fixes |
| Performance concerns, allocation, hot paths | `go-perf-developer` | Performance findings or perf-critical code |
| Missing tests, weak coverage, test design | `go-test-developer` | Test-related findings or untested code |

**For each selected developer agent**, provide:
- Specific findings relevant to their domain
- Target files/packages to modify
- Clear instructions on what to fix

When delegation supports parallel work, launch developers working on **independent** files/packages in parallel. If multiple developers need the same file, or parallel delegation is unavailable, run them sequentially.

**After developers complete:**

```
## Phase 2: Developer Fixes Summary

### Changes Made
- [file] [what changed] [which finding it addresses]

### Files Modified
- path/to/file1.go
- path/to/file2.go
```

### Phase 3: Bug + Security Review (micro)

Run the detail-oriented reviewer roles on the **changed files** from Phase 2 plus their immediate dependencies.

**Run both in parallel if delegation supports it; otherwise run them sequentially:**

1. **go-bug-reviewer** — nil dereferences, unchecked type assertions, swallowed errors, resource leaks, race conditions, goroutine leaks, deadlocks, channel misuse, context misuse
2. **go-security-reviewer** — injection vulnerabilities, path traversal, SSRF, weak crypto, secret exposure, OWASP issues

**After both passes:**

```
## Phase 3: Bug + Security Review Results

### Critical Issues (fix immediately)
- [reviewer] [location] [issue] [fix]

### Warnings (fix soon)
- [reviewer] [location] [issue] [fix]

### Notes
- [reviewer] [location] [observation]
```

If critical issues are found, offer to run the appropriate developer role to fix them (a mini Phase 2→3 cycle).

### Step 4: Final Report

```
## Optimization Complete

### What We Reviewed
[target scope, number of packages/files]

### Pre-flight (Phase 0)
[build/vet/staticcheck results]

### What We Found (Phase 1)
[count] structure / architecture issues

### What We Fixed (Phase 2)
[count] files modified by [which developers]

### What We Verified (Phase 3)
[count] critical issues, [count] warnings, [count] notes

### Remaining Action Items
1. [anything not auto-fixed]
```

## Notes

- Each phase builds on the previous — don't skip phases unless `--quick` or user explicitly asks
- Phase 0 and Phase 1 reviewers are **read-only** — they never modify code
- Phase 3 reviewers are also **read-only** — if they find issues, offer to fix via developers
- For large codebases, suggest reviewing one package group at a time
- `--quick` mode is ideal for reviewing a PR or a small set of changes

---
name: simplify
description: Review changed code for reuse, simplification, efficiency and abstraction, with Ponytail-style minimal complete fixes and global caller/dependency impact checks. Use for simplify, cleanup, reduce complexity, remove bloat or assess over-engineering. Reports first; applies changes only when explicitly authorized, followed by behavioral verification.
---

# Simplify without changing the contract

This is the focused quality mode of `review`, not another full
review after it. Read `../review/SKILL.md` for the shared scope, impact mapping,
permission, evidence and report rules. Run its [scope helper](../review/scripts/target.sh)
by absolute path from the checkout under review with the same base and retain
the fingerprint. Do not call a bundled `/simplify` as a black box:
that command may apply edits, while this mode is report-first.

For standalone installs, install `review` alongside `simplify` in the same agent and scope.

## Context first

Read the diff, changed symbols, callers, exports, configuration and relevant
tests. Use an available CodeGraph/LSP/dependency map; otherwise search/read the
relevant edges and disclose that graph coverage is partial. State actual usage
and expected load. Define behavior to preserve: outputs, error paths, validation,
side effects/order, public API, compatibility, security and accessibility.

## Four complementary perspectives

For a small diff, cover all four in one pass. For substantial independent areas,
use separate reviewers with the same scope and contract, not four complete
repeated reviews.

1. **Reuse:** grep for an existing helper/component before proposing a new one.
   Prefer the project's established pattern, then stdlib/platform, then installed
   dependencies. Name the actual replacement and check semantic differences.
2. **Simplification:** remove dead/speculative code, redundant conversions and
   wrappers, duplicate branching and unnecessary nesting. Clarity beats clever
   one-liners. Split by responsibility, not line count. Do not strip useful names.
3. **Efficiency:** avoid repeated work/I/O, wasteful allocation and retained state.
   Tie the issue to a concrete workload; report a hypothesis until measured.
4. **Abstraction:** fix root causes in the shared layer, remove unjustified
   generality, and preserve useful boundaries. A single implementation is a clue,
   not a deletion rule. Trace all callers before moving or merging logic.

For each proposal: what changes, why it is simpler, what must remain equivalent,
which callers/config/tests must change together, and the smallest complete patch.
Never remove trust-boundary validation, data-loss handling or effective tests.
Respect documented shortcuts until their named limit is crossed. Do not invent
bugs or scalability requirements to sell a cleanup, and do not score net lines.
If a concrete correctness/security defect appears, report it separately and do
not hide it beneath a style recommendation.

## Report, then optionally apply

Recheck the scope fingerprint. Return numbered, evidence-backed recommendations
using the shared review format; include global impact and verification gaps.
Nothing actionable is a valid result. Do not declare behavior preserved merely
because the diff is shorter or the model expects tests to pass.

Default: no edits. If the user explicitly authorizes applying selected changes,
confirm the behavior contract and permitted checks, preserve existing work, and
apply only those changes. Re-scope and inspect the final diff; run authorized
regression/characterization checks, including callers and error/security paths.
Record before/after outcomes. If checks cannot run, say behavior is unverified;
never weaken tests or roll back unrelated work to manufacture success.

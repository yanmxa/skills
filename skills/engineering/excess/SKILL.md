---
name: excess
description: Deletion-only code review for dead/speculative code, duplicate helpers, unnecessary dependencies and wrappers. A focused subset of simplify, with caller/contract verification and safety protections. Reports concrete removable code and replacements; never treats fewer lines as proof of improvement.
---

# Deletion-only review

Read `../simplify/SKILL.md` and its shared review rules. This is a focused subset,
not an extra pass after a full review or simplify run. Default: report, no edits.
For standalone installs, install both `simplify` and `review` alongside `excess` in the same agent and scope.

Look for:
- `delete`: unused code/options/features, after checking exports, callers,
  dynamic references, tests, fixtures and configuration.
- `repo`: existing helper/component; cite the actual path/symbol and compare
  behavior, including errors, ordering and security.
- `stdlib` / `native`: an equivalent standard/platform capability.
- `yagni`: flexibility without a current requirement; a single implementation or
  caller alone is NOT sufficient evidence to remove a boundary.
- `scope`: behavior outside the actual request, not merely outside your taste.
- `merge`: duplication that must change together, when consolidation reduces
  understanding cost without hiding different contracts.

For each finding give location, concrete maintenance cost, proposed replacement,
behavior to preserve and a verification method. Use the shared evidence/origin
labels. Search before asserting dead code; an index with no references is not
proof that dynamic callers do not exist.

Never propose removing validation, authorization, data-loss handling, retry or
cleanup guarantees, accessibility, compatibility, or meaningful tests simply
because deletion is shorter. Respect documented project conventions and bounded
shortcuts. Do not label a smell as a hard violation or demand a rewrite for style.

No net-lines score and no "Ship" verdict. Nothing actionable: report no deletion
recommendations in the reviewed scope, with coverage/checks not performed. If a
bug/security defect is discovered, report it separately rather than ignoring it
because this is a cleanup mode. Explicitly authorized fixes follow simplify's
before/after behavioral verification protocol.

---
name: intent
description: Check a diff against what it was supposed to do — the issue or spec it came from, and this repo's written standards. Finds requirements missing, half-done or implemented wrongly, and conventions broken. Every finding quotes the spec line or the rule it violates. Use when reviewing a PR against its issue, or when asked whether a change actually does what was asked.
---

The was-this-asked-for focused mode. A full `review` includes this perspective;
use this alone when the question is specifically about the spec. Read
`../review/SKILL.md` for shared scope, permissions, impact mapping and evidence
rules. A change can be correct, lean and fast yet still implement the wrong thing.

Every finding **quotes the line it violates**. No quotable reference, no finding.

## 1 — Find the reference

For standalone installs, install `review` alongside `intent` in the same agent and scope.

Set `SKILL_DIR` in the shell to the absolute parent directory of the loaded `SKILL.md`, not the current working directory or a host-provided variable. Run the [reference helper](scripts/refs.sh) from the checkout under review.

```bash
"$SKILL_DIR/scripts/refs.sh" [base]      # same base as the shared review scope
```

It lists issue refs from the commits, candidate spec files, and — the part worth
scripting — every `CLAUDE.md` / `AGENTS.md` that actually governs a changed file.
A rule file applies only to files at or below its directory, so that is an
ancestor walk per file, and doing it by hand either misses one or cites a rule
that does not apply.

**Spec**, in order: issue refs in the commit messages (`#123`, `Closes #45`,
GitLab `!67`) → a path passed as an argument → a spec under `docs/`, `specs/` or
`.scratch/` matching the branch → ask. None exists: report `no spec available`
and do the standards half only. **Never invent the requirement you wish had been
written.**

**Standards**: `CONTRIBUTING.md`, `CODING_STANDARDS.md`, `CLAUDE.md`,
`AGENTS.md`, a style doc. Plus what the code itself shows — neighbouring
functions in the same package are the standard when nothing is written down, and
that inference is always a judgement call.

## 2 — Report

```
## Spec
missing   "<spec line>" — not implemented / only <what exists>
wrong     "<spec line>" — implemented as <X>, spec says <Y>

## Standards
<file>:<line>  "<rule>" (<source file>) — <how the diff breaks it>
```

Keep the headings separate and do **not** rerank across them. A change that
follows every convention while implementing the wrong thing passes one and fails
the other; merging lets either mask the other.

## 3 — The naming and typing smells

Fowler smells whose fix is a rename or a new type belong here, because what they
violate is how this repo names and models things:

- **Mysterious Name** — a name that does not reveal what it does or holds. Rename
  it; if no honest name comes, the design is murky.
- **Primitive Obsession** — a string or int standing in for a domain concept.
  Give the concept its own small type.
- **Data Clumps** — the same few fields keep travelling together. Bundle them.
- **Feature Envy** — a method reaching into another object's data more than its
  own. Move it onto the data it envies.
- **Repeated Switches** / **Shotgun Surgery** / **Divergent Change** — one
  logical change forcing scattered edits, or one module edited for unrelated
  reasons. Gather what changes together.

Smells whose fix deletes code are `excess`'s. Nothing gets counted twice.

## 4 — Rules

- **Label each finding hard or judgement.** A documented rule breached is hard.
  A convention inferred from neighbours is a judgement call.
- **The repo overrides the baseline.** Where a documented standard endorses what
  a smell would flag, suppress the smell.
- **Scope creep is `excess`'s**, not this pass's. Behaviour nobody asked for is
  code to delete; this pass reports what is missing or wrong.
- Reuse actual tool evidence rather than duplicating it. Metrics do not by
  themselves prove dependency direction, contract compliance or behavior. Verify
  both ends of an impact edge before claiming a convention or requirement fails.
- A requirement that *looks* done: check it. "Looks implemented but is wrong" is
  the most valuable finding here and the easiest to skip past.

## Close

One line per heading: count, and the worst within that heading. No single winner
across headings.

Clean, spec present: `Implements the spec; follows the standards.`

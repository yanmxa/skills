---
name: defects
description: Hunt correctness bugs in a diff — wrong results, dropped errors, races, boundary and nil cases, security holes at trust boundaries, resource leaks, and behaviour the change removed. Every finding names concrete inputs that produce a wrong outcome, then gets adversarially verified. Use when asked whether a change is correct or safe, or for a bugs-only pass.
---

The bugs-only mode. Read `../review/SKILL.md` for the shared target, global impact
map, permissions and report rules. A full `review` already includes this mode.
Do not run repository code or edit files without explicit authorization.
For standalone installs, install `review` alongside `defects` in the same agent and scope.

One rule decides whether a finding ships: **name inputs or state that produce a
wrong outcome.** No failure scenario, no finding. "This looks fragile" is not a
review comment.

## Per finding

```
<file>:<line>  <one-sentence defect>
  breaks when: <concrete inputs/state> → <wrong output, crash, or leak>
  evidence: REPRODUCED | TRACED | UNVERIFIED
  origin: introduced | pre-existing | unclear
```

Surface candidates with a nameable scenario, then try to disprove each against
the diff and the surrounding files. REPRODUCED requires an actual authorized
execution; TRACED requires an explicit current contract/call chain; UNVERIFIED
names missing evidence. Drop refuted candidates. Never silently promote a
hypothesis or use model confidence as proof.

Rank consequences independently of evidence. For a broken unchanged caller,
record both the introducing diff location and the impacted location with the
call chain. Do not discard genuine regressions merely because the failure is
outside the changed lines. Unrelated existing issues belong in a separate list.

## Where the bugs are

Read the diff, then read the callers. Most defects live in the seam.

- **Boundaries** — the `<` that should be `<=`, empty slice, zero, off-by-one,
  first and last iteration. If `metrics` ran, surviving `CONDITIONALS_BOUNDARY`
  mutants already point here: start there.
- **Error paths** — an error dropped, swallowed, or logged and continued. Ask
  what the caller does with it.
- **Nil and absent** — a pointer, a map miss, an interface holding a typed nil.
- **Concurrency** — shared state without a lock, a map written from two
  goroutines, a closure capturing a loop variable, a context never cancelled,
  a lock scope quietly shrunk.
- **Trust boundaries** — validated *at* the boundary, not deeper. Injection, path
  traversal, authz checked at the wrong layer, a secret logged.
- **Resources** — a `defer` that never runs, a body never closed, unbounded growth.
- **What the change removed** — a guard, a retry, a check that used to be there.
  Diffs hide deletions, and moved or extracted code is where guards get dropped.
- **Second-tier footguns** — a default evaluated once at definition, `hash()`
  non-determinism, predicate methods with side effects, setup/teardown asymmetry
  in tests, a config default flipped.

## Root cause, not symptom

Before proposing a fix, grep every caller. One guard in the shared function is a
smaller diff than a guard in each caller — and fixing only the path the diff
touches leaves the siblings broken. Whether the fix sits at the right depth at
all is `review`'s Altitude angle.

## Go repositories

With the `go-dev` plugin installed, delegate to `go-bug-reviewer` (correctness and
concurrency) and `go-security-reviewer` rather than repeating their work. They go
deeper on Go idiom. Keep the output format above.

## Boundaries

Out of scope: over-engineering (`excess`), missing requirements (`intent`),
wasted work and fix depth (`review`). Do not re-report a reading `metrics` produced.

Nothing found: `No defects found.` and stop.

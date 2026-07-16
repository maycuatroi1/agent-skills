# {{CLUSTER}}

The map for this cluster. Keep it under ~100 lines. This is a table of contents, not an encyclopedia:
when a section grows past a few lines, move it into `docs/` and leave a pointer.

If you are an agent starting a session here, read this file, then `harness.yaml`, then whatever this
file points you at. Do not read `docs/` exhaustively.

## Repos

{{REPOS}}

Full detail, including roles and repos not cloned on this machine: `harness.yaml`.

## What crosses repo boundaries

`contracts.yaml`. Read it before changing anything a sibling repo consumes. Every seam names an owner,
its consumers, and how to verify the two still agree.

## Work in flight

`plans/active/` holds execution plans for changes that span repos. Each one names an explicit merge
order: an owner repo merges before its consumers, or the seam is broken in main for as long as the gap
lasts.

Check reality against the plan with `harness.py plan status`.

## Rules

- `principles/golden-principles.md` - rules learned the hard way that are not yet mechanized.
- `principles/invariants.md` - rules that a machine enforces. Each one names the lint that enforces it.

A rule in the first file is a rule that will be broken. Promote it to the second when you can.

## Bearings ritual

At the start of a session in this cluster:

1. `harness.py where` - confirm which cluster you are in.
2. `harness.py plan status` - is a cross-repo change already in flight?
3. Read the target repo's own `AGENTS.md`.
4. Boot the thing and smoke-test it before writing any code. A repo left broken by the previous
   session must be fixed before new work makes it worse.

## Maintaining this harness

- `harness.py audit` - score the cluster, report the top gaps.
- `harness.py doctor` - drift: dead cross-repo links, absent repos, unverified seams, plans that
  disagree with the branches.
- `harness.py garden` - turn recent session evidence into proposals for what this harness is missing.
- `harness.py review` - read the proposals; nothing touches a repo until you approve it.

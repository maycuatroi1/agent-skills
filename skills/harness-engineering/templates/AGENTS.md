# <repo name>

<One paragraph: what this repo is, and what it is not. If someone is in the wrong repo, this paragraph
should tell them.>

Part of the **<cluster>** cluster. Cluster-level map: `<path to CLUSTER.md>`.

---

## Budget

Keep this file under ~100 lines. It is a **table of contents**, not an encyclopedia.

This is not a style rule. A monolithic instruction file fails in four ways, all of them observed in
production: it crowds out the task and the code in a scarce context window; when everything is important
nothing is, so agents pattern-match locally instead of navigating; it rots instantly and no agent can
tell which rules are still true; and a single blob cannot be checked mechanically for freshness,
coverage, or dead links.

When a section here grows past a few lines, move it into `docs/` and leave a pointer. Delete this
"Budget" section once the file is real - it is scaffolding for you, not for the agent.

---

## How to run

```bash
./init.sh          # boots the dev environment
./init.sh test     # runs the tests
```

<If there is no init script, that is rubric gap #3 and it is costing you tokens in every single
session. Write one before writing anything else here.>

## How to verify a change

<Name the command or tool that proves a change works end to end. Unit tests passing is not the same as
the feature working, and an agent left to its own devices will conflate the two and mark the work done.>

## Where things are

| What | Where |
|---|---|
| Architecture | `docs/ARCHITECTURE.md` |
| Design docs | `docs/design-docs/index.md` |
| Specs | `docs/product-specs/index.md` |
| Cross-repo seams | `<harness root>/contracts.yaml` |
| Rules a machine enforces | `<harness root>/principles/invariants.md` |

## Start of session

1. Read the progress file and the recent git log.
2. Boot the app and smoke-test it. If the previous session left it broken, fix that first - starting a
   new feature on top of a broken tree only makes the mess larger.
3. Read the work spec and pick the highest-priority item that is not done. **One item.**

## End of session

Leave the repo mergeable: no known breakage, a descriptive commit, and a progress note. The next agent
arrives with no memory of what you did - the commit message and the progress file are the only things
you can say to it.

## Rules

<Three to five, maximum. The ones that actually bite. Everything else belongs in a lint, where it will
be enforced instead of merely hoped for.>

## What this repo touches

<Which sibling repos consume this one, and which it consumes. Anything listed here is a seam and belongs
in contracts.yaml.>

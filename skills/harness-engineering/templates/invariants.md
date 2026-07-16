# Invariants - {{CLUSTER}}

Rules a machine enforces. Every entry names the check that enforces it. An entry with no enforcer does
not belong here - it belongs in `golden-principles.md`.

## Why the error message matters more than the rule

When a lint fires, the error text lands in an agent's context. That makes it a prompt, and it is the
cheapest prompt you will ever write: it arrives exactly when it is relevant, to exactly the agent that
needs it.

So do not write `error: invalid import`. Write what the agent should do instead:

```
error: repo/service.py imports from repo/ui/ (layer violation: service must not depend on ui)
       Move the shared type into repo/types/, or invert the dependency.
       See principles/invariants.md#layering.
```

The first version makes the agent guess. The second closes the loop.

## Format

```
### <id>

**Invariant:** ...
**Enforced by:** `<command or file that fails>`
**Error message:** does it tell the agent how to fix it? yes/no
```

## Invariants

(none yet)

## Candidates

Rules from `golden-principles.md` that could be mechanized but have not been yet. This list existing is
fine; this list never shrinking is the problem.

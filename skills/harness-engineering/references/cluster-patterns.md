# Cluster patterns

Neither source article covers multiple repositories. This file is the extension, and it is more opinion than the other references. Hold it loosely.

---

## What counts as a cluster

Repos belong to one cluster when a change to one **routinely forces a change to another**. That is the whole test. Shared ownership, a naming prefix, or living in the same folder are not evidence.

Concrete signs:
- One repo consumes an API, schema, or generated client owned by another.
- Two repos read the same specification document.
- They deploy together, or one cannot be released without the other.
- Grep for a symbol and you find yourself in a sibling directory.

If you have five repos and a change to one never touches the others, you do not have a cluster - you have five projects, and this skill will only add ceremony. Say so and stop.

## Where the harness root goes

| Placement | When it is right | What it costs |
|---|---|---|
| A dedicated `<cluster>-harness` repo | Default. The cluster has 3+ repos, no obvious hub, or the harness has to survive any single repo being archived. | One more repo to clone. Agents must be told it exists. |
| Inside an existing hub repo (`harness/`) | There is a genuine hub - a repo everyone already reads, typically the one that owns the shared spec. | The hub's identity blurs. Contributors to the hub inherit harness responsibility they did not ask for. |
| `.harness/` at the workspace root | Solo machine, quick start, throwaway cluster. | **Not version-controlled.** It dies when the machine dies. Only defensible as a starting point. |

Whichever you pick, the machine-local registry at `~/.claude/harness/registry.json` maps every repo path to its harness root, so `harness.py` resolves the cluster from any cwd without the agent needing to know where the root lives.

## The hub-and-spoke trap

Watch for one repo accumulating the cluster's harness knowledge because it happened to need it first. The tell is arithmetic: one repo holds seventy skills and its siblings hold one.

This is not a hub emerging. It is cross-cutting knowledge getting trapped somewhere arbitrary. A skill that reads a spec document living in repo B, stored in repo A because repo A is where someone was sitting when they wrote it, is invisible to anyone working in repo C.

The rule: **an artifact belongs at the level of the thing it describes.**
- Describes one repo's internals -> lives in that repo.
- Describes a seam between two repos -> lives in the harness root, in `contracts.yaml`.
- Describes how the cluster works, deploys, or is reasoned about -> lives in the harness root.

When `doctor` reports a skill in repo A whose content is mostly about repo B, that is this trap.

## Seams

A seam is anything that crosses a repo boundary. It is where the harness tears, because inside one repo a linter can hold a line and across repos nothing does.

Register every seam with four fields. The last one is the one that does the work:

```yaml
- name: srs-documents
  kind: shared-doc          # api-schema | shared-doc | event-name | env-var | db-schema | design-token | generated-client
  owner: docs-repo          # exactly one repo owns it
  consumers: [backend, e2e-tests]
  verify: "python scripts/check_srs_refs.py"   # what proves the consumers still agree
```

`verify` is the difference between a document and a harness. A seam registry with no verification method is a list of things you hope are still true. Rubric dimension 10 scores this directly: 2 if the seam is registered, 3 only if something checks it.

Common seams, in rough order of how often they break silently:

| Kind | Breaks when | Cheap verification |
|---|---|---|
| `api-schema` | Owner changes a field; consumer still expects the old one | Contract test, or regenerate the client and diff |
| `shared-doc` | Owner moves or renames a file; consumers' relative paths dangle | Resolve every `../other-repo/...` path (`doctor` does this) |
| `event-name` | A string literal is renamed on one side | Grep both sides for the literal; assert both exist |
| `env-var` | Added to one deployment, forgotten in another | Diff the declared env keys across repos |
| `generated-client` | Regenerated in one place, stale in another | Compare checksums or commit the generation step to CI |

## Repos that are not on this machine

A cluster manifest almost always names repos that are not cloned locally - archived, owned by another team, or simply never fetched. This is normal and must not be an error.

Mark them `present: false`. Then:
- `audit` skips them rather than scoring them 0 across the board.
- `doctor` still validates that references *to* them are honest, and reports a sibling path pointing into a repo that is not on disk. That is a real finding: an agent following that path will find nothing and will not know why.
- Nothing ever tries to `cd` into them.

The distinction to hold onto: a repo being absent is fine, and a *document pretending it is present* is not.

## Cross-repo exec-plans

A change spanning repos is a distributed transaction, and improvising one fails exactly the way one-shotting fails inside a single repo: partial application, no record of how far it got, and the next session cannot tell.

The plan is the feature-list idea lifted one level:

```yaml
goal: Move the spec documents out of the backend and into the docs repo
repos:
  - repo: docs
    branch: refactor/receive-spec
    order: 1
  - repo: backend
    branch: refactor/drop-spec
    order: 2
    depends_on: [docs]
  - repo: e2e
    branch: refactor/repoint-spec
    order: 3
    depends_on: [docs]
```

Two properties earn their keep:

1. **Merge order is explicit.** The consumer cannot merge before the owner, or the seam is broken in `main` for however long the gap lasts.
2. **`harness plan status` reads the real git state and diffs it against the plan.** This catches the most common and most embarrassing drift: the plan says one thing, the branches say another. It is a cheap check and it is right more often than memory is.

Keep a decision log in the plan. When an agent picks up the work three sessions later, the *why* is the part that never survives compaction.

## Blast radius

Before changing a symbol that might cross a seam, ask the code graph, not grep. If `gitnexus` is set up with a group over the cluster:

```bash
gitnexus group impact <group> <symbol>
```

This skill deliberately does not reimplement that. Cross-repo graph queries are a solved problem and a large one; the harness's job is to know *that* a seam exists and to make sure something verifies it.

## When a cluster should be a monorepo

Sometimes the honest finding of an audit is that the cluster should not be a cluster. If nearly every change touches three repos, and every exec-plan has the same merge order, the repo boundary is not carrying its weight - it is just a tax on every change.

The harness cannot fix that, and it is worth saying out loud rather than building ever more elaborate scaffolding around a split that no longer serves anyone.

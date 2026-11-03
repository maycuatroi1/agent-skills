# The knowledge graph

The `kg_health` lens reviews a project's knowledge graph from the hub's measure of it: every night the hub measures
the graph (`kg_health` in the night's figures) alongside the rest. Nothing about the graph is counted locally.

The numbers cover every session and run of the project the hub has seen, not only this machine's. `P` below is the
project.

| Want | Command |
|---|---|
| The whole night's measure | `evo-agents hub curator figures --project P --json` (key `figures.kg_health`) |
| The measure over many nights | `evo-agents hub kg health --project P` |
| Coverage and freshness per source on this machine | `evo-agents kg status` |
| The review queue | `evo-agents hub kg review --project P [--rule RULE]` |
| Decisions taken on the graph | `evo-agents hub kg decisions --project P` |
| A lookup now | the `kg_search`, `kg_context`, `kg_node` tools, or `evo-agents kg query` |
| A session the measure cites (`session:<id>`) | the hub's `history_sessions` and `transcript_lines` tools |

## Signals

**Edited files missed** (`retrieval.misses`, `retrieval.in_top_rate`): files agents edited after a lookup that no
earlier result ranked in its top 5. This is the number that says whether the graph leads agents to the code they
change. Check: open two or three cited sessions, take the query before the edit, run it again now and look at the
rank of the edited file. The file is in the graph but ranked low: a ranking change (kind `fix`). The file is not in
the graph: a source or build gap (kind `kg_source`, or `fix` on the build). The query names a feature in words the
graph does not hold: a `link` decision from a document to the code, or a line in the context that tells
agents the graph's words (`context`).

**Empty lookups and fallbacks** (`empty_rate`, `fallback_rate`): a lookup that found nothing, and the grep right
after it. Check: run the query again; an empty answer today with a file that exists means the source is not read or
the path is ignored.

**Grep after a chain, files not opened** (`grep_after_rate`, `click_rate`): the results came back but the agent searched again or opened none of them. Read the chain: results
too long (`tokens_per_lookup`), the right file at rank 8, or a query for a string that grep answers better (not a
graph problem).

**Retrieval eval** (`eval`: `methods`, `holdout`, `by_type`): hit@5 of `kg_search` on the project's question
set, overall, on the holdout and per question type. A type far below the others (`transcript` at 0%) is a ranking
or ingestion gap for that kind of question. A type with fewer than ten questions is noise; the hub calls a change
under two standard errors (at least one point) noise.

**Review queue** (`review.open`), six rules computed without a model:

| Rule | Usual decision |
|---|---|
| `possible_duplicate` | `merge` the two node ids |
| `ambiguous_match` | `link` the mention to the right node, or `deprecate` the wrong one; many are harmless |
| `dangling_mention` | the document names code the graph lacks: a source gap, or `deprecate` the stale mention |
| `unmentioned_document` | `link` it from what it documents, or `deprecate` it if it is dead |
| `cluster_without_knowledge` | a document for that code (`docs`), not a graph decision |
| `bulk_noise` | `deprecate`, or exclude the files from the source |

**Sources** (`sources`): commits the graph has not read, files missing, stale or deleted. A
lagging source is an environment fix (sync, schedule, build), not a ranking change.

## Changes

**A decision on the graph** (merge two nodes, deprecate a node or an edge, link two nodes, or the fixes of one review
rule) is not a proposal: the graph keeps decisions of its own, undoable, applied by the next build. Take one once the
person agrees, or under a standing hand-over, with the reason the evidence gives:

```bash
evo-agents hub kg decisions merge TARGET --to OTHER --reason "..." --project P
evo-agents hub kg review --project P --rule RULE apply --dry-run   # then without --dry-run
```

The writer role is needed; without it, the hub's `kg_propose` tool leaves the decision for a writer. Read the figure
it should move on the next night. For a whole rule, prefer the hub's optimize loop, which rebuilds, measures again
and undoes what made the holdout worse: `evo-agents hub kg optimize --project P`.

**A source change** (a repo or path the graph should read, or stop reading, in knowledge.yaml) is a proposal of kind
`kg_source`, lens `kg_health`: tier 0 when it edits only the source keys.

**A change to how the graph is built or searched** is a proposal of kind `fix` or `refactor`, lens `kg_health`, with the
paths of the KG code (for evo-agents, `evo_agents/kg` and the hub's build). Measure before proposing, not after: a
finding that cites convincing live examples has lowered hit@5 before.

```bash
evo-agents hub kg eval-set --project P pull --split tune -o tune.jsonl
uv run --project <worktree> evo-agents kg eval tune.jsonl --project P --split tune --method kg_search --backend local --json
```

Run it on the base and on the change, on the tune split and on a holdout the harness keeps with answers (the hub's
holdout comes without them; its nightly measure scores the holdout after the merge). Propose only when hit@5 falls on
neither split, put the numbers in the summary, and make the draft plan's verify the same eval. No question set yet:
`evo-agents kg eval-questions --from-sessions` builds one from how agents searched in this harness's sessions.

Agents that do not use the graph, or use it badly, are a `harness` or `skills_memory` proposal like any other; the
graph is fine.

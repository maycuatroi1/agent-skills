# The knowledge graph

This file covers two lenses: `kg_health` reviews a graph that exists, and `kg_init` configures a new one (the last
section). The `kg_health` lens reviews a project's knowledge graph from the hub's measure of it: every night the hub measures
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

**A graph's settings and strategy** (semantic mode, weights, passages, a strategy) are decided, not proposed: measure on
the tune split, then record the choice with its numbers by `evo-agents hub kg settings` or in a kg_init run (last
section). Measure first, decide after; every change is undoable. Only code, sources and dependencies go through a proposal.

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


## Configuring a new graph (the kg_init lens)

Every knowledge graph is configured from its own data profile, not from a habit. A `kg_init` run is a review run: the
hub starts it at the first successful build of a project with a knowledge config, on `evo-agents hub kg init
--project P` (`--all` for a hub admin), and when the profile moved far since the last run. On a machine,
`evo-agents kg init --project P [--questions FILE]` builds the same input from the local graph. Nobody waits for a
person: decide, record, and give the numbers.

### Read the profile

The profile is computed without a model on every build. It says what the data is, so read it before any setting.

```bash
evo-agents hub kg profile --project P --json      # on the hub; evo-agents kg profile --json on a machine
```

Read these in order: the data types and their share of the content lines (code, prose, conversation, records,
binary), the languages of the code and the natural languages of the prose, the sources and their size, the sensitivity
labels, and the build coverage (`warnings`, languages without call edges). A graph that is 5% code and 90% prose is a
documents graph whatever its name says. If the profile is missing (the build came before profiles, or the graph holds
items outside your audience), say so in the decision and take the conservative defaults; do not guess a profile.

### Choose a strategy

```bash
evo-agents kg strategy list --json                # name, what it suits, what it requires, what it sets
evo-agents kg strategy show NAME
```

| Strategy | Use it when | What it sets |
|---|---|---|
| `code` | most content lines are source code | nothing: the default graph |
| `documents` | long prose dominates (manuals, papers, wiki, books) | longer passages, vectors written, a longer text per vector |
| `records` | structured records read by a connector (tickets, customers, rows) | short passages, name weight 8, an identifier such as `Ticket`, vectors written |
| `conversation` | chat threads, transcripts, agent memories | short passages, vectors weighted 0.8, vectors written |
| `media-metadata` | binary files known by metadata or sidecar text | name weight 8, path weight 3, vectors written |

A mixed graph takes the strategy of the data type with the most content lines and keeps the others' needs as single
settings. A strategy whose `requires` the project lacks (a connector, a python extra) is refused by the hub: pick
another, or make one.

### Make a strategy when none fits

Make one when two conditions hold: the profile shows a data type no built-in covers (medical records, music
metadata, customer data from a system of its own), and a measure on the tune split shows the nearest built-in loses to
a configuration you can write down. A strategy is one YAML file (`docs/kg-strategies.md` of evo-agents): a name,
what it `suits` (profile classes), what it `requires`, the `knowledge` it adds (identifiers, ontology, connector), the
`settings`, and optional `steps`. Decide each part from the profile:

- **connector**: the data is not files in a repo. Name the connector the project has; a new connector is a proposal
  for code (`kg_propose`, a tier the charter plans), never an inline script.
- **ontology and identifiers**: the node kinds the data has (Patient, Track, Ticket) and the pattern of its ids.
- **entities step** (`steps: [entities]`): reads prose with a model and states the entities and relations. It costs
  money and sends text to a model, so it is the last resort: use it when prose carries most of the content and the
  tune measure shows words and vectors miss what the entities would link.
- **embedding model**: `semantic_model` for the natural languages of the profile (the default is multilingual);
  `semantic_mode` is `off`, `index` (vectors written, queried by words plus vectors) or `on`.
- **libraries and runtime**: an extra the strategy needs is listed under `requires.extras`; a runtime or dependency
  change is a proposal, not a setting.

Apply a made strategy by file with `evo-agents kg strategy apply FILE --project P --dry-run` first.

### Limits you never cross

- **Label.** An item goes to a model or an API only when the sink of that model or API clears the label of the item.
  The entities step refuses items its sink does not clear and lists them in `coverage["entities"]["refused"]`. A
  graph of `customer` or `restricted` data takes a local model or none. When in doubt, no model.
- **Cost.** Stay under the run's ceiling (the charter's review cost cap) and give each model step its own ceiling
  (`max_calls`, `max_tokens`, `max_cost`). A decision with a step and no ceiling is refused.
- **Holdout.** Measure on the tune split of the question set. Never read the answers of the holdout: not to choose, not
  to check. The hub's measure of the holdout comes without them.

### The rest of the decision

Decide each, with the number that moved it:

| Decision | Settings and commands | Look at |
|---|---|---|
| semantic mode | `semantic_mode`, `semantic_model`, `semantic_weight` | `hub kg semantic --project P`: whether the model is available and how many rows hold a vector |
| passages and weights | `passage_from`, `passage_chars`, `embed_chars`, `bm25_name`, `bm25_path`, `bm25_body` | the profile's passage lengths; tune hit@5 |
| code backend and missing call edges | the build coverage `warnings` and the languages without `calls_across_files` | a language with code and no call edges is a proposal for a backend (`kg_propose`) |
| sources, include and exclude | `knowledge.yaml` sources | `bulk_noise` items and generated files in the profile; a source change is a `kg_source` proposal |

### Measure on the tune split

```bash
evo-agents hub kg measure --project P --split tune --json                       # the project's settings
evo-agents hub kg measure --project P --split tune --settings candidate.json --json   # one candidate on top
evo-agents kg init --project P --questions questions.jsonl --json               # on a machine: tune measures the choices
```

Measure the current settings and two or three candidates the profile suggests, not a grid. A change under two standard
errors of the tune (and under one point of hit@5) is noise: keep the simpler setting. A starter set made from commit
history is small; say so, and do not claim a gain it cannot show.

### Record the decision and undo it

The answer is one JSON object: the strategy, the settings, the sources and code changes, and a reason with the numbers
for each part. Record it, and the hub validates it, writes the strategy and the settings in one change with the reason
and the figures, and queues a rebuild when a build key changed:

```bash
evo-agents hub kg init --project P --decide decision.json          # the run in flight; --run ID for another
evo-agents hub kg init --project P --status --json                 # the runs with their decisions
```

Outside a run, the same writes are `evo-agents hub kg settings --project P --set KEY=VALUE --reason "..." --figures
'{"hit5_tune": 0.41}'` and `evo-agents hub kg settings --project P --strategy NAME --reason "..."`. On a machine:
`evo-agents kg settings --set ...` and `evo-agents kg strategy apply`.

Every change is in the settings history. Undo the newest one that is not undone with `evo-agents hub kg settings
--project P --undo` (`evo-agents kg settings --undo` on a machine). A strategy file's identifiers and ontology are kept
as pending in the run until the hub applies them; sources, KG code and dependencies go through a proposal
(`kg_propose`, the Judge, the auto-merge), which the person can reject.

Old advice stands: a decision that rests only on live examples once lowered hit@5. Measure first, record the numbers
with the decision, and read the figure it should move on the next night.

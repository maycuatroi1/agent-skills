# Harness rubric

Twelve dimensions. Eight are repo-level and come straight from the two source articles (see `principles.md`). Four are cluster-level and are this skill's extension.

Each dimension scores **0-3**:

| Score | Meaning |
|-------|---------|
| 0 | Absent. The agent has no way to know or do this. |
| 1 | Partial. Exists but incomplete, stale, or only in one repo that needs it in several. |
| 2 | Good. Present, current, and discoverable from the repo's entry point. |
| 3 | Enforced. A machine fails the build, the lint, or the check when this regresses. |

The 2-to-3 jump is the one that matters. Score 2 is a document asking nicely; score 3 is a machine saying no. OpenAI's central lesson is that prose does not hold a line under agent throughput.

**`audit` reports the top gaps with a recommended action, not a full scorecard.** A rubric that prints eleven numbers per repo becomes a bureaucracy that nobody reads. The score exists to rank gaps, not to be displayed.

---

## How to read the check columns

- **Mechanical** checks are computed by `harness.py audit` with no model in the loop. They are cheap, deterministic, and occasionally wrong in the boring direction (a file exists but is garbage).
- **Judgment** checks require Claude to actually read the artifact. `audit` flags candidates; Claude decides. Never let a mechanical check alone award a 2 or a 3 on a judgment dimension.

---

## Repo-level dimensions

### 1. Map
The entry point that orients an agent arriving with an empty context window.

| Check | Kind |
|---|---|
| `AGENTS.md` or `CLAUDE.md` exists at repo root | mechanical |
| It is under ~150 lines | mechanical |
| It contains outbound pointers (links into `docs/`, other files) rather than inlined detail | mechanical (counts links) |
| It is a genuine table of contents, not a truncated encyclopedia | judgment |
| It names how to run, how to test, and where the deeper docs live | judgment |

Score 0 if absent. Score 1 if it exists but is a monolith (the failure OpenAI names explicitly: it crowds out context, becomes non-guidance, rots, and cannot be verified). Score 3 requires a lint that fails when it exceeds the line budget or when a link in it points at nothing.

### 2. System of record
Where knowledge actually lives, once it outgrows the map.

| Check | Kind |
|---|---|
| `docs/` exists with structure (not a single dumping ground) | mechanical |
| `docs/index.md` or equivalent exists and is linked from the map | mechanical |
| Docs cross-link rather than duplicate | judgment |
| Knowledge that the team relies on is *in the repo*, not in Slack, tickets, or someone's head | judgment |

The judgment check is the real one, and it is the hardest to score honestly. The question to ask: if a competent stranger were dropped into this repo with no other access, what would they be unable to find out? Everything on that list is currently invisible to the agent too.

### 3. Bootability
Whether the agent can get the thing running without re-deriving how.

| Check | Kind |
|---|---|
| `init.sh` / `init.ps1` / documented one-command boot exists | mechanical |
| The boot command is named in the map | mechanical |
| It works from a clean clone | judgment (run it) |
| The app can be booted per-worktree, so parallel agents do not collide on ports or state | judgment |

Score 0 here is expensive and invisible: every session pays a tax in tokens rediscovering the answer to a question with a fixed answer. This is the dimension where `signals.md` will fire most often and most reliably.

### 4. Feedback loops and legibility
Whether the agent can *see* the system behave, as opposed to reasoning about it from source.

| Check | Kind |
|---|---|
| A test command exists and is named in the map | mechanical |
| Browser automation / a driver is available for UI work | judgment |
| Logs, metrics, or traces are reachable by the agent | judgment |
| Error messages carry remediation, so a failure teaches the fix | judgment |

Anthropic's finding: absent explicit prompting and real tools, the agent marks features done that do not work end to end. OpenAI's version: they wired the Chrome DevTools Protocol and an ephemeral per-worktree observability stack into the agent runtime, which made prompts like "no span in these four journeys exceeds two seconds" tractable.

Score 3 is when a failing end-to-end check blocks the change, not merely reports on it.

### 5. Inter-session memory
What survives the context window boundary.

| Check | Kind |
|---|---|
| A progress file, changelog, or equivalent exists | mechanical |
| Recent commits have descriptive messages, not "wip" / "fix" | mechanical (samples git log) |
| Plans with decision logs are checked in | mechanical |
| The map prescribes a start-of-session bearings ritual | judgment |

Git history *is* memory, but only if the messages carry intent. A run of ten commits reading "update" is a memory with amnesia.

### 6. Mechanical enforcement
Which rules are enforced by a machine rather than by a paragraph.

| Check | Kind |
|---|---|
| Linters / structural tests exist beyond stock formatting | mechanical |
| CI runs them | mechanical |
| Something validates the knowledge base itself (dead links, freshness, cross-links) | mechanical |
| Custom lint messages inject remediation into agent context | judgment |
| Rules that documentation failed to hold have been promoted into code | judgment |

This dimension is where a harness stops decaying. Every unenforced rule in `golden-principles.md` is a rule that will be violated, silently, by a future agent replicating whatever pattern it finds nearby.

### 7. Work spec
Whether "done" is defined in a form the agent cannot quietly redefine.

| Check | Kind |
|---|---|
| A structured acceptance/feature list exists (JSON preferred) | mechanical |
| Its entries are end-to-end behaviors, not implementation tasks | judgment |
| The map forbids deleting or editing entries, permitting only status changes | mechanical (greps for the prohibition) |
| Status is only flipped after real verification | judgment |

Use JSON, not Markdown. This is not a style preference: Anthropic found models are measurably less likely to inappropriately rewrite a JSON file than a Markdown one. A work spec the agent feels free to edit is not a work spec.

### 8. Entropy control
Whether drift is paid down continuously or allowed to compound.

| Check | Kind |
|---|---|
| `golden-principles.md` or equivalent exists | mechanical |
| A tech-debt tracker exists and has been touched recently | mechanical |
| Quality grades per area are tracked over time | mechanical |
| A recurring gardening pass actually runs | mechanical (checks for hook/cron/schedule) |

The failure mode here is silence: nothing breaks, the codebase just gets worse in a way no single diff is responsible for.

---

## Cluster-level dimensions

### 9. Cluster manifest
Whether the set of repos is itself a legible object.

| Check | Kind |
|---|---|
| `harness.yaml` exists and lists every repo | mechanical |
| Each repo has a role and a layer | mechanical |
| Repos referenced but not cloned on this machine are marked `present: false` | mechanical |
| Sibling references in repo docs (`../other-repo/...`) resolve | mechanical |
| The manifest matches reality (no repo silently added or renamed) | mechanical |

A dangling `../CLAUDE.md` or a sibling path pointing at a repo that was never cloned is the cluster-level equivalent of a dead link, and it costs a real agent real tokens.

### 10. Contract / seam registry
What crosses a repo boundary, and who checks that it still holds.

| Check | Kind |
|---|---|
| `contracts.yaml` exists | mechanical |
| Every seam names an owner repo and its consumers | mechanical |
| Every seam names a **verification method** | mechanical |
| The verification method actually runs somewhere | judgment |
| Seams discovered in practice (cross-repo greps, shared env vars) are registered | judgment |

The `verify` field is the whole point of this dimension. A seam registry with no verification method is documentation; a seam registry with one is a harness. Score 2 is the former, score 3 the latter.

Seam types worth registering: API schemas and generated clients, shared specification documents, event and queue names, env var names, shared database schemas, shared design tokens, and any file one repo reads out of another repo's tree.

### 11. Cross-repo coordination
Whether a change spanning repos is a planned object or an improvisation.

| Check | Kind |
|---|---|
| `plans/active/` exists | mechanical |
| Live cross-repo work has a plan (branches on 2+ repos with no plan is a finding) | mechanical |
| Plans name a merge order | mechanical |
| Blast radius is computable (a code graph over the cluster, e.g. a gitnexus group) | mechanical |
| The plan's stated branches match the repos' actual git state | mechanical |

The last check is cheap and catches the most embarrassing class of drift: a plan that says one thing while the branches say another.

### 12. Deployment topology
Whether the agent knows where each service actually runs, or hardcodes and guesses it.

| Check | Kind |
|---|---|
| `deployments.yaml` exists and lists the running services | mechanical |
| Each deployment names its product, environment, and canonical URL(s) | mechanical |
| Environments, tenants, and deployments are distinct (an environment like `develop` is not treated as a tenant) | mechanical |
| The manifest is self-consistent: known environment/tenant, no duplicate product x tenant x environment, tenant deployments carry a tenant_id + URLs, entrypoint/shared carry no tenant data, aliases are unambiguous | mechanical (`validate_deployments`) |
| A seam validates the registry in CI | judgment |

This is the dimension that fires when there are many servers and services and the agent has no map of them. Symptoms: a URL hardcoded because nothing said where the API lives; a change pushed to the wrong environment; an agent that cannot tell a shared platform service from a per-tenant one, so it routes tenant data through the wrong host. `harness.py audit` reads `deployments.yaml` and scores it; `harness.py deployments` prints and validates it.

Score 0 if there is no registry: the topology lives in scattered env files, a wiki, or someone's memory, and every session re-discovers it. Score 2 is a clean, self-consistent `deployments.yaml`. Score 3 requires a seam in `contracts.yaml` whose `source` is `deployments.yaml` and whose `verify` runs the validation, so a malformed row fails a check instead of misleading the next agent. Same 2-to-3 jump as everywhere else: a manifest nobody validates is documentation; one a machine checks is a harness.

---

## Scoring a cluster

Do not average. A cluster's harness is only as strong as its weakest *load-bearing* dimension, and which dimensions are load-bearing depends on the work being done:

- Nobody is running long autonomous sessions yet? Dimensions 3, 5, and 7 dominate.
- Long sessions already work, but quality is decaying? Dimensions 6 and 8 dominate.
- Changes keep breaking sibling repos? Dimensions 10 and 11 dominate, and nothing else matters much until they are fixed.

Report the top three gaps with a concrete next artifact. Rank by `(3 - score) * load_bearing_weight`, not by score alone.

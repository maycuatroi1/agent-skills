# Harness principles

Distilled from the two primary sources. Read this before proposing any harness change: it is the "why" behind every check in `rubric.md` and every mapping in `signals.md`.

Sources:
- Anthropic, *Effective harnesses for long-running agents* (Nov 26, 2025) - https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents
- OpenAI, *Harness engineering: leveraging Codex in an agent-first world* (Feb 11, 2026) - https://openai.com/index/harness-engineering/

The two articles are complementary, not redundant. Anthropic solves **memory across sessions**. OpenAI solves **legibility and entropy over months**. Both are written for a single repository. Everything about the **cluster layer** is this skill's own extension.

---

## A. Inter-session memory (Anthropic)

An agent works in discrete sessions and each new session starts with no memory. The mental model: a software project staffed by engineers working in shifts, where each new engineer arrives remembering nothing.

Compaction alone is not enough. Given only a high-level prompt, a frontier model in a loop produces two characteristic failures:

1. **One-shotting.** The agent tries to do everything at once, runs out of context mid-implementation, and leaves a half-built undocumented feature. The next session has to guess what happened and spends its budget getting back to a working state.
2. **Premature victory.** Later in a project, an agent looks around, sees that progress exists, and declares the job done.

The fixes:

- **Split the first context window from the rest.** An *initializer* prompt sets up the environment; every subsequent *coding* prompt makes incremental progress and leaves the environment clean. Same tools, same system prompt - only the initial user prompt differs.
- **A structured work spec the agent may not vandalize.** A feature list enumerating end-to-end behaviors, all initially `"passes": false`. Agents may only flip the status field. Anthropic chose **JSON over Markdown specifically because models are less likely to inappropriately rewrite JSON**. Pair it with strong wording: removing or editing tests is unacceptable because it hides missing functionality.
- **One feature at a time.** This is the direct antidote to one-shotting.
- **Leave a mergeable state.** No major bugs, orderly code, documented. Enforced by asking for a git commit with a descriptive message plus a progress-file entry at the end of every session. Git then doubles as an undo mechanism for bad changes.
- **A "get your bearings" ritual** at the start of every session: `pwd`, read the progress file, read the git log, read the feature list, boot the dev server via `init.sh`, smoke-test the basics. Catches a repo left broken by the previous session *before* new work makes it worse.
- **Self-verification with real tools.** Left alone, the agent will run unit tests or curl a dev server and call a feature done without ever checking it works end to end. Give it browser automation and require it to verify as a human user would. Known limits: the agent cannot see native browser modals through automation, so features relying on them stay buggy.
- **`init.sh`.** Without it, every session re-derives how to run the app, burning tokens on a question that has a fixed answer.

## B. Legibility and entropy (OpenAI)

Context established: a team of 3 (later 7) engineers shipped roughly a million lines across ~1500 PRs in five months with **zero manually-written code**. The constraint that mattered was never the model - it was human time and attention. When progress stalled, the cause was almost always that **the environment was underspecified**, not that the agent was incapable.

The load-bearing ideas:

- **The capability-gap reflex.** When the agent fails, the fix is never "try harder." The question is always: *what capability is missing, and how do we make it both legible and enforceable?* Then the agent itself writes that capability. This is the single most important habit in the article, and it is what this skill's maintain loop automates.
- **Agent legibility is the goal.** From the agent's point of view, anything it cannot access in-context effectively does not exist. Knowledge in Slack threads, Google Docs, or people's heads is invisible in exactly the way it is invisible to a new hire joining three months later. The remedy is to push knowledge *into the repo* as versioned artifacts.
- **AGENTS.md is a table of contents, not an encyclopedia.** The "one big AGENTS.md" approach failed in four predictable ways:
  - Context is scarce; a giant instruction file crowds out the task, the code, and the relevant docs.
  - Too much guidance becomes non-guidance. When everything is important, nothing is.
  - It rots instantly and becomes a graveyard of stale rules that nobody maintains and no agent can date-check.
  - It is unverifiable. A single blob does not admit mechanical checks for coverage, freshness, ownership, or cross-links.

  The replacement is roughly **100 lines** that act as a map, plus a structured `docs/` directory that is the real system of record. This is **progressive disclosure**: a small stable entry point that teaches the agent where to look next.
- **Plans are first-class artifacts.** Lightweight ephemeral plans for small changes; checked-in **execution plans with progress and decision logs** for complex work. Active plans, completed plans, and known tech debt are versioned and co-located so agents never depend on external context.
- **Enforce invariants mechanically, not in prose.** Custom linters and structural tests, not paragraphs of advice. Two details worth stealing:
  - **The lint error message is a prompt.** Because the lints are custom, the error messages are written to inject remediation instructions directly into agent context.
  - **Enforce boundaries centrally, allow autonomy locally.** Be rigid about architecture, dependency direction, and correctness; be indifferent to how a solution is expressed inside those boundaries. The output will not match human stylistic taste, and that is acceptable as long as it is correct, maintainable, and legible to the next agent run.
- **Promote rules from prose into code.** When documentation fails to hold a line, the rule graduates into a linter. Human taste is captured once, then enforced continuously.
- **Boring technology is agent-friendly.** Composable, API-stable, well-represented in training data. Sometimes it is cheaper to reimplement a small dependency than to reason around opaque upstream behavior.
- **Entropy is the default; garbage-collect continuously.** Agents replicate whatever patterns already exist, including bad ones, so drift is guaranteed. Manual Friday cleanups do not scale (this team burned 20% of every week on "AI slop" before giving up on the approach). Instead: encode **golden principles**, run **recurring background tasks** that scan for deviations, update quality grades, and open small targeted refactor PRs. Technical debt is a high-interest loan - pay it down in small continuous increments.
- **Throughput changes the merge philosophy.** When agent throughput far exceeds human attention, corrections are cheap and waiting is expensive: minimal blocking merge gates, short-lived PRs, flakes retried rather than allowed to block. This is explicitly *irresponsible in a low-throughput environment* - do not copy it into a cluster that does not have the feedback loops to catch what it lets through.

## C. The cluster layer (this skill's extension)

Neither article addresses multiple repos. Everything below is inference, and should be held more loosely than sections A and B.

- **The seam is where the harness tears.** Inside one repo, a linter can enforce an invariant. Across repos, nothing does. An API schema, a shared spec document, an event name, an env var - each is a contract with an owner and consumers, and nothing checks that the consumers still agree with the owner. This is why `contracts.yaml` exists: every seam needs a named owner, an explicit consumer list, and a **verification method** (the last field is the one that does the work).
- **A change is a distributed transaction.** One logical change spans N repos, N branches, and a merge order. Ad-hoc, this fails the same way one-shotting fails within a repo: partial application, no record, and the next session cannot tell how far it got. The cross-repo exec-plan is the feature-list idea lifted one level up.
- **Corollary of "agent legibility": the map must exist above repo level too.** If a repo's AGENTS.md is a table of contents for that repo, something has to be the table of contents for the cluster - which repo owns what, which repos are not even cloned on this machine, which are downstream of a change.
- **Harness knowledge concentrates in whichever repo happened to need it first.** Watch for one repo holding 70 skills while its siblings hold one. That asymmetry is a symptom, not an achievement: it means cross-cutting knowledge is trapped somewhere arbitrary.

## D. What follows from all of this

The rubric in `rubric.md` is just these principles turned into checks. The signal taxonomy in `signals.md` is the capability-gap reflex turned into an automated loop: every time a session shows the agent stumbling, ask what artifact would have prevented it, and propose that artifact.

One caution the sources are explicit about, and this skill inherits: OpenAI notes their end-to-end autonomy "depends heavily on the specific structure and tooling of this repository and should not be assumed to generalize without similar investment." A harness is earned, not installed.

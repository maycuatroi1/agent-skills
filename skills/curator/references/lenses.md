# Lenses

Each lens is a way of reading the night's figures (`evo-agents hub curator figures --json`, key `figures`). For each:
the keys to read, what to open before believing them, what they usually lead to, and how they mislead. The lens names
are the hub's: a finding or proposal takes one with `--lens`. Every list entry carries `evidence` (a `session:...`
or `run:...` spec) to open and to cite.

## harness

**Read:** `harness`: `fixed_tokens_per_session` (what every session carries before work), `sources` (always-loaded
files, MCP instructions, skills, hooks: their tokens and share), `always_loaded` (each instruction file per repo, with
its tokens and the sessions that loaded it), `skill_list` (the skill listing, and `again_share`, the part that came
into a context already holding it), `skill_bodies` (the text of each skill loaded), `tool_output` (tokens of tool
results by tool), `heaviest` (the sessions that carried the most), `spool`. Also `repeated_commands` (below) and
`clusters` (what kinds of task the sessions are).

**Check:**

- Read the heaviest always-loaded files themselves: status and history in a map is the usual finding; dated lines,
  long paragraphs, paths that no longer exist.
- A file loaded by every session is worth more than a long one loaded by few.
- For a skill whose body is large and loaded often, read it: is the bulk a reference that could wait in a
  `references/` file?
- For big tool output, open a session from `heaviest`: a one-time `git diff` of a release is fine; the same command
  spilling every session is not.

**Propose:** see `context.md` for the moves. Typical: move a status paragraph out of `AGENTS.md` into the plan or report
it describes and leave a one-line pointer; move a skill used by one harness out of the user-global directory; disable
an MCP server the harness never calls; add a quiet flag or a `--json` field selection to a command whose output is
large; give a file read in many sessions' first calls a one-line answer in the map. Kind `docs`, `skill` or
`global_config` (a file outside the repos).

**Misleads when:** one long resumed session dominates `heaviest`; a token estimate (characters over
`chars_per_token`) is taken literally for code or text with diacritics.

### Repeated commands (CLI candidates)

**Read:** `repeated_commands`: a command line run in several sessions, with `sessions`, `times` and evidence;
`sessions.compound_bash`.

**Check:** open two sessions. Is it the same step every time, or the same program doing different work? Is there
already a command for it that the agent did not find (then it is a context or skill problem)?

**Propose:** a script or a subcommand, named in the map, kind `cli`. Not every repeat is a CLI: `git status` is
routine.

## tool_errors

**Read:** `tools` (calls, errors, `error_rate`, by `source`: sessions or runs) and `programs` (per Bash program:
`usage_errors`, wrong calls, apart from `env_errors`).

**Check:** open the evidence; group failures by what went wrong, not by tool. An expected failure (a test written to
fail, `grep` finding nothing) is not an error.

**Propose:** climb the guard ladder (`building.md`): remove the failing path, a wrapper that refuses the wrong call with
the right one, a test, an error message that names its fix; a rule last. Kind `fix`, `cli` or `lint`.

## environment

**Read:** `environment`: by `cause` (harness blocked, server 5xx, rate limit, network, credentials, OS permission,
missing tool), with `samples`.

**Check:** whether the cause is still live today (a 5xx of one evening is not a pattern); whether the harness blocks
something on purpose.

**Propose:** an install step, a fix outside the prompt (the hub, the worker image), a line the agent was never told.
Kind `operation`, `fix` or `docs`.

## corrections

**Read:** `corrections`: the turns where the person corrected an agent, with the session.

**Check:** read each one; the patterns are words, not meaning. Keep the real ones and group them by the behaviour they
correct. For each group, open the turn before the correction and take the input that went wrong.

**Propose:** the same correction more than once is a missing guard. Climb the guard ladder (`building.md`). A proposal
whose evidence cites a correction and whose paths hold an AGENTS.md, a CLAUDE.md, a skill or `.claude` settings needs a
probe (`proposals.md`): a task and a one-line verify that shows whether an agent repeats the mistake.

## skills_memory

**Read:** `skills`: per skill, `sessions`, `calls`, `typed` (as /name), the snags after a load (`bash`, `error_rate`,
`usage_errors`, `env_errors`, `interrupts`, `corrections`) next to the baseline of every session
(`baseline_error_rate`, `baseline_interrupt_rate`), and `run_outcomes` of the runs that loaded it; `learned_skills`,
the backlog of continuous-learning.

**Check:** a skill whose snags stand well above the baseline: open the sessions after its load and find what it told the
agent that went wrong. A skill nobody loads in the window: is the window long enough?

**Propose:** a gotcha added to the skill, a step fixed, a skill scoped to the harness that uses it, a new skill for a
workflow `clusters` shows again and again. Kind `skill` or `memory`.

## runtime and cost

**Read:** `runtime.sessions` (tokens, cache reads and writes, `context` first and peak, cost, the heaviest sessions),
`runtime.runs`, `runtime.merged_prs` (cost per merged pull request), `runtime.hooks` and `runtime.tools` (median and
95th percentile time), `sessions.models`, `runs.cost_usd`.

**Check:** a slow hook: is it every prompt or a cold start? A heavy session: which subagents and tool outputs?

**Propose:** a cheaper model for a subagent that only searches or summarizes; less context in what a subagent starts
with; a hook made asynchronous or quiet. Name the numbers; a cost proposal without numbers is an opinion.

## failed_runs

**Read:** `failed_runs` by cause (`failed`, `lost`, a `sample`), `stuck_steps` (plan steps not moving, with days).

**Check:** read a run's events (`evo-agents hub run logs ID`). A cause that is the environment belongs to that lens.

**Propose:** what would have kept the run going: a verify that can run, a missing tool on the workers, a step split.

## kg_health

**Read:** `kg_health`: `retrieval` (lookups, empty ones, the searches after them, files edited that no result ranked in
its top 5, grep after a lookup, tokens per lookup), `eval` (hit@5 overall, on the holdout, per question type),
`review.open` (the review queue by rule), `sources` (commits behind, files missing, stale, deleted), `coverage`.

**Check and propose:** `kg.md`.

**Misleads when:** misses count every file edited after any lookup, including new files and files the lookup was not
about; a question type with a handful of questions swings by chance; the night's numbers lag a build made since.

## kg_init

Not a night's turn: a run of its own that the hub queues at a project's first build, on `evo-agents hub kg init`, or
when the data profile moved far. Its prompt holds the profile, so the figures are not read from the night. The whole
procedure is in `kg.md`, section "Configuring a new graph (the kg_init lens)".

## The others

`tech_debt` (`open_items`, `stuck_steps`), `code_health`, `docs_drift`, `security`, `product_goals` and `product`
(`product`) are lenses of the night shift too; read them the same way: the key, two pieces of evidence, the file the
change would touch.

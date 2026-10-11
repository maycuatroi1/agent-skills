# Lenses

Each lens is a way of reading the report. For each: where its signal is, what to open before believing it, what it
usually leads to, and how it misleads. The thresholds are starting points; say so when you use one.

## context

**Read:** the Context section. Startup tokens per runtime and kind (interactive, headless, subagent), peak tokens,
compactions, the components loaded at the start of the newest session, the instruction files with their smells,
the skill listing (size, unused skills, lines over 500 characters, trigger phrases two skills share), MCP servers
(calls, instruction size, deferred tools), big outputs, re-reads, orientation reads.

**Check:**

- What the startup number is made of. The transcript itemizes instruction files, the skill listing, MCP
  instructions, agent listing, deferred tool names, the system prompt and hook output; the rest of the count is
  not itemized (tool schemas are part of it). Only the itemized parts and the files behind them are yours to edit.
- For an instruction file with dated lines or long paragraphs, read those lines: status and history in a map is
  the usual finding.
- For an unresolved path, check whether it names a file in a sibling repo; if so the line needs the repo name, not
  a deletion.
- For an unused skill, check it is not used through a slash command under another name, and ask whether the
  window is long enough: a skill used monthly looks unused in 14 days.
- For a big output, open the call: a one-time `git diff` of a release is fine; the same command spilling every
  session is not.
- For a re-read, open the session: re-reading after an edit is normal; reading the same 60k file ten times is not.

**Propose:** see `context.md` for the moves. Typical: move a status paragraph out of `AGENTS.md` into the plan or
report it describes and leave a one-line pointer; move a skill used by one harness out of the user-global
directory; disable an MCP server a harness never calls; add a quiet flag or a `--json` field selection to a command
whose output is large; give a file read in many sessions' first calls a one-line answer in the map.

**Misleads when:** the window is short, the newest session is unusual (a long resumed session), or the token
estimate (characters divided by 4) is taken literally for code or text with diacritics. Startup tokens are
measured; component tokens are estimated.

## cli

**Read:** Repeated commands (a normalized command line in N sessions), Inline scripts (heredocs and `-c` programs
grouped by the file they work on), Sequences (programs that follow each other in N sessions).

**Check:** open two references. Is it the same job each time, with the same inputs varying in the same places? Is
there already a command for it (a `package.json` script, a `Makefile` or `justfile` target, a `scripts/` file, a
project CLI) that the agent did not know about? Then the fix is a line in the map, not a new command.

**Propose:**

- A command line rebuilt every session, especially one that sets up an environment (`export PATH=... PYTHONPATH=...
  DSN=...`): a script in the repo, named for the job.
- An inline script on the same files in many sessions (`python3 script on plans/active/*.yaml`): a subcommand that
  prints the view the scripts compute, or a pointer to the tool that already does.
- `X --help | head` in many sessions: the agent relearns a tool's interface each time; add the two lines it needs
  to the map or to the skill that uses the tool.
- `X 2>&1 | tail -n` in many sessions: the command is too loud; a quiet target or flag.
- A sequence of three or four programs in many sessions: a script that runs the sequence, if the steps never need
  judgment between them.

**Misleads when:** the repeated command is routine (git status, git diff, commit), exploratory (grep, sed, find;
the figures already leave these out), or repeated inside one long session only. Count sessions, not runs.

## skills

**Read:** Skills used (sessions, loads, and how: Skill tool, slash command, reading `SKILL.md`), the listing's
unused skills, the backlog (learned skills and CLI suggestions pending, garden proposals pending), subagents started.

**Check:** a workflow without a skill shows up as the same sequence of reads, commands and corrections in several
sessions. Open them and write down the steps; if you cannot write the same steps for three sessions, it is not a
skill yet. For a pending learned skill, look for sessions where its knowledge would have helped.

**Propose:** a new skill (see `building.md`), a gotcha added to an existing skill where its sessions keep failing
the same way, a description rewritten with the trigger phrases people actually typed, two skills with overlapping
triggers merged or separated, a pending learned skill promoted or discarded with its evidence.

**Misleads when:** usage is undercounted: a skill applied from its description without being loaded leaves no
trace, and a seasonal skill looks dead in a short window.

## tool_errors

**Read:** Tool errors (rate per tool and per shell program), Repeated errors (signature, count, sessions, cause).

**Check:** open the failing call and the call after it. Did the agent recover in one step (cheap) or spend several
(expensive)? Is the failure the work itself (a test that fails before a fix is written) rather than trouble with a
tool?

**Propose:** for an error that repeats with the same signature, the cheapest fix that makes it stop: a wrapper that
sets the missing flag, an error message in the project's own tool that names the fix, a line in the map ("run X
before Y"), or a lint config change when the same lint rule fails in many sessions (for example a line length the
code base does not follow).

**Misleads when:** `lint_failed` and `tests_failed` are the expected inner loop of real work; `wrong_input` from
`Edit` (string not found) is often a stale read, not a tool problem.

## environment

**Read:** Causes flagged `(environment)`: `harness_blocked`, `server_5xx`, `rate_limit`, `network`, `credentials`,
`os_permission`, `missing_tool`.

**Check:** these are failures the agent did not cause and often cannot fix by trying harder. Read the exact
message: a harness block usually says what to do instead.

**Propose:** a rule the agent was never told, placed where it will be read before the blocked action (for example,
how to wait for a background job in this runtime); an install step in the init script; for a server answering 5xx,
a finding for whoever owns that server, not a prompt change.

## corrections

**Read:** Corrections: turns that start like a correction, contain a correction phrase, or follow an interrupt.

**Check:** read each one; the patterns are words, not meaning. Keep the real ones and group them by the rule they
imply.

**Propose:** a one-line rule in the right file (global when it applies to every repo, project otherwise), with the
reason. When the rule already exists and was still broken, propose a hook or a check instead of a louder rule.

## harness

**Read:** Orientation reads, re-derived commands (a test or boot command assembled differently in several
sessions), files edited in several repos without a plan.

**Propose:** a map entry for the file every session reads first, a `scripts/test` or `init.sh` for the command that
gets re-derived, and for gaps the harness-engineering rubric covers (seam registry, cross-repo plan), a pointer to
that skill.

## cost

**Read:** Usage (tokens by runtime, models), subagent transcripts and their calls, startup tokens of subagents.

**Propose:** a cheaper model for a subagent type that only searches or summarizes; less context in what a subagent
starts with; fewer broad reads in the main session when a subagent would return a summary. Name the numbers; cost
proposals without numbers are opinions.

# Signal taxonomy

The maintain loop rests on one idea, taken from OpenAI's article and stated there as a habit rather than a system:

> When the agent struggles, we treat it as a signal: identify what is missing - tools, guardrails, documentation - and feed it back into the repository.

This file turns that habit into a lookup table. **Every stumble in a session transcript is evidence that the harness is missing something.** The job of `garden` is to name the missing artifact.

---

## The division of labor (do not blur this)

| Stage | Does what | Uses a model? |
|---|---|---|
| `digest` (SessionEnd hook) | Records **raw facts** from the transcript: commands run, tool errors, files read, repos touched, user turns | **No** |
| `garden` (batched) | **Interprets** those facts against this taxonomy and writes proposals | Yes |
| `review` / `apply` | Human decides; approved proposals land on a branch | No |

The hook must never classify. Deciding "was that user turn a correction?" with a regex is exactly the kind of brittle inference that produces a loop nobody trusts. `digest` writes down what happened. The model reads it later, in batch, with the taxonomy in hand.

**Batching is not just a cost optimization.** A single session where Claude fumbles the boot command is noise. The same fumble across three sessions is an `init.sh` that does not exist. Most signals below only become legible across sessions, and the per-session confidence column reflects that.

---

## The table

| Observed in transcript | What the harness is missing | Artifact to write | Rubric dim | Confidence from one session |
|---|---|---|---|---|
| Two or more *different* commands attempting to boot / run / serve the same thing | The boot procedure is not encoded | `init.sh` + `init.ps1`, and a "How to run" line in the map | 3 | Medium |
| Repeated failed attempts to find the test command | Test entry point not in the map | Map section + `init.sh test` | 3, 4 | Medium |
| The *same* tool error appears twice or more | The error does not teach its own fix | Remediation text in the error (if we own it); otherwise a Gotchas entry in docs | 4, 6 | **High** |
| A user turn that negates, corrects, or overrides Claude ("no", "we always use X here", "don't do Y", "khong phai the") | A tacit rule was never written down | Entry in `golden-principles.md`; promote to `invariants.md` + a lint if it is mechanizable | 6, 8 | **High** |
| Claude reads more than ~5 files to answer one question | The docs index is missing an entry, or the map does not point at it | `docs/index.md` entry + a pointer in the map | 1, 2 | Medium |
| A Grep or Glob sweeping across repo boundaries for one symbol | An undocumented cross-repo seam | Entry in `contracts.yaml` with owner, consumers, and a verify method | 10 | **High** |
| Files edited in 2+ repos in one session with no active plan | A cross-repo change happened by improvisation | A cross-repo exec-plan in `plans/active/` | 11 | **High** |
| Claude declares a feature done without ever running the app | No verification loop, or none the agent can reach | Acceptance entry in the work spec + a verify step in the map | 4, 7 | Medium |
| A doc is read and then contradicted by the code | Doc rot | A doc-gardening fix proposal | 2, 8 | **High** |
| A long detour ending in "actually, let me try a different approach" | Missing capability or missing constraint - genuinely ambiguous | Read it and decide; often a golden principle, sometimes a tool | varies | Low |
| The same non-obvious shell incantation is retyped across sessions | A CLI subcommand is missing | This is `continuous-learning`'s job, not ours. Leave it alone. | - | - |
| Claude re-derives the same piece of domain knowledge in different sessions | Knowledge lives in someone's head, not the repo | A design doc or product spec | 2 | Medium |
| A permission prompt is denied, then Claude works around it | The harness is fighting the human | Usually a settings/permissions fix, not a harness artifact. Note it, do not propose. | - | Low |

---

## Rules for writing a proposal

1. **Cite the evidence.** Every proposal quotes the specific session, the specific commands, the specific error. A proposal that cannot point at what provoked it is a generic best practice, and generic best practices are exactly what this loop must not produce. If `garden` starts emitting "consider adding more documentation," the loop has failed and the threshold must be raised.
2. **Propose the smallest artifact that closes the gap.** A missing boot command is an `init.sh` line, not a documentation initiative.
3. **Prefer enforcement over prose.** If the rule is mechanizable, propose the lint, not the paragraph. A paragraph is a score-2 answer to a problem that has a score-3 answer available.
4. **One proposal, one gap.** Do not bundle.
5. **Say where it goes.** Name the exact target repo and path. A proposal that does not know its destination cannot be applied.
6. **Respect the boundary with `continuous-learning`.** That skill turns repeated *command* patterns into CLI subcommands and reusable *skills*. This skill turns *harness gaps* into harness artifacts. When a signal is really about a repeated command, let the other skill have it.

## Thresholds

Defaults, tunable in `harness.yaml` under `garden:`:

| Setting | Default | Why |
|---|---|---|
| `min_sessions` | 3 | Below this there is not enough evidence to distinguish a pattern from an accident |
| `min_occurrences` | 2 | A single stumble is noise |
| `max_proposals_per_run` | 5 | A gardening run that emits twenty proposals will be ignored wholesale |
| `lookback_days` | 14 | Older signals describe a harness that may no longer exist |

If proposals come back vague, the fix is almost always to raise `min_occurrences`, not to rewrite the prompt.

## The honest failure mode

This loop can degrade into a generator of plausible-sounding busywork. The test, run it after the first real `garden`: **pick a proposal at random and ask whether it names a specific thing that actually happened.** If it does not, the loop is producing slop and should be switched off until the thresholds are fixed. It is better to have no maintain loop than one that trains you to ignore its output.

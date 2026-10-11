# Organizing context

Everything a session holds came from one of three places, and each costs differently:

| Layer | What is in it | When it is paid |
|---|---|---|
| Always loaded | system prompt, tool definitions, instruction files (`CLAUDE.md` chain, `AGENTS.md`), memory index, skill listing, MCP instructions, agent listing, SessionStart hook output | every model call of every session, and again in every subagent that starts from the same base |
| On demand | a skill's body and its references, docs, plans, a knowledge graph query, a file read | when the agent decides it needs it |
| Per turn | tool output, the person's messages, the agent's own text | once, then carried until the session ends or compacts |

The curator measures the first layer from what the runtime recorded (`Loaded at start of ...`) and from the files
themselves, and the third from tool output sizes, re-reads and compactions. The aim is a small, stable first layer
that points to everything else, and a third layer that does not fill up with output nobody needed.

## Principles

1. **The map points; it does not narrate.** An always-loaded instruction file is a table of contents: what this
   place is, where things live, the commands to run, the rules that hold everywhere. Status ("step 11 is pending"),
   history ("the plan before that was ..."), dates and long explanations belong in the plan, report or doc they
   describe, with one line in the map that points there. Lines with dates are the curator's proxy for this smell.
2. **One fact, one place.** A rule for every repo lives in the user-level file; a rule for one repo lives in that
   repo's file; a rule for one directory lives next to it. The same line in two files loaded by one runtime is paid
   twice and drifts.
3. **A skill's description is routing text.** It says what the skill does and when to use it, with the phrases
   people actually type, in a few hundred characters. Everything else goes in the body, and the body's detail goes
   in `references/` and `scripts/`, loaded only when needed.
4. **Scope by use.** A skill or MCP server that only one harness uses belongs to that harness, not to every session
   on the machine. One no harness used in the window is a candidate to disable, after checking a longer window.
5. **Commands should print what the next step needs.** Big outputs come back into the context and stay there. A
   command an agent runs often should have a quiet default, a summary, a `--json` mode with chosen fields, or a
   limit. `X | tail -n` typed in many sessions means the command itself should be quieter.
6. **Answer the question every session asks.** A file read in the first calls of many sessions, or read many times
   in one session, holds an answer the map should give in one line, or should be split so the answer is findable.
7. **Search wide in a subagent, decide in the main session.** A subagent that reads twenty files and returns a
   summary keeps the main context small. Subagents start from much of the same base, so trimming the first layer
   pays once per subagent too.
8. **Compactions mean the session carried more than its task.** Look at what filled it before blaming the length of
   the work.
9. **Edit by deltas.** Add, move or remove specific lines. A rewrite of a whole instruction file loses the details
   that earned their place, and once lost they are hard to notice.

## Moves

| Move | When | Example |
|---|---|---|
| point | status, history or detail sits in an always-loaded file | the plan history paragraph of `AGENTS.md` becomes one line: "plans and their reports: `plans/`, `reports/`" |
| dedupe | two loaded files hold the same rule | keep it in the narrower file that every runtime loads, delete the other copy |
| scope down | a user-global skill or server used by one harness | move the skill into that harness's skills directory; disable the server elsewhere |
| disable | a skill or server unused across a long window | turn it off for this harness; keep it installed |
| shorten a description | a listing line over about 500 characters | keep what and when and the trigger phrases; move the rest into the body |
| split | a large file read again and again for one section | an index at the top, or one file per topic |
| summarize | many sessions read the same file to learn one fact | the fact as one map line, with the file as its source |
| quiet | a command's output is large in many sessions | a flag, a target, a wrapper that prints a summary |
| mechanize | a rule in a document keeps being broken | a hook, a lint, a test; the document line can then shrink |

## Measuring

Give each context proposal a metric so the next review can tell whether it worked: `startup_tokens` (median startup
tokens of interactive sessions), `file_chars:<file>`, `listing_chars`, `big_outputs`, `rereads`, `compactions`.
Startup tokens move with things outside the harness too (a new runtime version, a new plugin); compare the
itemized components when the total moves for no reason you can see.

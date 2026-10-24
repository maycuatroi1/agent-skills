---
name: problem-intake
description: This skill should be used when the user asks to "find problems in this chat", "intake", "problem intake", "đọc chat tìm bài toán", "đọc email tìm vấn đề", "từ context mơ hồ tới bài toán", "what problems are hiding in these messages", or points at a Messenger group, a chat.fpt.com thread, an Outlook folder, a directory of documents, another harness or the hub's own chats and wants the pains in it turned into problems (P-n) with evidence. Also when the user asks to "tìm cơ hội", "opportunity", "find opportunities", "khai thác cơ hội": it then reads the same context for opportunities (O-n) across every project the member reads. On request only; reads with the member's own access and puts one evo-intake/2 result per project with `evo-agents hub intake put`.
version: 0.2.0
---

# problem-intake

Turn vague context (a group chat, a mail folder, a directory of documents, another harness) into
candidate problems and candidate opportunities with quoted evidence, the promises people made, and the
questions that only a person can answer. Every piece is read through two lenses: the problem lens
(what hurts, as in version 1) and the opportunity lens (what could be won). One run reads, cuts, filters, matches and puts one result on the hub. Writers then
approve what it proposed. The format and the hub rules are in evo-agents `docs/intake.md` and, for
opportunities, `docs/opportunities.md`.

Needs `evo-agents` >= 0.44.1 signed in (`evo-agents hub login`), and the writer role on the project
for `hub intake start` and `hub intake put`. Version 1 documents (`evo-intake/1`) are still accepted;
this skill puts `evo-intake/2`.

Never run on a schedule. Never log in for the member. Never send a message, mail or comment to
anyone: anything meant for another person is a draft in your reply, not an action.

## What an opportunity is

An opportunity is somebody's need, times something the project already has, times a time window.
Missing one factor, it is something else: a need without a lever is another party's problem; a lever
without a need is an asset left idle; a need and a lever whose window passed is a missed opportunity.
Its fields are `statement` (what gets better), `beneficiary` (who gains, possibly outside the
project), `leverage` (what the project has that makes it reachable now), an optional window, and
`answers` (the P-n it solves, in this project or another).

## Phase 0: ask

Ask only what you cannot read:

1. Which sources, each with a label: `public`, `internal` or `personal`. When the member does not say,
   the label is `internal`.
2. Which hub project the result goes to by default. List the projects the member sees with
   `evo-agents hub project list`.
3. The period to read, when the source is a stream.
4. Whether to look for opportunities. When the member asks for "tìm cơ hội", "opportunity" or
   "khai thác cơ hội", run at member scope (see "The opportunity lens"); otherwise run as in version 1
   and still note, without putting, any opportunity you happen to see.

Then read the problems already on the project once, so later matching costs nothing:

```
evo-agents hub problem list --project <project> --json
evo-agents hub problem evidence list P-3 --project <project>
```

For an opportunity run, read the opportunities already on every project in scope, too:

```
evo-agents hub opportunity list --project <project> --json
evo-agents hub opportunity show O-1 --project <project>
evo-agents hub opportunity list --closing-within 14 --project <project>
```

Open the intake. The hub stores kind, label and a short name, never content:

```
evo-agents hub intake start --project <project> \
  --source messenger:internal:"Dept group" --source file:public:thesis-outline.docx \
  --note "what the member asked for"
```

It prints `I-n`. Keep it for the put.

## Phase 1: read, with the member's access

| Source | How |
|---|---|
| Messenger | The browser session the member is already signed in to. Messenger has no API for personal messages and the list is virtualised: scroll up in steps, read each screen, and drop messages you already saw (same sender, same time, same text). Stop at the period start. If the page asks for a login, stop and ask the member to sign in; never type credentials. |
| chat.fpt.com | Same: the signed-in browser session, scroll and dedupe. |
| Outlook | The session's M365 tools when it has them. Without them, ask the member for an export. |
| Directory, attachments | Read the files. PDF, DOCX and XLSX carry the core of the matter (papers, outlines, summary sheets): extract their text and tables, do not skip them because they are not chat. |
| Another harness | `kg_search` and `kg_context` of the evo-hub tools, then `git log` of the repos, for what was done and when. |
| Hub data | `kg_search`, `history_search` and the hub's chats (`chat_thread`). Chats carry an audience; do not lift a private chat into a result others read. |
| Call logs | A call with only a duration is not readable. Do not guess its content: make it a question (Phase 4). |

Keep the raw reading on the machine. Only the result goes to the hub.

## The opportunity lens

Run it on every piece in addition to the problem lens, and only when the member asked for
opportunities.

**Scope is the member, not one project.** The densest opportunities cross projects: one project's
embedding route fixes another project's failing course sync; a classifier built for a blog serves two
other projects. Read all the projects `evo-agents hub project list` shows, in one run, and read them
together; a single-project run sees none of this. Keep the per-project cost low: list problems and
opportunities for each project first (Phase 0), read sources once, and attribute pieces to projects in
Phase 4.

**Cheap probes first**, before any model reads a piece. Each probe is a keyword or regex pass that
yields a candidate signal; the model then reads only the hits:

| Signal | Probe |
|---|---|
| `wish` | "I wish", "it would be nice", "ước gì", "giá mà", "nên có" |
| `external_demand` | a person or team outside the project asking for what the project could give: "can you give us", "xin", "cho mượn", "cần dùng" |
| `window` | a date, a deadline, an event, a term ("before 31/12", "tuần sau", "đến hết quý"); windows hide in prose, so scan for every date and relative time |
| `reusable_asset` | something shipped or built that another place could use as is: a service, a model, a classifier, a route, a template |
| `pull` | someone using a thing the owner did not push ("they already use it", "đang dùng thử") |
| `intro` | a person who could connect the project to a buyer, a user or a team |
| `idle_capacity` | read from hub numbers, not from chat (below) |

The other eight signals (`complaint`, `workaround`, `repeated_request`, `blocker`, `commitment`,
`proposed_solution`, `contradiction`, `decision_without_reason`) apply too: a repeated request from
outside the project is demand.

**Idle capacity comes from numbers.** Shipped and unused assets are the cheapest opportunities and
chat rarely mentions them. Read the hub's own figures with the commands that exist:

```
evo-agents hub curator status --project <project> --json
evo-agents hub org worker list --json
```

A night-shift curator that ran on 2 of 40 runs, a credential-sharing feature or a worker fleet that
sits almost unused: each is an `idle_capacity` line, with the figure as the excerpt and the command as
the source (`source_kind: other`, `source_uri` the command and project).

**What to keep.**

- A new opportunity needs a line of demand (`external_demand`, `pull`, `repeated_request`,
  `complaint`, `blocker` or `workaround`) or an `answers` code, and a line of leverage
  (`reusable_asset` or `idle_capacity`). Without both, and without a member's confirmation, the hub
  answers 422. Find the second line, ask the member to confirm (`confirmed_by`), or turn it into a
  question.
- A wish by the owner alone is noisy: owners wish for much. Keep it only with at least one line from
  the beneficiary's side and one line of leverage. With only the wish, it is a question for the owner,
  not a candidate.
- A `window_until` needs a line of signal `window` that quotes where the date comes from. No date in
  the source means no window; do not invent one.
- Real demand tends to come from the ecosystem around the member's organisation. Public channels give
  little; do not count an absence there as a finding.
- Missing sources are a limit to report: Messenger, Zalo and call recordings are not readable here, and
  many sessions have no transcript on the hub. Say so in the report.

**Match before proposing.** Compare each candidate with `hub opportunity list` of the project that
would hold it (Phase 0). The same opportunity gets `matches: "O-n"` and only new evidence lines.

**Split by the project that holds the lever.** Each opportunity goes to the project that has the
leverage, not the project that has the need. Its `answers` point at the P-n of the project that needs
it: `<project>/P-3` for another project, `P-3` for its own. A cross-project code is accepted only when
the writer who puts the result holds a grant on that project and the problem exists and is not
dropped; if you cannot cite such a P-n, leave `answers` out and say who needs it in `beneficiary`.

**Keep the label of the source project.** An evidence line that came from project A keeps the label A
gave it (`public` or `internal`). Moving data across a project boundary raises, never lowers, the
label. Drop every piece of a project whose sink does not allow it to reach the project you put to; if
you do not know the sink, treat the piece as `internal` and ask the member before using it. A
`personal` piece stays on the machine as in Phase 4.

## Phase 2: cut into addressed pieces

Cut every source into pieces, each with an address you can quote back: source kind, source name or
path, locator (message time, page, sheet and cell, commit), speaker, time. A piece without an address
is not evidence; drop it or find the address. The `source_uri` and `locator` of an evidence line come
from this address.

## Phase 3: filter, cheap rules first

Run rules that cost nothing before any model reads a piece: keyword and regex passes for complaint
words, "waiting for", "again", "still not", "can you", "I will handle it" and their Vietnamese
forms ("để em xử lý", "chưa được", "lại bị"), dates, repeated senders, attachment names. Keep the
pieces that hit. Only then let the model read the survivors and classify each by signal:
`complaint`, `workaround`, `repeated_request`, `blocker`, `commitment`, `proposed_solution`,
`contradiction`, `decision_without_reason`.

What the nine hand-run lessons say to look for:

1. A promise is the most valuable signal: someone said they would handle it. It carries a promiser, a
   job and an implied date. Check it against the harness (Phase 5); a promise with no trace is a
   hanging job.
2. One request is not a problem. The same kind of request five times in nine days (a key, a deploy, a
   renamed model) is. Group pieces by kind of request over time before proposing.
3. People often hand over the solution ("build a tool into the console"). That is a `proposed_solution`
   line attached to the problem, not the problem. Ask what the tool is for.
4. Call recordings are the largest blind spot. Messenger has no recording; the cheap fix is one line
   of notes per call from the member.
5. Attachments carry the substance. A candidate that ignores them is probably wrong.
6. Identities merge: one person has three names, and one name fits two people. See Phase 4.
7. Route to the right project: two chats can yield problems for four places.
8. Sensitivity is per piece. A remark about a person never leaves the machine; the technical part of
   the same message may.
9. Messenger lists are virtualised and need the member's own session: scroll and dedupe, never sign
   in for them.

## Phase 4: identities, projects, existing problems, labels

- **Identities.** Map each name to one person. The hub's members of the project are the base (their
  logins appear in `hub project list` and in hub chats). Keep the rest in a local alias file outside
  git (for example `~/.config/problem-intake/aliases.yaml`: name or handle to person). When two people
  share a name or one person has several, ask the member; do not merge on a guess.
- **Project.** Split candidates to the project they belong to with `evo-agents hub project list`.
  One put goes to one project; run Phase 6 once per project that has candidates, with its own
  `intake start`. An opportunity goes to the project that holds its leverage (see "The opportunity
  lens"); a problem goes to the project where it hurts.
- **Existing problems.** Before proposing a new problem, compare with
  `evo-agents hub problem list --project <project> --json` (and `problem show` for the detail of one).
  When a candidate is the same problem, set `matches: "P-n"` and give only the new evidence lines.
  Two near matches: pick the closer and say so in a question.
- **Labels.** Label every piece. A `personal` piece (remarks about people, private matters) stays
  on the member's machine: it does not enter a candidate's evidence and is not in the result. The hub
  answers 422 to a `personal` line.
- **Calls with only a duration.** List each as a question for the member: "call with X on 2026-10-12,
  41 min: one line of notes?" with `for` set to the member.

## Phase 5: candidates, promises, questions

A **new candidate** has the four fields of a problem: `statement`, `who`, `when`, `workaround`. Each
field has a basis in `basis`: a quote of at most 300 characters, or `inferred`. Never write an inferred
field as if it were quoted. Proposed solutions go in as `proposed_solution` evidence lines, not in
`statement`.

**Evidence lines** have `source_kind`, `source_uri`, `locator`, `speaker`, an `excerpt` of at most 300
characters, a `signal` and a `label` (`public` or `internal`).

**Rule of two independent sources.** A source is independent of another when its kind or address
differs. A candidate with one independent source that no member confirmed is refused with 422 and
nothing is written. Find a second source, set `confirmed_by` to the login of a project member who
confirmed it (ask), or turn the candidate into a question.

**Promises.** Check each against the harness with `kg_search` and `git log --since <date> --grep`
for the repo concerned. Record `delivery_seen: true` with a `delivery_note` only when you found the
trace; no trace is `false`, and that is the finding.

**Questions.** What you could not decide, each with your hypothesis in the text and the person to ask
in `for`: "Is the model deploy of 10-23 still open? I think yes, no trace in the repo." Questions stay
in the intake for the people named.

## Phase 6: put the result

Write one document per project, `evo-intake/2`. It is `evo-intake/1` plus `opportunities` (at most
50 per document). A run with no opportunity may still put `evo-intake/1`. Opportunity candidates are
either `matches: "O-n"` with `evidence` only, or new, with `statement`, `beneficiary` and `leverage`
each backed by a `basis` (a quote of at most 300 characters, or `inferred`), an optional
`window_until` (YYYY-MM-DD) and `window_note` with their own basis, and optional `answers`:

```json
{
  "schema": "evo-intake/2",
  "candidates": [
    {
      "statement": "Teams ask for model keys and deploys by hand, five times in nine days",
      "who": "lab students",
      "when": "each new experiment",
      "workaround": "message the lab admin",
      "basis": {
        "statement": "inferred",
        "who": {"quote": "em xin key để chạy thử"},
        "when": "inferred",
        "workaround": {"quote": "nhắn anh xử lý giúp em"}
      },
      "evidence": [
        {"source_kind": "messenger", "source_uri": "Dept group", "locator": "2026-10-12 09:41",
         "speaker": "member-a", "excerpt": "em xin key để chạy thử", "signal": "repeated_request",
         "label": "internal"},
        {"source_kind": "email", "source_uri": "Outlook/Inbox/key-request", "locator": "2026-10-19",
         "excerpt": "xin cấp key cho nhóm 3", "signal": "repeated_request", "label": "internal"}
      ]
    },
    {
      "matches": "P-3",
      "evidence": [
        {"source_kind": "file", "source_uri": "notes/summary.xlsx", "locator": "Sheet1!C14",
         "excerpt": "deploy chờ duyệt 6 ngày", "signal": "blocker", "label": "internal"}
      ]
    }
  ],
  "opportunities": [
    {
      "statement": "Serve the course-sync AI feature of another project from our embedding route",
      "beneficiary": "learners of the course platform",
      "leverage": "a self-hosted embedding route that already runs and has spare capacity",
      "window_until": "2026-12-31",
      "window_note": "term ends",
      "answers": ["lms/P-4"],
      "basis": {
        "statement": "inferred",
        "beneficiary": {"quote": "học viên không sync được AI"},
        "leverage": {"quote": "route embedding đang chạy, còn dư"},
        "window_until": {"quote": "trước hết kỳ 31/12"},
        "window_note": "inferred"
      },
      "evidence": [
        {"source_kind": "hub_chat", "source_uri": "lms/chat/course-sync", "locator": "2026-10-20",
         "excerpt": "khóa học không sync được AI", "signal": "external_demand", "label": "internal"},
        {"source_kind": "other", "source_uri": "hub curator status --project ialab", "excerpt": "route used on 2 of 40 runs",
         "signal": "idle_capacity", "label": "internal"},
        {"source_kind": "hub_chat", "source_uri": "lms/chat/course-sync", "locator": "2026-10-20",
         "excerpt": "trước hết kỳ 31/12", "signal": "window", "label": "internal"}
      ]
    },
    {
      "matches": "O-2",
      "evidence": [
        {"source_kind": "email", "source_uri": "Outlook/Inbox/demo", "locator": "2026-10-22",
         "excerpt": "cho chúng tôi xem bản demo", "signal": "pull", "label": "internal"}
      ]
    }
  ],
  "promises": [
    {"text": "Deploy the model by 10-23", "promiser": "member-b", "due": "2026-10-23",
     "delivery_seen": false, "source": "Dept group"}
  ],
  "questions": [
    {"text": "Call of 2026-10-12, 41 min: one line of notes? I think it was about the key quota.",
     "for": "member-a"}
  ]
}
```

Put it once. The intake closes; a second put is a 409. Show the member the candidates, promises and
questions in your reply first when they asked to see them, then put:

```
evo-agents hub intake put I-<n> result.json --project <project>
evo-agents hub intake show I-<n> --project <project>
```

A new candidate becomes a pending proposal of kind `problem` with its evidence; a `matches` candidate
becomes a pending proposal of evidence lines for that P-n; a new opportunity becomes a pending proposal
of kind `opportunity` (the next free O-n, in order) and a matching one a proposal of evidence lines
for that O-n (see them under `outcome.opportunity_proposals` of `intake show`); each promise becomes a task due on its date;
questions stay in the intake. Nothing is approved by you: writers approve proposals in the Inbox, in
code order. On a 422, read the reason, fix the document (a second source, a label, a field), and put
again; a rejected put wrote nothing.

## Report

Say what was read (sources, period, how many pieces, and for an opportunity run which projects), what was dropped and why (duplicates, no
address, `personal`), the intake code, and what the put made. List the `personal` pieces only as a count.
For an opportunity run, list per project the opportunities put, the ones that matched an existing
O-n, the wishes held back as questions, the pieces dropped for a sink or a label, and the sources you
could not read. Messages for others are drafts, shown to the member in the reply, never sent.

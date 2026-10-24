---
name: problem-intake
description: This skill should be used when the user asks to "find problems in this chat", "intake", "problem intake", "đọc chat tìm bài toán", "đọc email tìm vấn đề", "từ context mơ hồ tới bài toán", "what problems are hiding in these messages", or points at a Messenger group, a chat.fpt.com thread, an Outlook folder, a directory of documents, another harness or the hub's own chats and wants the pains in it turned into problems (P-n) with evidence. On request only; reads with the member's own access and puts one evo-intake/1 result with `evo-agents hub intake put`.
version: 0.1.0
---

# problem-intake

Turn vague context (a group chat, a mail folder, a directory of documents, another harness) into
candidate problems with quoted evidence, the promises people made, and the questions that only a
person can answer. One run reads, cuts, filters, matches and puts one result on the hub. Writers then
approve what it proposed. The format and the hub rules are in evo-agents `docs/intake.md`.

Needs `evo-agents` >= 0.42.0 signed in (`evo-agents hub login`), and the writer role on the project
for `hub intake start` and `hub intake put`.

Never run on a schedule. Never log in for the member. Never send a message, mail or comment to
anyone: anything meant for another person is a draft in your reply, not an action.

## Phase 0: ask

Ask only what you cannot read:

1. Which sources, each with a label: `public`, `internal` or `personal`. When the member does not say,
   the label is `internal`.
2. Which hub project the result goes to by default. List the projects the member sees with
   `evo-agents hub project list`.
3. The period to read, when the source is a stream.

Then read the problems already on the project once, so later matching costs nothing:

```
evo-agents hub problem list --project <project> --json
evo-agents hub problem evidence list P-3 --project <project>
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
  `intake start`.
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

Write one document, `evo-intake/1`:

```json
{
  "schema": "evo-intake/1",
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
becomes a pending proposal of evidence lines for that P-n; each promise becomes a task due on its date;
questions stay in the intake. Nothing is approved by you: writers approve proposals in the Inbox, in
code order. On a 422, read the reason, fix the document (a second source, a label, a field), and put
again; a rejected put wrote nothing.

## Report

Say what was read (sources, period, how many pieces), what was dropped and why (duplicates, no
address, `personal`), the intake code, and what the put made. List the `personal` pieces only as a count.
Messages for others are drafts, shown to the member in the reply, never sent.

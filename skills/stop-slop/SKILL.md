---
name: stop-slop
description: This skill should be used when the user asks to "remove AI tells", "make this sound human", "de-slop this", "bỏ giọng AI", "viết cho tự nhiên", "sửa văn phong AI", "edit this draft", "review my writing", or is drafting/editing/reviewing English prose (blog posts, essays, docs, READMEs, release notes, emails, landing copy) that must not read as machine-written. Supplies the banned-phrase list, the structural clichés to avoid, before/after rewrites, and a 5-dimension score to decide whether a draft ships or gets revised.
version: 0.1.0
---

# stop-slop

Remove predictable AI writing patterns from prose.

Ported from [hardikpandya/stop-slop](https://github.com/hardikpandya/stop-slop) by
[Hardik Pandya](https://hvpandya.com), MIT. Upstream is the source of truth for the pattern lists;
re-sync when it changes.

## When to use

- Drafting any prose that a human will read as human writing.
- Editing or reviewing a draft (yours or the user's) before it ships.
- The user complains that text "sounds like AI" or "sounds generic".

Do not apply to code, code comments, commit messages, or structured output (YAML, JSON, tables).
Terse machine-facing text is not slop.

## Core rules

1. **Cut filler phrases.** Remove throat-clearing openers, emphasis crutches, business jargon, and all
   adverbs. See [references/phrases.md](references/phrases.md).

2. **Break formulaic structures.** Avoid binary contrasts, negative listings, dramatic fragmentation,
   rhetorical setups, false agency. See [references/structures.md](references/structures.md).

3. **Use active voice.** Every sentence needs a human subject doing something. No passive
   constructions. No inanimate objects performing human actions ("the complaint becomes a fix").

4. **Be specific.** No vague declaratives ("The reasons are structural"). Name the specific thing. No
   lazy extremes ("every", "always", "never") doing vague work.

5. **Put the reader in the room.** No narrator-from-a-distance voice. "You" beats "People". Specifics
   beat abstractions.

6. **Vary rhythm.** Mix sentence lengths. Two items beat three. End paragraphs differently. No em
   dashes.

7. **Trust readers.** State facts directly. Skip softening, justification, hand-holding.

8. **Cut quotables.** If it sounds like a pull-quote, rewrite it.

## Quick checks

Run this pass before delivering prose:

- Any adverbs? Kill them.
- Any passive voice? Find the actor, make them the subject.
- Inanimate thing doing a human verb ("the decision emerges")? Name the person.
- Sentence starts with a Wh- word? Restructure it.
- Any "here's what/this/that" throat-clearing? Cut to the point.
- Any "not X, it's Y" contrasts? State Y directly.
- Three consecutive sentences match length? Break one.
- Paragraph ends with a punchy one-liner? Vary it.
- Em dash anywhere? Remove it.
- Vague declarative ("The implications are significant")? Name the specific implication.
- Narrator-from-a-distance ("Nobody designed this")? Put the reader in the scene.
- Meta-joiners ("The rest of this essay...")? Delete. Let the essay move.

## Scoring

Rate 1-10 on each dimension:

| Dimension | Question |
|-----------|----------|
| Directness | Statements or announcements? |
| Rhythm | Varied or metronomic? |
| Trust | Respects reader intelligence? |
| Authenticity | Sounds human? |
| Density | Anything cuttable? |

Below 35/50: revise and re-score. Report the score only when the user asked for a review; when they
asked for a draft, apply the rules silently and hand over the clean text.

## Workflow

**Drafting.** Apply the core rules while writing. Do not write slop and then strip it.

**Editing a draft.** Read [references/phrases.md](references/phrases.md) and
[references/structures.md](references/structures.md) first, then rewrite. Return the revised text.
List the cuts only if the user asked what changed.

**Reviewing.** Quote the offending span, name the pattern, give the replacement. One line each. Then
score.

See [references/examples.md](references/examples.md) for before/after transformations.

## Repo conventions this skill inherits

`~/.claude/CLAUDE.md` already bans em dashes, en dashes, and smart quotes machine-wide. This skill
bans them too, for a different reason: they are an AI tell. ASCII `-`, `"`, `'` only.

## License

MIT, same as upstream.

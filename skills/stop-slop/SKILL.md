---
name: stop-slop
description: This skill should be used when the user asks to "remove AI tells", "make this sound human", "de-slop this", "bỏ giọng AI", "viết cho tự nhiên", "sửa văn phong AI", "edit this draft", "review my writing", or is drafting/editing/reviewing English or Vietnamese prose (blog posts, essays, docs, READMEs, release notes, emails, landing copy) that must not read as machine-written. Supplies the banned-phrase list, the structural clichés to avoid, before/after rewrites, Vietnamese-specific AI tells (calque, binary contrast, signpost, slogan, usher sentences, over-translated terms, uniform density), and a 5-dimension score to decide whether a draft ships or gets revised.
version: 0.3.1
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

9. **Vietnamese: escape the English skeleton.** Vietnamese AI prose keeps Vietnamese vocabulary but
   preserves English syntax - binary contrast "không A, mà B", triple parallel "Một X, một Y, một Z",
   signpost "Nói cách khác:", calque "đóng đinh một dữ kiện". The vocabulary is Vietnamese; the rhythm
   is still English. See [references/vietnamese-patterns.md](references/vietnamese-patterns.md).

10. **Vietnamese: kill calques literal-translation.** Read the phrase aloud. If it sounds translated
    ("đóng đinh dữ kiện" for "nail down a data point", "tự sai" for "discredits itself", "hỏng đúng
    chỗ" for "breaks down"), a Vietnamese speaker would never say it. Replace with the natural
    phrasing. The calque table is in [references/vietnamese-patterns.md](references/vietnamese-patterns.md)
    section 4.

11. **Cut usher sentences.** A sentence whose only job is to introduce the next sentence, or to tell
    the reader how to read it, is the heaviest machine tell. "Here's how it works.", "Put simply, the
    whole paragraph collapses to one line:", "The rest of this section covers X". Delete it and check
    the following paragraph still reads. It almost always does. Same for the piece narrating itself:
    "this post", "from here to the end", "I'll come back to this throughout". See
    [references/vietnamese-patterns.md](references/vietnamese-patterns.md) section 11.

12. **Leave a beat after the hard part.** Machine prose runs at 100 percent information density, every
    sentence advancing. That unrelenting forward pressure is the tell, not the vocabulary. After a
    formula, a table, or a dense definition, drop one sentence that carries no information and only
    touches the reader ("Bạn thấy chứ?", "Read that again."). Placement is the point: an usher goes
    BEFORE the hard block, a beat goes AFTER it. Once or twice per piece, never as a template. See
    section 12.

13. **Vietnamese: do not over-translate technical terms.** Rule 10 applied too hard becomes its own
    error. Kill calqued metaphors and idioms; keep technical nouns the reader already says out loud.
    "attention" beats "chú ý", "RAM" beats "ngốn máy", "context length" beats "chiều dài". Test: if
    translating the phrase back to English lands on a familiar idiom, it is a calque; if it was English
    to begin with, leave it. See section 13.

14. **Never count source text units for effect.** "in exactly one sentence on page 13", "the whole
    paragraph collapses to one line", "a mere three lines on this". Test: delete the number. If the
    reader's conclusion is unchanged, cut it - the count was there to sound diligent, not to argue.
    Keep it only when rarity or exhaustiveness IS the argument ("this appears once in 58 pages"). Same
    for "hẳn", "tận", "vỏn vẹn", "a mere", "no fewer than" glued to a number that already speaks. See
    section 15.

15. **Uneven beats even.** The rules above are symptoms; the disease is uniformity. Every paragraph
    pulling its weight, every section landing on a constructed beat, every block introduced. Real
    writing is lumpy, because a real mind gets excited and then gets tired. Accept that the right edit
    is sometimes the WORSE sentence: cutting the fifth instance of a rhetorical move beats keeping a
    good line that completes a predictable pattern. Count sections ending on a shaped punchline; over
    half is broken. See section 14.

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
- Any sentence that only introduces the next one? Delete it and re-read. It almost always survives.
- Does the piece narrate itself ("this post", "from here on")? Name the subject instead.
- Any formula/table/dense definition with no beat after it? Add one zero-information sentence.
- Count sections ending on a shaped punchline. Over half? Let some end flat.
- Counting sentences or lines in a source ("in exactly one sentence")? Delete the number; if nothing changes, leave it deleted.

Vietnamese-specific (see [references/vietnamese-patterns.md](references/vietnamese-patterns.md) quick
check section for the full list):

- Any "không A, mà B" / "không nằm ở A, nó nằm ở B" binary contrast? State Y directly.
- Any signpost "Nói cách khác:" / "Điểm chốt:" / "Tức là:"? Cut.
- Any calque that sounds translated ("đóng đinh dữ kiện", "tự sai", "hỏng đúng chỗ")? Replace with
  natural Vietnamese.
- Any standalone closing sentence that sounds like a pull-quote or motivational tagline? Rewrite.
- Any triple parallel "Một X, một Y, và một Z"? Break the rhythm.
- Any "X là thứ duy nhất Y, và cũng Z nhất" thesis formula? Split into two sentences.
- Read aloud: does it sound like Vietnamese a person speaks, or like translated text? Rewrite the
  translated parts.
- Any technical term translated past what the reader says out loud ("chú ý" for attention, "phép tính
  dấu phẩy động" for FLOPs)? Put the working term back.
- Replaced a term in bulk? Re-check every hit by grammatical role. "sự attention", "đáng attention",
  "đã attention vào đâu" are broken Vietnamese a find-replace leaves behind.

## Scoring

Rate 1-10 on each dimension:

| Dimension | Question |
|-----------|----------|
| Directness | Statements or announcements? |
| Rhythm | Varied or metronomic? |
| Trust | Respects reader intelligence? |
| Authenticity | Sounds human? |
| Density | Anything cuttable? Anywhere running at 100 percent with no beat? |
| Evenness | Do all sections land the same shape? Uniform is worse than lumpy. |

Below 42/60: revise and re-score. Report the score only when the user asked for a review; when they
asked for a draft, apply the rules silently and hand over the clean text.

## Workflow

**Drafting.** Apply the core rules while writing. Do not write slop and then strip it.

**Editing a draft.** Read [references/phrases.md](references/phrases.md) and
[references/structures.md](references/structures.md) first, then rewrite. For Vietnamese prose, also
read [references/vietnamese-patterns.md](references/vietnamese-patterns.md). Return the revised text.
List the cuts only if the user asked what changed.

**Reviewing.** Quote the offending span, name the pattern, give the replacement. One line each. Then
score.

See [references/examples.md](references/examples.md) for before/after transformations.

## Repo conventions this skill inherits

`~/.claude/CLAUDE.md` already bans em dashes, en dashes, and smart quotes machine-wide. This skill
bans them too, for a different reason: they are an AI tell. ASCII `-`, `"`, `'` only.

## License

MIT, same as upstream.

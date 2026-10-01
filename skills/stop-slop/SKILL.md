---
name: stop-slop
description: This skill should be used when the user asks to "remove AI tells", "make this sound human", "de-slop this", "bỏ giọng AI", "viết cho tự nhiên", "sửa văn phong AI", "edit this draft", "review my writing", or is drafting/editing/reviewing English or Vietnamese prose (blog posts, essays, docs, READMEs, release notes, emails, landing copy) that must not read as machine-written. Supplies the banned-phrase list, the structural clichés to avoid, before/after rewrites, Vietnamese-specific AI tells (calque, binary contrast, signpost, slogan, usher sentences, over-translated terms, uniform density), and a 5-dimension score to decide whether a draft ships or gets revised.
version: 0.4.0
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

16. **Never hand the reader the verdict before the evidence.** "The mechanism is almost annoyingly
    simple.", "There is one line that is easy to skim past.", "The two most interesting rows read the
    opposite of what you would guess." Each announces how to feel about a thing not yet shown. This is
    NOT rule 11: an usher organizes ("here is how it works"), a verdict distrusts ("this is going to
    surprise you"). The material either lands or it does not, and saying so first cannot help it.
    Test: does this sentence contain a fact, or a rating of a fact? Ratings go. See section 16.

17. **Interrogate the motive, not just the shape.** Every rule above can be gamed by a model that
    matches templates and misses the one it has not seen. The generative question is: did I write this
    sentence because the content needed it, or because the paragraph felt unfinished without it? The
    honest answer for most slop is the second. Three numbers ending a paragraph feel bare, so a
    three-clause chime gets glued on ("Same lab, same benchmark, one generation apart") that repeats
    what the numbers already said. Nothing in the sentence is false; nothing in it is new either. Let
    the paragraph end bare. Discomfort with a flat ending is the writer's problem, not the reader's.
    See section 17.

18. **When unsure how it is really said, search for it. Do not guess.** Every rule above is a list of
    what to avoid; this is the one positive check, and it is stronger, because it finds the tells no
    list has caught yet. Before coining a term, translating one, or shipping a phrase that might be a
    calque, run a web search and read what actual writers wrote. Three query forms, each answering a
    different question, all verified 21/08/2026:

    - `"the exact phrase"` in quotes - **does this collocation exist at all?** Searching
      `"đơn giản tới mức khó chịu"` returned zero pages using it as a unit; every hit matched the
      component words separately (irritability as a medical condition, simplicity as a lifestyle).
      That decomposition IS the signal: the phrase was invented in translation.
    - `<word> nghĩa là gì` - **does the word mean what I think?** `"bảng số" nghĩa là gì` came back
      as a vehicle licence plate, with the table-of-numbers sense secondary. Collision found.
    - the concept phrased **entirely in the target language, no English mixed in** - what do people
      call this thing? Mixing English technical terms into the query returns topic noise instead of
      usage evidence; that query form failed on the first try and had to be rewritten.

    Read the results for usage, not for answers. The summary paragraph a search engine writes is
    itself machine prose. What counts is whether real pages use the phrase as a unit. See section 18.

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
- Any sentence rating a fact instead of stating one ("surprisingly simple", "easy to miss")? Cut the rating, show the fact.
- For each sentence you would fight to keep: did the content need it, or did the paragraph feel unfinished? Cut the second kind.

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
- Not sure whether a phrase is real Vietnamese? Do not guess and do not ask the user. Search the
  exact phrase in quotes. No page using it as a unit means you invented it.
- Any technical term translated past what the reader says out loud ("chú ý" for attention, "phép tính
  dấu phẩy động" for FLOPs)? Put the working term back.
- Replaced a term in bulk? Re-check every hit by grammatical role. "sự attention", "đáng attention",
  "đã attention vào đâu" are broken Vietnamese a find-replace leaves behind.
- Coined a folksy Vietnamese term where standard Vietnamese already has one ("cú ngắt" for "gián
  đoạn")? Use the standard one. Inventing is over-translation too.
- Reached for textbook register ("đại lượng", "yếu tố", "phương diện") where the things have plain
  names ("phép tính và bộ nhớ")? Name them.
- Does the Vietnamese word you picked already mean something else? "bảng số" is a licence plate, not
  a table of numbers. Say the phrase aloud to someone who has not read your draft.
- Pointing at your own text ("dòng này", "mục ba", "bài này")? Name the thing instead. If you can
  name it, the location is noise. If a section number is genuinely needed, write "mục 3".

## Blacklist quét bằng máy (tiếng Việt)

[references/blacklist-vi.txt](references/blacklist-vi.txt) giữ các cụm đã bị bắt tại
trận, dạng pattern ERE mỗi dòng một cái. Chạy trước khi ship:

```bash
grep -vE '^[[:space:]]*(#|$)' blacklist-vi.txt | grep -n -i -E -f - bai.mdx
```

Kết quả là chỗ cần nhìn, không phải chỗ phải sửa. Đọc từng câu rồi mới quyết, vì có
dương tính giả (ví dụ "phải trả" khi bài đang nói về tiền thật).

Bắt được cụm mới thì thêm vào file đó, kèm chú thích lý do trong nhóm của nó. Không
ghi lý do thì lần sau lại tưởng là câu hay.

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

**Drafting.** Apply the core rules while writing. Do not write slop and then strip it. When a phrase
is uncertain, search it (rule 18) at the moment of doubt rather than shipping it and hoping the review
pass catches it. The review pass only catches patterns already on a list.

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

## Separator convention

Do not use the middle-dot character U+00B7 as a separator in authored prose, headings,
captions, diagram labels, interface labels, or human-readable table cells. Do not emit
its HTML entity forms as a workaround. Use commas, colons, ASCII hyphens, or separate
lines according to the sentence.

Check the complete deliverable before publishing, including images with text and diagrams.
Preserve verbatim source quotations, identifiers, and mathematical operators when fidelity
requires them; do not silently rewrite source material as a style edit.

## License

MIT, same as upstream.

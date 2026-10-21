---
name: stop-slop
description: Draft, edit, or review English and Vietnamese prose to remove AI tells while preserving facts, uncertainty, and the author's voice. Use for "bỏ giọng AI", "viết cho tự nhiên", "stop-slop", prose rewrites, or editorial reviews. Includes phrase and structural checks, Vietnamese usage guidance, authorship and evidence boundaries, and a six-dimension review rubric. Not a style filter for code, formulas, or structured data.
version: 0.6.0
---

# stop-slop

Remove predictable AI writing patterns from prose.

Ported from [hardikpandya/stop-slop](https://github.com/hardikpandya/stop-slop) by
[Hardik Pandya](https://hvpandya.com), MIT. Upstream is the source of truth for the pattern lists;
re-sync when it changes, preserving the local authorship, evidence, and Vietnamese adaptations.

## When to use

- Drafting any prose that a human will read as human writing.
- Editing or reviewing a draft (yours or the user's) before it ships.
- The user complains that text "sounds like AI" or "sounds generic".

Do not apply to code, code comments, commit messages, or structured output (YAML, JSON, tables).
Terse machine-facing text is not slop.

## Preserve meaning before style

Keep facts, quantities, units, attribution, conditions, and uncertainty intact. Do not make a claim
more certain or invent an experience to make prose sound confident or personal. Preserve the user's
genre and intended voice: a proposal may need future tense; a technical distinction may need a
contrast. The pattern lists are review prompts, not automatic deletion rules. Functional questions,
three-part definitions, and qualifications such as "may", "if", "có thể", or "chưa đủ" can be essential.

For ghostwriting, technical explanations, or illustrated articles, read
[references/authorship-and-evidence.md](references/authorship-and-evidence.md). It covers narrator
identity, repeated plan narration, evidence caveats, bilingual terminology, and captions.

When editing a specific author's prose, read
[references/author-corrections.md](references/author-corrections.md) first. The author's own rewrites
outrank every rule below: a sentence can pass all of them and still be one the author would never say.

## Core rules

1. **Cut filler phrases.** Remove throat-clearing openers, emphasis crutches, business jargon, and empty
   intensifiers. Keep modifiers that specify frequency, precision, or uncertainty. See
   [references/phrases.md](references/phrases.md).

2. **Break formulaic structures.** Avoid binary contrasts, negative listings, dramatic fragmentation,
   rhetorical setups, false agency. See [references/structures.md](references/structures.md).

3. **Name the actor when it matters.** Rewrite a passive when it hides who decided, caused, or is
   responsible. No inanimate objects performing human actions ("the complaint becomes a fix"). Do not
   purge every passive: instruction-tuned models already use agentless passives at about half the human
   rate (Reinhart et al. 2025, PNAS), so a blanket ban pushes prose further from human writing.

4. **Be specific, from a source.** No vague declaratives ("The reasons are structural"). Name the
   specific thing. No lazy extremes ("every", "always", "never") doing vague work. Every specific must
   come from a source, a measurement, or the author. An invented time, scene, count, or feeling is
   fabrication, and fabrication is worse than abstraction; see section 7 of
   [references/workshop-leaks.md](references/workshop-leaks.md).

5. **Put the reader in the room with the material.** No narrator-from-a-distance voice. "You" beats
   "People". Put the reader in front of the code, the number, or the screenshot, not in a staged scene
   ("It is 2 a.m. and the shop is slow").

6. **Vary rhythm.** Mix sentence lengths. Avoid repeating a decorative three-part cadence; keep lists
   whose items serve the content. End paragraphs differently. No em dashes.

7. **Trust readers.** State facts directly. Cut performative reassurance and hand-holding; retain
   limitations that change how the reader should interpret a claim.

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

12. **Vary pace without adding filler.** After a formula, table, or dense definition, use a paragraph
    break, a concrete example, or a short explanation of a likely stumbling point when needed. Do not
    automatically append "Bạn thấy chứ?" or "Read that again." A natural conversational aside may fit
    the author's voice, but there is no quota for zero-information sentences. See
    [references/vietnamese-patterns.md](references/vietnamese-patterns.md) section 12.

13. **Vietnamese: do not over-translate technical terms.** Rule 10 applied too hard becomes its own
    error. Kill calqued metaphors and idioms; keep technical nouns the reader already says out loud.
    "attention" beats "chú ý", "RAM" beats "ngốn máy", "context length" beats "chiều dài". Test: if
    translating the phrase back to English lands on a familiar idiom, it is a calque; if it was English
    to begin with, consider the audience and context. Ordinary terms may read better in Vietnamese;
    avoid awkward mixed-language grammar. See section 13 and the bilingual examples in
    [references/authorship-and-evidence.md](references/authorship-and-evidence.md).

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

19. **Nothing from the workshop reaches the reader.** File and script names, the date you checked
    something, how many pages you read, constraints copied from the prompt, usernames, and the history of
    how the piece changed belong in a handoff note for whoever assigned the work. Test: delete it; does
    the reader lose anything they can use? If it only proves diligence or records production, it goes.
    Most examples in [references/workshop-leaks.md](references/workshop-leaks.md) passed an earlier
    stop-slop review because no rule named them.

20. **Write the way people talk.** Prefer the verb and the particle a person would say over the nominal
    phrase a report would use. "HTTP 200 chưa chứng minh quyền truy cập" is a
    memo; the author rewrote it as "HTTP 200 nhưng chắc gì đã vào được". Cut trailing explanatory clauses
    (", highlighting...", ", cho thấy...", ", góp phần..."); they are rule 16 disguised as grammar.
    Vietnamese section 20.

21. **Titles, headings, labels, and figure text get their own pass.** List every one separately and read
    it as prose. No colon in a title or heading, no counting cadence ("Six steps, three figures"), no
    negative headings, no teaser questions, no question as a title, no self-certifying adjectives ("So
    sánh công bằng" became "So sánh"), no popularity numbers of someone else's post in a title. The
    blacklist targets body sentences and cannot read text inside images, so title patterns slip through.
    Vietnamese section 21.

22. **Say each fact once, and do not narrate the figure.** The same fact in title, lede, body, caption,
    and alt text reads as padding. Text beside a figure says what the figure cannot: why, so what, what
    to notice. It does not retell what the figure already shows, and it does not point at it ("Read the
    data line in Figure 2"). Vietnamese section 22.

23. **Keep the reason and the joke when cutting.** When asked to be brief, keep the reason and the
    author's edge; the author's own short messages are often longer than the agent's clipped
    commands (see `author-corrections.md`). A concrete twist at the end of a paragraph is fine when it
    carries a real object, number, or person; an abstract moral is not. Keep the author's real jokes;
    never add staged ones. Vietnamese sections 23 and 24.

## Quick checks

Run this pass before delivering prose:

- Any empty intensifiers? Cut them; preserve modifiers carrying evidence, precision, or conditions.
- A passive that hides who decided or caused something? Name the actor. Leave harmless passives alone.
- Inanimate thing doing a human verb ("the decision emerges")? Name the person.
- A Wh- opener used only as a rhetorical setup? Restructure it; keep actual research or diagnostic questions.
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
- Does a dense block need breathing room? Try spacing, an example, or clarification, not compulsory filler.
- Count sections ending on a shaped punchline. Over half? Let some end flat.
- Counting sentences or lines in a source ("in exactly one sentence")? Delete the number; if nothing changes, leave it deleted.
- Any sentence rating a fact instead of stating one ("surprisingly simple", "easy to miss")? Cut the rating, show the fact.
- For each sentence you would fight to keep: did the content need it, or did the paragraph feel unfinished? Cut the second kind.
- Any file name, tool name, check date, "đã đọc N trang", prompt constraint, username, or revision history? Delete (rule 19).
- Any time, weekday, scene, or feeling with no source behind it? Delete or ask the author (rule 4).
- Listed every title, heading, caption, alt text, slide title, and text inside images, and read each one? (rule 21)
- Same fact in two places? Keep the one where the reader needs it (rule 22).
- Trailing ", highlighting..." or ", cho thấy..." clause? Cut it or give its fact its own sentence.

Vietnamese-specific (see [references/vietnamese-patterns.md](references/vietnamese-patterns.md) quick
check section for the full list):

- Any "không A, mà B" / "không nằm ở A, nó nằm ở B" binary contrast? State Y directly.
- Any signpost "Nói cách khác:" / "Điểm chốt:" / "Tức là:"? Cut.
- Any template "Từ X tới/đến Y" (including "từ X sang Y") in a title, heading, caption, or
  summary? Name the subject or state the claim instead. Keep literal ranges, routes, and actual
  conversions; see section 19 of [vietnamese-patterns.md](references/vietnamese-patterns.md).
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

## Authorship, evidence, and captions

- Check who "I/mình" refers to. Assistant work status is not an author's biography or experience.
- Read repeated "mình sẽ / mình dự kiến" across the whole draft. In an explainer, replace task narration
  with the method itself; preserve genuine plans in proposals and user-supplied personal context.
- Put evidence limits beside the relevant example or claim. Keep "Số liệu minh họa" with invented
  numbers; avoid repeating the same disclaimer in the intro, body, caption, and footer.
- Captions explain the figure, units, provenance, and material edits. Put rendering tools and QA logs
  in production notes unless the article is teaching those tools. Do not add production-style
  headers/footers to screenshots by default.

Examples and counterexamples: [authorship-and-evidence.md](references/authorship-and-evidence.md).

## Blacklist quét bằng máy (tiếng Việt)

[references/blacklist-vi.txt](references/blacklist-vi.txt) giữ các cụm đã bị bắt tại
trận, dạng pattern ERE mỗi dòng một cái. Chạy trước khi ship:

```bash
# Run from the skill directory; replace bai.mdx with the draft path.
grep -vE '^[[:space:]]*(#|$)' references/blacklist-vi.txt | grep -n -i -E -f - bai.mdx
```

Kết quả là chỗ cần nhìn, không phải chỗ phải sửa. Đọc từng câu rồi mới quyết, vì có
dương tính giả (ví dụ "phải trả" khi bài đang nói về tiền thật).

Chạy blacklist trước và sau mỗi lượt sửa rồi diff hai danh sách hit. Hit mới xuất hiện sau
lượt sửa là slop do chính lượt sửa đẻ ra: Antislop thấy cấm một bộ pattern làm mọc pattern
khác (Paech et al. 2025), và thí nghiệm E6 ngày 18/10/2026 đo được 10 lượt dọn bài chèn thêm
10 hit mới.

Bắt được cụm mới thì thêm vào file đó, kèm chú thích lý do và ngày trong nhóm của nó, rồi
thêm một câu bị bắt và một câu hàng xóm đọc ổn vào `scripts/test_vietnamese_blacklist.py`.
Không ghi lý do thì lần sau lại tưởng là câu hay. Chạy test:
`python3 scripts/test_vietnamese_blacklist.py`.

## Scoring

Rate 1-10 on each dimension:

| Dimension | Question |
|-----------|----------|
| Directness | Statements or announcements? |
| Rhythm | Varied or metronomic? |
| Trust | Respects reader intelligence? |
| Authenticity | Sounds human? |
| Density | Anything cuttable? Are dense passages readable without padding? |
| Evenness | Do all sections land the same shape? Uniform is worse than lumpy. |

Use the rubric to organize a review, not as a gate. Strong LLMs judge writing quality barely above
chance (Chakrabarty et al. 2025b), and drafts that scored above 42/60 here were still rejected by the
author. The gate is countable: blacklist hits before and after, every heading and caption read,
workshop-leak grep clean, word count not grown by the edit pass. When two versions are close, show
both to the author and let them pick. Report the score only when the user asked for a review; when
they asked for a draft, apply the rules silently and hand over the clean text. A user-identified issue
overrides any score; inspect the whole draft for the same cause.

## Workflow

**Drafting.** Read `author-corrections.md` first when writing for a specific author. Apply the core
rules while writing. Do not write slop and then strip it. When a phrase is uncertain, search it (rule
18) at the moment of doubt rather than shipping it and hoping the review pass catches it. The review
pass only catches patterns already on a list. Write Vietnamese from notes, not from an English draft
translated afterwards. For an opening, title, or example, write five options, drop the most typical
one, and offer the author the rest; models default to the most familiar phrasing (typicality bias,
Zhang et al. 2025, Verbalized Sampling).

**Sửa bằng cách xoá (thêm 20/09/2026, tiếng Việt).** Mọi lần sửa phải là xoá hoặc thay tại chỗ. Chữa một lỗi bằng cách chèn thêm câu giải thích hay thú nhận là cách slop sinh ra nhanh nhất: ngày 20/09/2026, một bài đã qua lượt stop-slop vẫn đầy slop, và 5/9 câu bị bắt là do chính lượt review chèn vào. Đo bằng số chữ trước và sau: lượt sửa slop mà làm bài dài ra thì phải giải trình từng câu đã thêm. Hit blacklist thì xoá ý đó, đừng đảo câu cho lọt regex. Ngoại lệ duy nhất là lỗi thiếu chi tiết: chỉ được chèn chi tiết lấy từ tác giả hoặc từ nguồn có ghi, không chèn câu giải thích. Người viết chuyên nghiệp sửa văn LLM bằng 74% thay thế, 18% xoá, 8% chèn (Chakrabarty et al. 2025, LAMP).

**Editing a draft.** Read [references/phrases.md](references/phrases.md),
[references/structures.md](references/structures.md), and
[references/workshop-leaks.md](references/workshop-leaks.md) first, then rewrite. For Vietnamese prose, also
read [references/vietnamese-patterns.md](references/vietnamese-patterns.md). Include headings,
captions, and closing notes in a full-piece review. Do not edit source quotations or code as prose.
Read the revised piece again for flow and check that scope, evidence limits, numbers, and attribution
survived. Return the revised text.
List the cuts only if the user asked what changed.

**Reviewing.** Use a fresh reviewer that reads every file in `references/` before reading the draft;
a self-review that only greps the blacklist misses most of what the author later catches. Quote the
offending span, name the pattern, give the replacement. Explain any apparently similar construction
kept for meaning or genre. Then score.

**When the author corrects you.** Add the pair to `author-corrections.md` the same day. If the
correction is a new pattern, add it to the right reference file and, for Vietnamese, to the blacklist
with a test case. When asked for skill
improvements, distinguish existing rules from genuinely missing guidance and propose changes; do
not modify the skill unless the user requests it.

See [references/examples.md](references/examples.md) for before/after transformations.

## Typography convention

Use ASCII `-`, `"`, and `'` in authored prose for this skill. Preserve verbatim source quotations,
code, formulas, and identifiers; do not normalize them as a prose-style edit.

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

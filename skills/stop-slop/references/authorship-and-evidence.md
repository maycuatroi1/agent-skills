# Authorship, evidence, and captions

Use when editing on someone's behalf, explaining technical work, or preparing illustrated prose.
These rules apply to English and Vietnamese; examples use Vietnamese where the failure is easier
to see. Preserve the requested genre and the author's supplied context.

## 1. Keep the narrator separate from the assistant

A sentence about what the assistant has or has not done is not automatically true of the author.
Review first-person claims of experience, uncertainty, and intention: "I tested", "I have not read",
"mình chưa làm", "mình sẽ", "mình dự định". Do not invent actions, feelings, plans, or anecdotes to
make a draft sound personal. Keep first-person context supplied by the user when it serves the piece.

| Before | Edit | Reason |
|---|---|---|
| "Mình chưa thực hiện nghiên cứu này" added because the assistant only drafted the article | Delete the unsupported author claim; label the constructed example where it appears | Assistant status was assigned to the author |
| "Đây là những nguồn mình dự kiến xem, chưa phải các nguồn đã search cho bài blog" | "Các nguồn để cân nhắc gồm..." | A recommendation does not need the assistant's execution history |
| "Mình đã thử cách này suốt một tuần" with no supplied experience | Remove it or ask for the missing experience if it is central | Specificity must not become fabrication |

Check the whole piece, not just individual sentences. An explainer with "mình sẽ / mình dự kiến"
at every step reads like a work plan. Describe the method instead of announcing each future action.
Do not replace every first-person sentence with an imperative; vary the form and keep the voice.

**Counterexamples to keep:**

- A user-supplied opening such as "Mình định viết một bài review về..." that explains the topic choice.
- "Tuần tới tôi sẽ phỏng vấn năm người" in a proposal or actual plan. The future tense is the content.
- An explicit author disclosure required by the genre or publication, based on supplied facts.

## 2. Put evidence limits beside the relevant claim

Ask whether the caveat changes what the reader may infer. If it does, keep it near the result,
example, or recommendation. If it only reports the drafting process or reassures the reader that
the assistant was careful, remove it from the prose or put it in a separate handoff note.

- Constructed numbers: put "Số liệu minh họa" with the figure and introduce the example as hypothetical.
  Do not repeat the same warning in the introduction, body, caption, and footer without a reason.
- Untested query: introduce "Một query để thử" and explain how to test it. Do not imply it was validated.
- Different benchmarks: retain the limit on comparing success rates; changing the wording must not
  turn incomparable measurements into a ranking.
- Missing cost data: retain "không được báo cáo". Do not replace missing values with zero for brevity.

Words such as "may", "if", "approximately", "có thể", "nếu", or "chưa đủ" can carry evidence or
conditions. A clearer sentence is not necessarily a more certain one. Preserve mandatory disclosures,
source attribution, and material uncertainty even when that makes the prose less punchy.

## 3. Use bilingual terms for meaning and audience

Keep technical nouns the audience uses, especially when they distinguish concepts or help readers
look up a source. Prefer natural Vietnamese for ordinary terms when the English adds no precision.
Explain unfamiliar terms once and use them consistently. Read the whole sentence after replacing a
term; a dictionary substitution can break Vietnamese grammar.

| Awkward phrasing | Context-appropriate edit |
|---|---|
| "quyết định eligibility ở bước full text" | "đọc toàn văn và quyết định bài có đủ điều kiện" |
| "lượng citations và thứ hạng venue" | "số lượt trích dẫn và thứ hạng nơi công bố" |
| "thu hẹp đối tượng, điều kiện so sánh và outcome" | "xác định nhiệm vụ, phương án so sánh và đo hiệu quả bằng gì" |
| "Appendix ... abstract" in a general Vietnamese explanation | "Phụ lục ... phần tóm tắt" |

These are examples, not a replacement dictionary. In a paper explaining PRISMA's vocabulary,
record/report/study may need to remain in English. In an ML article, attention, token, and benchmark
may be the audience's working terms. Do not translate everything or enforce an English-word quota.
Read alongside section 13 of [vietnamese-patterns.md](vietnamese-patterns.md).

## 4. Keep captions about the figure

Captions should help the reader interpret the figure: what it shows, units, source, and relevant
scope. Keep licenses and attribution where required. Disclose highlighting, cropping, blurring, or
other material edits without inserting a production report into every image.

- "Dựng bằng thư viện X, render bằng browser, đã kiểm tra..." belongs in production notes when the
  article is about research methodology. A useful caption describes the research flow and links the source.
- A tutorial about library X may need that same tool information in the caption. Preserve it there.
- A source screenshot normally needs the source page and the relevant passage. Do not automatically
  add an editorial header, footer, badge, or QA status to the image. Put the source link in the caption.
- An illustrative figure still needs its illustrative label; an edited screenshot still needs an
  honest description of material edits. Removing clutter must not imply stronger evidence.

## Final read

Read the piece including its opening, transitions, captions, and ending. Check that edits preserve
the requested genre, narrator, figures, qualifiers, and attribution. Keep genuine research questions,
functional lists, and accurate technical contrasts; do not change them merely to avoid a pattern.

Record concrete edits and unresolved concerns before scoring. Scores and blacklist hits are aids,
not proof of natural prose. If a user identifies a missed issue, look for its cause elsewhere in the
piece instead of defending the earlier score or only deleting the quoted sentence.

# Workshop leaks

Nothing from the workshop reaches the reader. An agent leaves traces of how it worked: file names, the date it
checked something, how many pages it read, constraints copied from the prompt. Those traces belong in a handoff note
to the person who assigned the work. In the deliverable they read as machine-written, and readers say so: "đọc phát
biết văn của AI viết".

Most examples below were caught by the author in drafts that had already passed a stop-slop review.

**Test.** Delete the phrase. Does the reader lose anything they can use? If the phrase only proves the writer was
careful, records how the piece was produced, or repeats what the assignment said, it goes.

## 1. Tool, file, and script names

| Caught | Fix |
|---|---|
| `Source: slides/assets/drawio/osi-position.drawio - editable, rebuild with make-diagrams.py` on a lecture slide | Delete. Keep the source path in the repo README |
| "`model.py` chứng minh bảy đồng nhất thức bằng sympy" | Keep the identities, drop the script and the solver |
| `Nguồn sơ đồ: QACI-Offensive-Agent-v3.drawio` under a figure | Delete |
| "Hình vẽ bằng matplotlib", "render bằng Manim" in a caption | Delete unless the article teaches that tool |

**Keep** tool names that are the subject (a tutorial on matplotlib), a methods section of a paper that must be
reproducible, and download links the reader can use ("Bạn có thể tải bộ đề và script phân tích").

## 2. Verification stamps

| Caught | Fix |
|---|---|
| "Trạng thái ghi nhận ngày 18/10/2026" | Delete. The publication date already dates the piece |
| "Trạng thái đối chiếu code trên origin/main, kiểm ngày 2026-09-27." | Delete. If staleness matters, say what may change |
| "Checked against the latest docs on 2026-10-02" | Delete, or date the specific fact that moves |

A fast-moving number (a price, a star count, a leaderboard rank) still carries its month, written the way a person
says it: "giá tháng 10/2026 là 15 USD".

## 3. Diligence claims

| Caught | Fix |
|---|---|
| "SPEAR full paper đã đọc 9 trang" | Delete. The author's comment: "đương nhiên cho vào thì phải đọc rồi" |
| A screenshot of a login page as evidence | Delete. It proves the agent logged in, not the claim |
| "Đã kiểm lại hai lần", "I verified each number against the source" | Delete. Show the source instead |

Evidence is the quoted passage or the measured number.

## 4. Prompt echo

| Caught | Fix |
|---|---|
| "Phạm vi: phòng lab / eval được cấp phép • Bản draft" in a figure footer | Delete. The author: "rõ ràng là lấy từ promt" |
| "Phạm vi. Tài liệu lập luận ở mức kiến trúc... qua một cổng human review" as an opening paragraph | Delete. Put a real scope statement in one clause only if the reader needs it |
| "Ví dụ 2025-2026, tách phạm vi Windows, Linux và mạng Active Directory." | Delete, or turn it into content the reader needs |
| "Không bịa kết quả lab", "theo yêu cầu", "as requested" | Delete |

Check every disclaimer, scope line, and footer against the prompt or brief. If it paraphrases an instruction, delete
it.

## 5. Handles, minor names, and backstage history

| Caught | Fix |
|---|---|
| "Trong thread trên r/LocalLLaMA, `tiensss` yêu cầu..." | "Nhiều người dùng yêu cầu..." (keep the true count: one person is "có người") |
| Preprint author names, small project names, a side project's minor numbers | Delete unless the reader needs them to reproduce or compare |
| "Ban đầu đề cương thế này, nhưng cuối cùng thế này" | Describe the final state only |
| Errata history, "bản trước của bài này viết sai..." | Fix the text. Add a dated correction note only for a material error in a published piece |

Citation fields printed on the page (author, note) follow the same rule: "Hacker News", "r/LocalLLaMA", not
usernames; a note says what the source is and what it supports, not how it was fetched.

## 6. Metadata chrome on slides and documents

| Caught | Fix |
|---|---|
| "How today runs", instructor name, class code, room, and date as a running header on content slides | Put logistics on the title slide only, or nowhere |
| "OSG203 / PROCESSES / 21 SEPTEMBER 2026" over every slide | Delete |
| A large header "Run #1 running, plan run" above the content a screen is about | Delete; show details on demand |

The author's comment: "Nó là slide bài giảng thì tập trung vào nội dung, thêm mấy cái metadata này vào nội dung làm
quái gì ?"

## 7. Fake specificity

Rule 4 asks for specifics. Without a source, a model meets it by inventing them.

| Caught | Fix |
|---|---|
| "It is 2 a.m. and the shop is slow" | Delete the staged scene; start with the problem |
| "Last night at 23:59", "What you should be able to do at 12:20", "140 minutes, three syllabus sessions" | Delete. The author: "Nghe nó rất giả tạo" |
| "Hôm thứ ba tuần trước, mình đang ngồi debug..." with no such event in the brief | Delete or ask the author for the real event |
| "model gọi mọi thứ là mèo, nhìn confusion matrix, đóng laptop" | Keep the real detail ("accuracy tụt gần nửa"), drop the embellishment |

A specific is legitimate when it comes from a source, a measurement, or the author. Times, scenes, feelings, and
counts that come from nowhere are fabrication.

## 8. Saying the same thing twice

The same fact in the title, the lede, the body, the caption, and the alt text reads as padding even when each
instance is short. The author: "mày có thấy là duplicate thông tin không ?". Give each fact one home: the place
where the reader needs it.

## Final read

Grep the deliverable, including headings, captions, alt text, speaker notes, citation notes, and text inside images:

- file extensions (`.py`, `.drawio`, `.ipynb`, `.json`) outside code blocks
- "ghi nhận ngày", "kiểm ngày", "đối chiếu", "as of", "checked on"
- "đã đọc", "đã kiểm", "verified"
- "draft", "bản nháp", "phạm vi", "được cấp phép", "theo yêu cầu", "as requested"
- `@`, `u/`, backticked handles
- clock times and weekdays in narrative ("lúc 11 giờ đêm", "tối thứ sáu")

Each hit is a candidate. Read the sentence, apply the test at the top, and delete rather than rephrase.

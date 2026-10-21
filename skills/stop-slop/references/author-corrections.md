# Author corrections

When the author rewrites one of your sentences, the rewrite outranks every rule in this skill. A sentence can pass
every check and still be one the author would never say. Rules describe what to avoid; the author's own edits show
what the target sounds like.

Evidence for working this way: professional writers editing LLM prose mostly replace text in place (74% of edits),
delete 18%, and insert 8% (Chakrabarty et al. 2025, LAMP corpus); preference descriptions inferred from a user's edits
beat prompt-only baselines (Gao et al. 2024, CIPHER); and few-shot imitation from pasted samples barely works for
blog prose, around 17-21% authorship-verification accuracy with five samples, with little gain from more (Wang et
al. 2025). Pairs of before and after carry more signal than another page of rules.

## How to use

1. Before editing someone's prose, read the pairs below whose context matches (blog, slides, chat message, doc).
2. When an edit is uncertain, compare it to the closest pair, not only to the rules.
3. When the author corrects you, add a row the same day: what you wrote, what they wrote or said, the context, the
   pattern. If they only said what was wrong, record their words; do not invent the "after".

## Pairs from Bình (omelet.tech, teaching, project docs)

| Context | Agent wrote | Bình wrote or said | Pattern |
|---|---|---|---|
| Blog, 2026-10-19 | HTTP 200 chưa chứng minh quyền truy cập | HTTP 200 nhưng chắc gì đã vào được (plus a meme: JSON `status: 403`, `message: "Cút ra ngoài"`) | Document register to spoken register; humor from a real artifact |
| Doc heading, 2026-10-21 | So sánh công bằng | So sánh | Self-certifying adjective |
| Blog, 2026-09-20 | câu trên slide còn đúng | Monolith | Name the thing, do not point at text |
| Blog, 2026-09-19 | electromagnetic-wave example for square roots | "Bạn là một thợ xây hy lạp, odysseus chuẩn bị đi đánh trận về. Ông ấy muốn một cái hồ hình vuông có thể chứa lượng nước nặng bằng 10 con bò. Làm thế nào ?" | Everyday example with a character and countable objects |
| Blog, 2026-10-19 | Trong thread trên r/LocalLLaMA, `tiensss` yêu cầu... | nhiều người dùng yêu cầu... | Handles are backstage |
| Blog, 2026-09-19 | chín mươi chín team | 99 team | Measured counts in digits |
| Blog, 2026-10-18 | Trạng thái ghi nhận ngày 18/10/2026 | (deleted) "ngày viết bài là ngày này người ta xem là xong" | Verification stamp |
| Report, 2026-10-14 | SPEAR full paper đã đọc 9 trang | (deleted) "đương nhiên cho vào thì phải đọc rồi" | Diligence claim |
| Blog, 2026-09-22 | Đây là đề xuất để thử, chưa phải một hệ thống đã triển khai... | (deleted) "Rất ai slob kiểu assistant" | Hedge stacking |
| Blog, 2026-09-21 | Nếu bạn thấy mình tính sai ở đâu... mình muốn được cãi lại. | (deleted) | Templated closing invitation |
| Blog title, 2026-09-21 | x^x = 49: câu sai trong bài Medium 1.4K clap và lời sửa trong comment | "việc quái gì mention medium 1.4k clap lên header làm gì ?" | Popularity numbers and colon in a title |
| Doc heading, 2026-09-25 | Tầng 0, hiện trạng: một hoá đơn bằng giờ người | "đặc mùi ai slop" | Label, colon, and metaphor heading |
| Slides, 2026-09-20 | It is 2 a.m. and the shop is slow | "chẳng ai viết kiểu này cả" | Staged scene |
| Messenger to students, 2026-10-12 | "hệ thống AI hỗ trợ triage" ở mục tiêu, không RQ nào, phép đo nào nói tới AI. Bỏ hoặc đo | ... không RQ nào, phép đo nào nói tới AI. Tự nhiên nó mọc ra ở đây | Keep the jab when cutting |
| Messenger to students, 2026-10-12 | Bọn em tự viết rule rồi tự dựng đáp án thì hội đồng hỏi 1 câu là xong | Hay bọn em tự viết rule rồi tự dựng đáp án rồi tự claim là cách làm của tôi VIP pro hơn | Mimic the target's voice instead of predicting consequences |
| Messenger to students, 2026-10-12 | Sửa thẳng lên bản online để thầy track change, xong báo thầy | Bọn m sửa lên bản online nhé. Thầy sẽ check change để review chứ không đọc lại full cho bọn m kiểu mỗi tuần 1 file mới tinh nữa. OK ? | Give the reason; end with a tag question |

## What the pairs have in common

- The author's version is often **longer** than the agent's terse one in chat, and **shorter** in prose. Agents
  compress messages into commands and pad articles with hedges; the author does the opposite.
- The author's version uses verbs and modal particles ("chắc gì đã", "tự nhiên nó mọc ra") where the agent used
  nominal phrases ("chưa chứng minh quyền truy cập").
- The author's jokes come from something real: a real HTTP response, the students' own claim, the author's own
  failure. Never from an invented scene.
- Most corrections are deletions. When the author keeps a sentence but changes it, the change is toward how a
  person would say it aloud.

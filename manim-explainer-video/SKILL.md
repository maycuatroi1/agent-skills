---
name: manim-explainer-video
description: This skill should be used when the user asks to "làm video giải thích", "tạo video Manim", "make an explainer video", "animate this concept", "video giải thích thuật toán/khái niệm", "dựng video toán/ML bằng Manim", or wants an animated technical explainer with Vietnamese narration, subtitles, and a timecoded dubbing script. Provides a working Manim scaffold (light theme, real-number pipeline, cue-based SRT generation) plus the macOS workarounds required to make Manim render at all.
version: 1.0.0
---

# Video giải thích bằng Manim

Dựng video giải thích kỹ thuật bằng Manim Community: nền sáng, tiếng Việt, số liệu
tính thật, kèm kịch bản lời bình có timecode và phụ đề SRT khớp chính xác khung hình.

Đã dùng thật cho video hồi quy tuyến tính (1080p60, 3 phút 49, 61 câu lời bình).

## Bắt đầu

Tạo thư mục video mới và dựng môi trường trong một lệnh:

```bash
~/.claude/skills/manim-explainer-video/scripts/new-video.sh <thư-mục-đích> [slug]
```

Script copy scaffold, cài `dvisvgm` / `mupdf-tools` / `ffmpeg` / font Inter, tạo venv,
cài Manim, rồi **render thử một scene có cả tiếng Việt lẫn LaTeX** để chứng minh
pipeline chạy được trước khi bắt tay viết nội dung. Idempotent, chạy lại vô hại.

Nếu thư mục đã có sẵn thì chỉ chạy `scripts/setup.sh <thư-mục>`.

## Chỉ phải viết hai file

Scaffold cho sẵn `theme.py`, `build_final.py`, `render.sh`, `manifest.py`. Ba file đầu
tái dùng nguyên vẹn, **không sửa**. Việc thật nằm ở hai file:

**`data.py`** giữ mọi con số sẽ hiện lên màn hình, tính thật bằng numpy. Không hard-code
số trong `scenes.py`. Lý do không phải sạch sẽ: video giải thích mà bịa số thì mất sạch
giá trị, và tính thật thì đổi input là cả video tự đổi theo. Chạy `python data.py` in hết
số liệu ra kiểm tra bằng mắt trước khi dùng.

**`scenes.py`** chứa các cảnh. Tên class phải khớp `manifest.py` (đó là nguồn duy nhất cho
danh sách và thứ tự cảnh, cả `render.sh` lẫn `build_final.py` đều đọc từ đó).

## Ba luật không được phá

Vi phạm là render chết hoặc chữ vỡ. `scripts/check.sh` bắt cả ba bằng grep.

1. **Tiếng Việt luôn đi qua `Text()` + Pango. LaTeX chỉ chứa ASCII.**
   `MathTex(r"\text{diện tích}")` lỗi Unicode. Ghép chữ Việt với công thức thì tách:
   `VGroup(Text("Diện tích"), MathTex("= e^2")).arrange(RIGHT)`.

2. **`MathTex` chỉ nhận một chuỗi.** Pipeline `pdflatex` + `mutool` không sinh group id
   nên `MathTex("a", "=", "b")` gộp thành 1 submobject, `formula[i]` sẽ `IndexError`.
   Cần tô màu từng phần thì ghép nhiều `MathTex` rồi `arrange()`.

3. **Không dùng em-dash ở bất kỳ đâu**, kể cả lời bình trong `self.cue()`. Thay bằng
   dấu hai chấm, dấu phẩy, hoặc tách câu.

## Lời bình và timecode

Đặt `self.cue("câu thoại")` **ngay trước** `self.play()` mà câu đó đi kèm:

```python
self.cue("Đổi w thì đường xoay.")
self.play(wt.animate.set_value(0.075), run_time=1.7)
```

`CueScene` ghi lại `self.renderer.time` tại đúng thời điểm đó. `build_final.py` cộng
offset bằng độ dài `.mp4` thật (ffprobe) rồi sinh SRT. Nghĩa là chỉnh timing animation
thì timecode phụ đề tự đổi theo, không bao giờ lệch và không phải sửa tay.

`build_final.py` cảnh báo khi một câu dài hơn quỹ thời gian dành cho nó (mốc ~4,5 âm
tiết/giây). Gặp cảnh báo thì rút gọn lời **hoặc** nới `self.wait()`, thường phải làm cả
hai. Đọc `references/narration.md` trước khi viết lời: cách viết số cho vừa đọc vừa hiển
thị, và giọng nên dùng.

## Lồng tiếng

Đưa `final/narration.tsv` (hoặc `subtitles.srt`) cho TTS, **bắt buộc chọn chế độ bám
timecode**, đừng để nó đọc liền một mạch. Vbee đã dùng thật và bám tốt.

Kiểm tra trước khi ghép, đừng tin là khớp:

```bash
./check-audio.sh narration.mp3    # dò đoạn có tiếng, so với mốc cue
```

Khớp thì đặt file tên `narration.mp3` ở gốc thư mục video, `build_final.py` tự ghép,
giữ nguyên hình (`-c:v copy`) và pad audio cho bằng độ dài. Luôn ghép từ bản câm nên
chạy lại bao nhiêu lần cũng như nhau. Chi tiết cách đọc kết quả: `references/narration.md`.

## Vòng lặp làm việc

```bash
./render.sh -ql     # 480p15, nhanh: lặp ở đây cho tới khi nội dung đúng
./check.sh          # em-dash, LaTeX tiếng Việt, MathTex nhiều tham số
./render.sh         # 1080p60, bản giao (tự ghép narration.mp3 nếu có)
```

**Trích frame ra xem thật, đừng tin là ổn.** Lỗi chồng chữ và tràn khung không bao giờ
lộ ra lúc chạy, chỉ lộ ra khi nhìn:

```bash
ffmpeg -ss 42 -i media/videos/scenes/480p15/S03.mp4 -frames:v 1 -y /tmp/f.png
```

Xem ít nhất 2-3 frame mỗi cảnh. Đây là bước hay bị bỏ và luôn tìm ra lỗi.

## Kết quả

`render.sh` xuất ra `final/`:

| File | Dùng để |
|---|---|
| `<slug>.mp4` | Video 1920×1080, 60fps, có tiếng nếu đã đặt `narration.mp3` |
| `script.md` | Kịch bản có timecode, chia theo cảnh, cho người lồng tiếng |
| `subtitles.srt` | Phụ đề, nạp thẳng vào player hoặc YouTube |
| `narration.tsv` | `start · end · text`, đưa cho TTS |

## Tài liệu kèm theo

- **`references/macos-gotchas.md`** đọc khi Manim báo lỗi lạ. Bốn cái bẫy trên macOS
  (LaTeX chọn nhầm bản, dvisvgm không đọc DVI, font vỡ dấu, ffmpeg thiếu libass) kèm
  triệu chứng chính xác để nhận ra ngay. `setup.sh` đã gỡ sẵn cả bốn.
- **`references/scene-patterns.md`** đọc trước khi viết `scenes.py`. Luật bố cục chống
  chồng chữ, `ValueTracker` + `always_redraw`, biến đại lượng trừu tượng thành diện tích
  nhìn được, nối hai không gian, phát lại thuật toán chạy thật.
- **`references/narration.md`** đọc trước khi viết lời bình. Đặt cue, canh nhịp, viết số,
  giọng văn.

## Thiết kế

Palette và font sinh từ skill `ui-ux-pro-max` (light theme), style Minimalism & Swiss:
nhiều khoảng trắng, không đổ bóng, không gradient, **một màu nhấn duy nhất** (amber, dành
cho sai số và nhấn mạnh). Đổi màu hoặc font thì sửa `theme.py`, cả video đổi theo. Không
hard-code màu trong `scenes.py`.

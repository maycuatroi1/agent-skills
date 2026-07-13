# Bốn cái bẫy khi chạy Manim trên macOS

Mỗi cái đều làm mất thời gian debug lần đầu. `scripts/setup.sh` đã gỡ sẵn cả bốn.
File này ghi lại **triệu chứng** để nhận ra ngay khi gặp lại, và **lý do** để biết
khi nào workaround không còn cần nữa.

---

## 1. Manim gọi nhầm bản LaTeX

**Triệu chứng.** Render bất kỳ scene nào có `MathTex` thì hỏng. Log LaTeX có:

```
! LaTeX Error: File `standalone.cls' not found.
Enter file name:
! Emergency stop.
```

**Nguyên nhân.** Máy có hai bản TeX. `/usr/local/bin/latex` là bản tối giản
(BasicTeX / TeX Live nhỏ) và **thiếu `standalone.cls`**, mà Manim bắt buộc dùng
documentclass đó. Homebrew texlive có đủ nhưng nằm sau trong `PATH`.

**Cách gỡ.** Đẩy `/opt/homebrew/bin` lên đầu `PATH` **trước khi `import manim`**.
Đã có sẵn ở đầu `theme.py`:

```python
import os
os.environ["PATH"] = "/opt/homebrew/bin:" + os.environ.get("PATH", "")
from manim import *
```

Thứ tự quan trọng: Manim gọi `latex` qua subprocess, subprocess kế thừa `os.environ`
tại thời điểm gọi, nên sửa `PATH` sau khi import vẫn kịp. Nhưng đặt trước cho chắc.

**Kiểm tra nhanh.**
```bash
kpsewhich standalone.cls        # phải ra đường dẫn trong Cellar/texlive
```

---

## 2. dvisvgm không đọc được DVI

**Triệu chứng.** Manim báo lỗi nghe như dvisvgm quá cũ, dù vừa cài bản mới nhất:

```
ValueError: Your installation does not support converting .dvi files to SVG.
Consider updating dvisvgm to at least version 2.4.
```

Chạy tay thì thấy lý do thật:

```
WARNING: PostScript header file tex.pro not found
PostScript error: undefined in TeXDict
```

**Nguyên nhân.** dvisvgm của Homebrew link vào libkpathsea nhưng resolve `TEXMFROOT`
theo vị trí binary của chính nó (trong `Cellar/dvisvgm/`), nên không tìm ra các file
PostScript header (`tex.pro`, `texps.pro`...). Đặt `TEXMFCNF` **không cứu được**.

**Cách gỡ.** Bỏ đường DVI, đi đường PDF. Đã có sẵn trong `theme.py`:

```python
config.tex_template = TexTemplate(tex_compiler="pdflatex", output_format=".pdf")
```

Đường PDF cần `mutool` (`brew install mupdf-tools`), vì dvisvgm từ chối
Ghostscript >= 10.01:

```
ERROR: To process PDF files, either Ghostscript < 10.01.0 or mutool is required.
The installed Ghostscript version 10.06.0 is not supported.
```

### Hệ quả phải nhớ: MathTex nhiều tham số vỡ

SVG do mutool sinh **không có group id**, mà Manim dựa vào group id để tách
`MathTex` thành các submobject theo từng chuỗi. Nên:

```python
f = MathTex(r"\hat{y}", "=", "w", "x")   # -> chỉ 1 submobject, không phải 4
f[2].set_color(BLUE)                      # IndexError: list index out of range
```

Log sẽ có `ERROR MathTex: Could not find SVG group for tex part ...`.

**Cách viết đúng.** Một chuỗi duy nhất, tô màu cả cụm:

```python
f = MathTex(r"\hat{y} = w \cdot x + b", color=MODEL)
```

Cần tô màu từng phần thì ghép nhiều `MathTex` rời:

```python
VGroup(MathTex("w", color=MODEL), MathTex("="), MathTex("2")).arrange(RIGHT, buff=0.15)
```

`scripts/check.sh` bắt lỗi này bằng grep.

---

## 3. Font vỡ dấu tiếng Việt

**Triệu chứng.** Chữ hiện trên video bị tách rời ở đúng vài từ:
"thước" thành "th ư ớc", "bước" thành "b ư ớc", "trước" thành "tr ư ớc".
Chỉ xảy ra ở **weight bold**, chữ thường trông gần như bình thường nên rất dễ lọt.

**Nguyên nhân.** Helvetica Neue thiếu glyph tổ hợp cho các ký tự như U+1EDB (ớ)
ở bold, Pango phải fallback sang font khác giữa chừng và spacing vỡ.

**Cách gỡ.** Dùng **Inter** (`brew install --cask font-inter`). Inter phủ kín
tiếng Việt ở mọi weight. Đã đặt trong `theme.py`:

```python
FONT_SANS = "Inter"
FONT_MONO = "JetBrainsMono Nerd Font"
```

**Cách kiểm font khác.** Render thử một scene chỉ có một dòng, cả regular và bold:

```
thước đo · bước học · trước · dữ liệu · mất mát · tối ưu
```

Nếu bold không tách chữ thì font đó dùng được.

### Luật đi kèm: tiếng Việt không bao giờ vào LaTeX

`MathTex(r"\text{diện tích}")` sẽ lỗi Unicode lúc compile. LaTeX chỉ chứa ASCII.
Ghép chữ Việt với công thức thì tách ra:

```python
VGroup(
    Text("Diện tích ô vuông", color=ERROR),
    MathTex("= e_i^2", color=ERROR),
).arrange(RIGHT, buff=0.2)
```

---

## 4. ffmpeg thiếu libass

**Triệu chứng.** Muốn burn phụ đề vào video để xem thử thì:

```
[AVFilterGraph] No option name near 'subtitles.srt'
```

`ffmpeg -filters | grep subtitles` không ra gì.

**Nguyên nhân.** ffmpeg của Homebrew build không kèm libass.

**Hệ quả.** Không burn-in phụ đề bằng `-vf subtitles=` được. Không sao: giao file
`.srt` rời là đủ cho YouTube và mọi player. Muốn **kiểm tra sync** thì trích frame
rồi vẽ phụ đề đang active lên bằng PIL, xem lời có khớp hình không.

Cần bản burn-in thật thì cài `brew install ffmpeg --with-libass` (hoặc dùng
`ffmpeg-full` từ tap khác), nhưng thường không đáng.

---

## Bẫy phụ: ffmpeg gãy sau khi brew nâng cấp x265

**Triệu chứng.** Mọi lệnh ffmpeg/ffprobe chết ngay:

```
dyld[...]: Library not loaded: /opt/homebrew/opt/x265/lib/libx265.215.dylib
```

Manim vẫn render bình thường (nó dùng PyAV, không gọi ffmpeg CLI), nên chỉ lộ ra
lúc ghép video hoặc chạy ffprobe. Sửa: `brew reinstall ffmpeg`.

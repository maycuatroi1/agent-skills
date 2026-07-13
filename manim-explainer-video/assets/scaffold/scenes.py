"""
Cac canh cua video. Ten class phai khop manifest.py.

BA LUAT KHONG DUOC PHA (check.sh grep bat ca ba):

1. Tieng Viet LUON di qua Text() + Pango. LaTeX chi chua ASCII.
   Ghep chu Viet voi cong thuc thi tach ra roi VGroup(...).arrange(RIGHT).

2. MathTex chi nhan MOT chuoi. Nhieu chuoi se gop lam 1 submobject nen
   formula[i] IndexError. Muon to mau tung phan thi ghep nhieu MathTex roi arrange.

3. Khong dung em-dash o bat ky dau nao, ke ca loi binh trong self.cue().

Ly do va vi du: references/macos-gotchas.md.

CUE: dat self.cue("...") NGAY TRUOC self.play() ma cau do di kem. Timestamp lay
tu self.renderer.time nen phu de tu khop. Doc references/narration.md truoc khi viet loi.
"""

from manim import *

import data as D
from theme import (
    INK, MUTED, GRID, DATA, MODEL, ERROR, ERROR_FILL,
    FONT_SANS, FONT_MONO, CueScene, fit, title, sub, body, rule, make_axes, dot,
    section_header,
)


def mono(text, size=22, color=INK):
    return Text(text, font=FONT_MONO, font_size=size, color=color)


# =============================================================== 01. TITLE
class S01Title(CueScene):
    def construct(self):
        head = fit(Text("TIÊU ĐỀ VIDEO", font_size=62, weight=BOLD, color=INK), 11)
        line = rule(width=head.width, color=INK, stroke=3)
        line.next_to(head, DOWN, buff=0.45)
        sub1 = sub("Một câu phụ đề cụ thể, không sáo rỗng", size=30)
        sub1.next_to(line, DOWN, buff=0.45)

        self.cue("Câu mở đầu, đọc trong lúc tiêu đề hiện ra.")
        self.play(Write(head), run_time=1.6)
        self.play(Create(line), run_time=0.6)
        self.play(FadeIn(sub1, shift=UP * 0.2), run_time=0.8)
        self.wait(1.5)

        self.play(FadeOut(*self.mobjects), run_time=0.7)


# =============================================================== 02. CONCEPT
class S02Concept(CueScene):
    def construct(self):
        self.cue("Mảnh thứ nhất.")
        section_header(self, "01  Khái niệm", "Một câu dẫn cụ thể")

        # Vi du bo khung: truc + diem + duong dieu khien boi ValueTracker.
        # Xoa het va viet lai theo noi dung that.
        axes = make_axes([0, 10, 2], [0, 10, 2], x_length=7.2, y_length=4.6)
        axes.shift(LEFT * 2.4 + DOWN * 0.05)
        # Nhan truc x dat o dau mut PHAI de chua giua duoi trong cho caption.
        xlab = Text("trục x", font_size=20, color=MUTED)
        xlab.next_to(axes.x_axis.get_end(), DOWN, buff=0.25)

        self.cue("Đưa dữ liệu lên đồ thị.")
        self.play(Create(axes), FadeIn(xlab), run_time=1.2)

        self.wait(1.0)
        self.play(FadeOut(*self.mobjects), run_time=0.7)

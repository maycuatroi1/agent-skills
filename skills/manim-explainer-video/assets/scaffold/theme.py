"""
Design system + he thong cue. Tai dung nguyen ven cho moi video, khong can sua.

Style: Minimalism & Swiss (grid-based, whitespace, WCAG AAA contrast).
Palette: light data-viz - xanh cho chu the, amber la mau nhan duy nhat.
Nguon: skill ui-ux-pro-max --design-system (light theme).

Doi mau/font o day thi ca video doi theo. Dung hard-code mau trong scenes.py.
"""

import json
import os
import pathlib

# May nay co 2 ban TeX: /usr/local (toi gian, thieu standalone.cls) va Homebrew
# texlive (day du). Manim goi latex qua subprocess nen phai uu tien Homebrew.
os.environ["PATH"] = "/opt/homebrew/bin:" + os.environ.get("PATH", "")

from manim import *

# LaTeX -> DVI -> SVG that bai vi dvisvgm cua Homebrew khong tim thay cac file
# PostScript header (tex.pro...). Duong vong: pdflatex -> PDF -> SVG qua mutool.
config.tex_template = TexTemplate(tex_compiler="pdflatex", output_format=".pdf")

# ---------------------------------------------------------------- palette
BG = "#F8FAFC"       # slate-50   - background
INK = "#0F172A"      # slate-900  - text chinh (contrast 16:1 tren BG)
MUTED = "#475569"    # slate-600  - text phu (contrast 7.5:1)
GRID = "#CBD5E1"     # slate-300  - truc, luoi
FAINT = "#E2E8F0"    # slate-200  - duong ke rat nhat

DATA = "#3B82F6"     # blue-500   - du lieu / chu the chinh
MODEL = "#1E40AF"    # blue-800   - ket qua / duong / mo hinh
ERROR = "#F59E0B"    # amber-500  - sai so / nhan manh (accent DUY NHAT)
ERROR_FILL = "#FDE68A"  # amber-200 - fill nhat cho vung nhan manh

# ---------------------------------------------------------------- fonts
# Helvetica Neue vo cum dau tieng Viet ("thuoc" -> "th u oc") vi thieu glyph
# tien to hop U+1EDB... o weight bold. Inter phu kin tieng Viet o moi weight,
# va dung mood "dashboard / data / precise" ma design system goi y.
FONT_SANS = "Inter"
FONT_MONO = "JetBrainsMono Nerd Font"

# ---------------------------------------------------------------- defaults
config.background_color = BG

Text.set_default(font=FONT_SANS, color=INK)
MathTex.set_default(color=INK)
Tex.set_default(color=INK)


# ---------------------------------------------------------------- cue system
CUE_DIR = pathlib.Path(__file__).parent / "cues"


class CueScene(Scene):
    """Scene co the danh dau moc loi binh.

    Goi self.cue("cau thoai") ngay truoc animation ma cau do di kem.
    self.renderer.time la thoi diem that trong canh, nen timestamp trong SRT
    khop chinh xac voi video chu khong phai uoc luong bang tay.
    """

    def setup(self):
        super().setup()
        self._cues = []

    def cue(self, text):
        self._cues.append({"t": round(float(self.renderer.time), 3), "text": text})

    def tear_down(self):
        CUE_DIR.mkdir(exist_ok=True)
        name = type(self).__name__
        payload = {
            "scene": name,
            "duration": round(float(self.renderer.time), 3),
            "cues": self._cues,
        }
        (CUE_DIR / f"{name}.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        super().tear_down()


# ---------------------------------------------------------------- helpers
def fit(m, max_width):
    """Thu nho mobject neu no rong hon khung cho phep. Khong bao gio phong to."""
    if m.width > max_width:
        m.scale_to_fit_width(max_width)
    return m


def title(text, size=44):
    return Text(text, font_size=size, weight=BOLD, color=INK)


def sub(text, size=26):
    return Text(text, font_size=size, color=MUTED)


def body(text, size=28, color=INK, weight=NORMAL):
    return Text(text, font_size=size, color=color, weight=weight)


def rule(width=10.0, color=GRID, stroke=2):
    """Duong ke ngang mong - dau an Swiss style."""
    return Line(LEFT * width / 2, RIGHT * width / 2, color=color, stroke_width=stroke)


def make_axes(x_range, y_range, x_length=8.0, y_length=5.0, ticks=True):
    return Axes(
        x_range=x_range,
        y_range=y_range,
        x_length=x_length,
        y_length=y_length,
        axis_config={
            "color": GRID,
            "stroke_width": 2.5,
            "include_ticks": ticks,
            "include_tip": False,
            "font_size": 22,
            "tick_size": 0.05,
            "decimal_number_config": {
                "num_decimal_places": 0,
                "color": MUTED,
            },
        },
    )


def dot(point, color=DATA, radius=0.075, opacity=0.85):
    """Diem du lieu - opacity 0.85 theo chart guideline (0.6-0.8 cho density)."""
    return Dot(point, radius=radius, color=color, fill_opacity=opacity)


def section_header(scene, text, subtitle_text=None):
    """Chuyen canh: tieu de section lon giua man hinh roi fade."""
    t = title(text, size=52)
    group = VGroup(t)
    if subtitle_text:
        s = sub(subtitle_text, size=28)
        s.next_to(t, DOWN, buff=0.35)
        group.add(s)
    group.move_to(ORIGIN)

    line = rule(width=t.width + 1.0)
    line.next_to(group, DOWN, buff=0.5)

    scene.play(FadeIn(t, shift=UP * 0.3), run_time=0.7)
    if subtitle_text:
        scene.play(FadeIn(group[1], shift=UP * 0.2), Create(line), run_time=0.6)
    scene.wait(1.2)
    scene.play(FadeOut(group), FadeOut(line), run_time=0.5)

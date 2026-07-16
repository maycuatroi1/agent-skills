#!/usr/bin/env bash
# Dung moi truong Manim cho MOT thu muc video. Idempotent: chay lai nhieu lan vo hai.
#
#   ./setup.sh /duong/dan/toi/thu-muc-video
#
# Lo tron cac cai bay macOS. Doc references/macos-gotchas.md neu muon hieu tai sao.
set -euo pipefail

TARGET="${1:-$PWD}"
cd "$TARGET"

echo "==> 1/5  Cong cu he thong (brew)"
# dvisvgm   : Manim can de doi LaTeX -> SVG
# mupdf-tools: cung cap mutool; dvisvgm can no de doc PDF vi Ghostscript >= 10.01 bi tu choi
# ffmpeg    : ghep video, ffprobe do do dai canh
for pkg in dvisvgm mupdf-tools ffmpeg; do
  if brew list --formula "$pkg" >/dev/null 2>&1; then
    echo "    $pkg da co"
  else
    echo "    cai $pkg"; brew install "$pkg"
  fi
done

echo "==> 2/5  Font Inter (tieng Viet)"
# Helvetica Neue vo cum dau "uo" o weight bold. Inter phu kin tieng Viet moi weight.
if fc-list 2>/dev/null | grep -q "Inter"; then
  echo "    Inter da co"
else
  brew install --cask font-inter
fi

echo "==> 3/5  TeX day du"
# Can standalone.cls. Ban TeX toi gian o /usr/local KHONG co no.
if ! /opt/homebrew/bin/kpsewhich standalone.cls >/dev/null 2>&1; then
  echo "    !! Khong tim thay standalone.cls trong Homebrew texlive."
  echo "       Chay: brew install texlive"
  exit 1
fi
echo "    standalone.cls ok"

echo "==> 4/5  Python venv + Manim"
if [ ! -x .venv/bin/manim ]; then
  uv venv --python 3.12 .venv
  uv pip install --python .venv/bin/python manim
fi
.venv/bin/python -c "import manim; print('    manim', manim.__version__)"

echo "==> 5/5  Kiem tra pipeline LaTeX that su chay"
# Neu buoc nay qua, moi cai bay deu da duoc go.
cat > /tmp/_manim_smoke.py <<'EOF'
from manim import *
from theme import INK, MODEL, FONT_SANS
class Smoke(Scene):
    def construct(self):
        # tieng Viet co dau + LaTeX: hai thu hay vo nhat
        self.add(VGroup(
            Text("Thước đo bước học trước", font=FONT_SANS, weight=BOLD),
            MathTex(r"L=\frac{1}{n}\sum(\hat{y}_i-y_i)^2", color=MODEL),
        ).arrange(DOWN, buff=0.5))
EOF
cp /tmp/_manim_smoke.py ./_smoke.py
if .venv/bin/manim -ql -s --format=png _smoke.py Smoke >/dev/null 2>&1; then
  echo "    LaTeX + tieng Viet render OK"
  rm -rf _smoke.py media/images/_smoke
else
  echo "    !! Render that bai. Chay lai khong an output de xem loi:"
  echo "       .venv/bin/manim -ql -s --format=png _smoke.py Smoke"
  exit 1
fi

echo
echo "Xong. Buoc tiep: viet data.py roi scenes.py, sau do ./render.sh -ql"

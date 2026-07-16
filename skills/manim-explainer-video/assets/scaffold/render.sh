#!/usr/bin/env bash
# Render moi canh, ghep thanh video, roi sinh script + phu de vao final/.
# Danh sach canh doc tu manifest.py, khong hard-code o day.
#
#   ./render.sh          -> 1080p60 (giao hang)
#   ./render.sh -ql      -> 480p15  (vong lap sua nhanh, dung cai nay khi con dang lam)
set -euo pipefail

cd "$(dirname "$0")"

QUALITY="${1:--qh}"
case "$QUALITY" in
  -ql) DIR="480p15" ;;
  -qm) DIR="720p30" ;;
  -qh) DIR="1080p60" ;;
  -qk) DIR="2160p60" ;;
  *) echo "Chat luong khong hop le: $QUALITY (dung -ql/-qm/-qh/-qk)"; exit 1 ;;
esac

PY=.venv/bin/python
# mapfile can bash 4+, macOS ship bash 3.2 -> dung mang co dien
SCENES=()
while IFS= read -r line; do SCENES+=("$line"); done < <(
  $PY -c 'from manifest import SCENES; [print(s) for s, _ in SCENES]'
)
SLUG=$($PY -c 'from manifest import SLUG; print(SLUG)')
OUT="$SLUG.mp4"

for S in "${SCENES[@]}"; do
  echo ">> render $S"
  .venv/bin/manim "$QUALITY" scenes.py "$S"
done

echo ">> ghep $OUT"
LIST=$(mktemp)
for S in "${SCENES[@]}"; do
  echo "file '$PWD/media/videos/scenes/$DIR/$S.mp4'" >> "$LIST"
done
# stream copy: cac canh cung codec/fps nen khong can encode lai
ffmpeg -v error -f concat -safe 0 -i "$LIST" -c copy -y "$OUT"
rm -f "$LIST"

echo ">> sinh script + phu de"
$PY build_final.py "$DIR"

#!/usr/bin/env bash
# Symlink moi skill trong repo nay vao ~/.claude/skills/ de Claude Code thay duoc.
# Chay lai sau khi git pull tren may moi. Idempotent.
set -euo pipefail

REPO="$(cd "$(dirname "$0")" && pwd)"
DEST="$HOME/.claude/skills"
mkdir -p "$DEST"

for dir in "$REPO"/*/; do
  name="$(basename "$dir")"
  [ -f "$dir/SKILL.md" ] || continue

  link="$DEST/$name"
  if [ -L "$link" ]; then
    ln -sfn "$dir" "$link"
    echo "  cap nhat  $name"
  elif [ -e "$link" ]; then
    echo "  BO QUA    $name (da co thu muc that o $link, khong phai symlink)"
    continue
  else
    ln -s "$dir" "$link"
    echo "  lien ket  $name"
  fi
done

echo
echo "Xong. Mo lai Claude Code de nap skill moi."

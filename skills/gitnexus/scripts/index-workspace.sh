#!/usr/bin/env bash
set -euo pipefail

ROOT="${1:-$PWD}"
GROUP="${2:-}"
EMB=""
for a in "$@"; do
  [ "$a" = "--embeddings" ] && EMB="--embeddings"
done

if ! command -v gitnexus >/dev/null 2>&1; then
  echo "ERROR: gitnexus not installed. Run scripts/install.sh first." >&2
  exit 1
fi

ROOT="$(cd "$ROOT" && pwd)"
echo "Indexing git repos directly under: $ROOT"
[ -n "$EMB" ] && echo "(embeddings enabled)"

count=0
for d in "$ROOT"/*/; do
  d="${d%/}"
  [ -d "$d/.git" ] || continue
  name="$(basename "$d")"
  echo "==== analyze: $name ===="
  if ( cd "$d" && gitnexus analyze $EMB 2>&1 | grep -E "indexed successfully|nodes \||error|Error" ); then
    count=$((count+1))
  else
    echo "  skipped $name (analyze failed)"
  fi
done
echo "Indexed $count repo(s)."

if [ -n "$GROUP" ]; then
  echo "==== building group: $GROUP ===="
  gitnexus group create "$GROUP" >/dev/null 2>&1 || true
  gitnexus list | ROOT="$ROOT" GROUP="$GROUP" python3 - <<'PY'
import os, re, subprocess, sys
root = os.environ["ROOT"].rstrip("/") + "/"
group = os.environ["GROUP"]
text = sys.stdin.read()
name = None
added = 0
for line in text.splitlines():
    m = re.match(r"^\s{2}(\S.*)$", line)
    if m and "Path:" not in line and "Indexed:" not in line and "Commit:" not in line \
       and "Stats:" not in line and "Clusters:" not in line and "Processes:" not in line:
        name = m.group(1).strip()
        continue
    pm = re.match(r"^\s+Path:\s+(.*)$", line)
    if pm and name:
        path = pm.group(1).strip()
        if (path.rstrip("/") + "/").startswith(root):
            subprocess.run(["gitnexus", "group", "add", group, name, name],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            added += 1
        name = None
print(f"  added {added} repo(s) to group {group}")
PY
  gitnexus group sync "$GROUP"
  echo "Try: gitnexus group query $GROUP \"<question>\""
fi

#!/usr/bin/env bash
# Kiem tra truoc khi giao video. Chay TRONG thu muc video.
#
#   ./check.sh
#
# Bat 3 loi chet nguoi + 1 canh bao. Dung python3 chu khong dung grep vi BSD grep
# tren macOS khong hieu lop ky tu \x00-\x7F, se bao nham.
set -uo pipefail

if [ ! -f scenes.py ]; then
  echo "!! Chay script nay TRONG thu muc video (cho co scenes.py)."
  exit 1
fi

python3 - <<'PYEOF'
import ast
import pathlib
import re
import sys

fail = False


def report(ok, title, hits, fixhint):
    global fail
    print(f"==> {title}")
    if not hits:
        print("    ok")
        return
    for line, text in hits:
        print(f"    {line}: {text.strip()[:88]}")
    print(f"    X {fixhint}")
    fail = True


src = pathlib.Path("scenes.py")
lines = src.read_text(encoding="utf-8").splitlines()
tree = ast.parse(src.read_text(encoding="utf-8"))

# ---- 1. em-dash, quet moi file text kem theo (ke ca loi binh da sinh ra)
emdash = []
targets = ["scenes.py", "theme.py", "data.py", "manifest.py"]
targets += [str(p) for p in pathlib.Path("final").glob("*") if p.suffix in {".md", ".srt", ".tsv"}] \
    if pathlib.Path("final").is_dir() else []
for t in targets:
    p = pathlib.Path(t)
    if not p.exists():
        continue
    for i, ln in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
        if "—" in ln:
            emdash.append((f"{t}:{i}", ln))
report(True, "em-dash", emdash,
       "thay bang dau hai cham / dau phay / tach cau")

# ---- 2 & 3. soi cac loi goi MathTex/Tex bang AST (bo qua docstring va comment)
viet_trong_latex, mathtex_nhieu_chuoi = [], []
for node in ast.walk(tree):
    if not isinstance(node, ast.Call):
        continue
    fn = node.func
    name = fn.id if isinstance(fn, ast.Name) else getattr(fn, "attr", None)
    if name not in {"MathTex", "Tex"}:
        continue

    strs = [a for a in node.args if isinstance(a, ast.Constant) and isinstance(a.value, str)]
    raw = lines[node.lineno - 1]

    if any(not s.value.isascii() for s in strs):
        viet_trong_latex.append((f"scenes.py:{node.lineno}", raw))
    if len(strs) > 1:
        mathtex_nhieu_chuoi.append((f"scenes.py:{node.lineno}", raw))

report(True, "tieng Viet lot vao LaTeX", viet_trong_latex,
       "LaTeX chi duoc chua ASCII. Tach chu Viet ra Text() roi VGroup(...).arrange()")
report(True, "MathTex nhieu tham so", mathtex_nhieu_chuoi,
       "nhieu chuoi khong tach duoc submobject (pdflatex+mutool). Ghep nhieu MathTex roi arrange()")

# ---- canh bao (khong chan): mau hard-code
print("==> mau hard-code")
hard = [(f"scenes.py:{i}", ln) for i, ln in enumerate(lines, 1)
        if re.search(r'"#[0-9A-Fa-f]{6}"', ln)]
if hard:
    for line, text in hard:
        print(f"    {line}: {text.strip()[:88]}")
    print("    ! nen dat mau trong theme.py de doi mot cho, ca video doi theo")
else:
    print("    ok")

print()
if fail:
    print("Con loi o tren, sua truoc khi render ban giao hang.")
    sys.exit(1)
print("Sach. Chay ./render.sh de xuat ban cuoi.")
PYEOF

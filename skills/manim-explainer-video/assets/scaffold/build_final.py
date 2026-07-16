"""
Sinh script loi binh + phu de tu cac moc cue that trong video.
Tai dung nguyen ven cho moi video: danh sach canh doc tu manifest.py.

Nguon thoi gian:
  cues/<Scene>.json  : self.renderer.time tai moi self.cue(...) trong canh
  do dai .mp4 that   : ffprobe, dung lam offset giua cac canh

Nho vay doi timing animation thi timecode phu de tu doi theo, khong bao gio lech.

Xuat ra final/:
  <slug>.mp4        video
  script.md         kich ban co timecode, de long tieng
  subtitles.srt     phu de chuan
  narration.tsv     start<TAB>end<TAB>text, cho cong cu TTS doc may
"""

import json
import pathlib
import shutil
import subprocess
import sys

from manifest import SCENES, SLUG, TITLE

ROOT = pathlib.Path(__file__).parent
CUE_DIR = ROOT / "cues"
FINAL = ROOT / "final"
VIDEO = f"{SLUG}.mp4"

# Loi binh da thu am / TTS. Dat o goc thu muc thi build tu ghep vao video.
# File nay phai duoc sinh theo dung timecode trong final/narration.tsv.
NARRATION = ["narration.mp3", "narration.wav", "narration.m4a"]

# Toc do doc tieng Viet thoai mai: ~4.5 am tiet/giay. Vuot nguong -> canh bao.
SYLLABLES_PER_SEC = 4.5
MIN_SUB = 1.2      # phu de ngan nhat
MAX_SUB = 7.0      # dung de mot dong phu de treo qua lau


def probe_duration(path):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(path)],
        capture_output=True, text=True, check=True,
    )
    return float(out.stdout.strip())


def tc(seconds, sep=","):
    """00:01:23,450"""
    ms = int(round(seconds * 1000))
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d}{sep}{ms:03d}"


def collect(video_dir):
    """Gop cue cua moi canh thanh mot danh sach theo thoi gian toan video."""
    lines, offset = [], 0.0
    for scene, label in SCENES:
        cue_file = CUE_DIR / f"{scene}.json"
        mp4 = video_dir / f"{scene}.mp4"
        if not cue_file.exists():
            sys.exit(f"Thiếu {cue_file}. Render lại cảnh {scene} trước.")
        if not mp4.exists():
            sys.exit(f"Thiếu {mp4}. Render lại cảnh {scene} trước.")

        data = json.loads(cue_file.read_text(encoding="utf-8"))
        real = probe_duration(mp4)  # do dai that cua file, dung lam offset

        for cue in data["cues"]:
            lines.append({
                "scene": scene,
                "label": label,
                "start": offset + cue["t"],
                "text": cue["text"],
            })
        offset += real

    # ket thuc mot dong = luc dong ke tiep bat dau
    for i, ln in enumerate(lines):
        nxt = lines[i + 1]["start"] if i + 1 < len(lines) else offset
        span = nxt - ln["start"]
        ln["end"] = ln["start"] + max(MIN_SUB, min(span - 0.08, MAX_SUB))
        ln["window"] = span
    return lines, offset


def check_pace(lines):
    """Canh bao neu cau qua dai so voi khoang thoi gian danh cho no.

    Tieng Viet moi tu la mot am tiet, nen dem tu la du chinh xac.
    """
    warn = []
    for i, ln in enumerate(lines, 1):
        need = len(ln["text"].split()) / SYLLABLES_PER_SEC
        if need > ln["window"]:
            warn.append((i, ln["text"][:48], need, ln["window"]))
    return warn


def check_emdash(lines):
    return [(i, ln["text"]) for i, ln in enumerate(lines, 1) if "—" in ln["text"]]


def write_srt(lines):
    out = [f"{i}\n{tc(ln['start'])} --> {tc(ln['end'])}\n{ln['text']}\n"
           for i, ln in enumerate(lines, 1)]
    (FINAL / "subtitles.srt").write_text("\n".join(out), encoding="utf-8")


def write_tsv(lines):
    rows = ["start\tend\ttext"]
    rows += [f"{ln['start']:.3f}\t{ln['end']:.3f}\t{ln['text']}" for ln in lines]
    (FINAL / "narration.tsv").write_text("\n".join(rows) + "\n", encoding="utf-8")


def write_script(lines, total):
    n = len(lines)
    syl = sum(len(ln["text"].split()) for ln in lines)
    doc = [
        f"# Kịch bản lời bình: {TITLE}",
        "",
        f"Tổng thời lượng **{tc(total, '.')}** · {n} câu · khoảng {syl} âm tiết.",
        "",
        "Timecode lấy trực tiếp từ Manim (`self.renderer.time`) nên khớp đúng khung hình,",
        "không phải ước lượng. Dùng để lồng tiếng hoặc làm phụ đề.",
        "",
        "Cột **Vào** là lúc câu bắt đầu, khớp thời điểm animation tương ứng chạy.",
        "Cột **Khoảng** là quỹ thời gian tới câu kế tiếp: đọc gọn trong khoảng đó.",
        "",
    ]
    cur = None
    for i, ln in enumerate(lines, 1):
        if ln["label"] != cur:
            cur = ln["label"]
            doc += ["", f"## {cur}", "",
                    "| # | Vào | Khoảng | Lời bình |",
                    "|---|-----|--------|----------|"]
        doc.append(f"| {i} | `{tc(ln['start'], '.')}` | {ln['window']:.1f}s | {ln['text']} |")
    doc.append("")
    (FINAL / "script.md").write_text("\n".join(doc), encoding="utf-8")


def find_narration():
    for name in NARRATION:
        p = ROOT / name
        if p.exists():
            return p
    return None


def deliver(silent_master):
    """Xuat final/<video>. Co loi binh thi ghep vao, khong thi copy ban cam.

    Luon ghep tu ban CAM, khong ghep chong len ban da co tieng, nen chay lai
    build_final bao nhieu lan cung ra ket qua nhu nhau.
    """
    out = FINAL / VIDEO
    audio = find_narration()

    if audio is None:
        shutil.copy2(silent_master, out)
        print("  (chưa có narration.mp3, video xuất ra không có tiếng)")
        return

    subprocess.run(
        ["ffmpeg", "-v", "error",
         "-i", str(silent_master), "-i", str(audio),
         "-map", "0:v", "-map", "1:a",
         "-c:v", "copy",            # khong encode lai hinh
         "-c:a", "aac", "-b:a", "128k",
         "-af", "apad",             # tieng ngan hon hinh vai chuc ms -> chen im lang cho bang
         "-shortest",
         "-movflags", "+faststart",
         "-y", str(out)],
        check=True,
    )
    va, aa = probe_duration(silent_master), probe_duration(audio)
    print(f"  lồng tiếng: {audio.name}  ({aa:.1f}s tiếng / {va:.1f}s hình)")
    if abs(aa - va) > 2.0:
        print(f"  ! tiếng lệch hình {abs(aa - va):.1f}s. Kiểm tra TTS có bám timecode "
              f"trong narration.tsv không.")


def main():
    quality_dir = sys.argv[1] if len(sys.argv) > 1 else "1080p60"
    video_dir = ROOT / "media" / "videos" / "scenes" / quality_dir

    FINAL.mkdir(exist_ok=True)
    lines, total = collect(video_dir)

    write_srt(lines)
    write_tsv(lines)
    write_script(lines, total)

    # render.sh de ban cam o goc thu muc; do la master de ghep tieng.
    silent_master = ROOT / VIDEO
    if silent_master.exists():
        deliver(silent_master)
    else:
        print("  ! không thấy video câm ở gốc thư mục, bỏ qua bước xuất bản.")

    print(f"final/  {len(lines)} câu · {tc(total, '.')}")

    for i, text in check_emdash(lines):
        print(f"  X câu {i} còn em-dash, phải bỏ: \"{text[:50]}...\"")

    for i, text, need, have in check_pace(lines):
        print(f"  ! câu {i} có thể hơi dài: cần ~{need:.1f}s, chỉ có {have:.1f}s  \"{text}...\"")


if __name__ == "__main__":
    main()

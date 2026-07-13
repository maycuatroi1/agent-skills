#!/usr/bin/env bash
# Kiem tra file loi binh co bam dung timecode khong, TRUOC khi ghep vao video.
# Chay TRONG thu muc video, sau khi da co final/narration.tsv.
#
#   ./check-audio.sh narration.mp3
#
# Cach lam: do cac doan co tieng trong audio, so voi moc cue trong narration.tsv.
# TTS bam timecode -> moi cau khop trong ~0.3s. Khong bam -> lech dan va lech to.
set -uo pipefail

AUDIO="${1:-narration.mp3}"
[ -f "$AUDIO" ] || { echo "!! Khong thay $AUDIO"; exit 1; }
[ -f final/narration.tsv ] || { echo "!! Chua co final/narration.tsv. Chay ./render.sh truoc."; exit 1; }

# silencedetect bao silence_end tai luc am thanh vuot nguong, tre hon diem bat dau
# that khoang 0.2s. Do la san, khong phai loi.
ffmpeg -hide_banner -i "$AUDIO" -af silencedetect=noise=-35dB:d=0.35 -f null - 2>&1 \
  | grep -oE "silence_end: [0-9.]+" | awk '{print $2}' > /tmp/_onsets.txt

python3 - "$AUDIO" <<'PYEOF'
import csv, statistics, subprocess, sys

audio = sys.argv[1]
cues = [(i, float(r["start"]), r["text"])
        for i, r in enumerate(csv.DictReader(open("final/narration.tsv"), delimiter="\t"), 1)]
onsets = sorted(float(l) for l in open("/tmp/_onsets.txt") if l.strip())

if not onsets:
    print("!! Khong do duoc doan co tieng nao. File co im lang hoan toan khong?")
    sys.exit(1)


def dur(p):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                          "-of", "csv=p=0", p], capture_output=True, text=True)
    return float(out.stdout.strip())


deltas, bad = [], []
for i, c, txt in cues:
    o = min(onsets, key=lambda x: abs(x - c))
    d = abs(o - c)
    deltas.append(d)
    if d > 0.8:
        bad.append((i, c, o, txt))

print(f"độ dài tiếng : {dur(audio):.1f}s")
print(f"số câu       : {len(cues)}")
print(f"lệch trung vị: {statistics.median(deltas):.2f}s  (gồm độ trễ ~0.2s của phép đo)")
print(f"lệch lớn nhất: {max(deltas):.2f}s")
print()

if bad:
    print(f"{len(bad)}/{len(cues)} câu lệch quá 0.8s:")
    for i, c, o, txt in bad[:10]:
        print(f"  câu {i:>3}  kịch bản {c:>7.2f}s  tiếng {o:>7.2f}s   \"{txt[:44]}\"")
    print()
    print("Vài câu lệch ở ĐẦU video thường vô hại (TTS chèn khoảng lặng dẫn).")
    print("Lệch NHIỀU câu và tăng dần nghĩa là TTS nối liền không bám timecode:")
    print("cần sinh lại từ final/narration.tsv hoặc final/subtitles.srt.")
else:
    print("Mọi câu đều bám timecode. Đặt file vào gốc thư mục tên narration.mp3")
    print("rồi chay ./render.sh (hoac python build_final.py) de ghep vao video.")
PYEOF

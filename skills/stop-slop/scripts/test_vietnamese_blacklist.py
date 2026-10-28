"""Exercise the ERE blacklist with grep, the documented consumer."""
from pathlib import Path
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
BLACKLIST = (ROOT / "references/blacklist-vi.txt").read_text()
PATTERNS = [s for s in BLACKLIST.splitlines()
            if s.strip() and not s.lstrip().startswith("#")]
SECTION = BLACKLIST.split('# --- Khuôn bao quát "Từ X tới/đến Y" ---', 1)[1].split("\n# ---", 1)[0]
PATTERN = next(s for s in SECTION.splitlines() if s.strip() and not s.startswith("#"))

def matches(pattern, text):
    result = subprocess.run(["grep", "-i", "-E", "-e", pattern], input=text + "\n",
                            capture_output=True, text=True)
    if result.returncode not in (0, 1):
        raise AssertionError(result.stderr)
    return result.returncode == 0

class VietnameseBlacklist(unittest.TestCase):
    def test_all_patterns_compile(self):
        for pattern in PATTERNS:
            with self.subTest(pattern=pattern):
                matches(pattern, "")

    def test_template_variants_are_review_candidates(self):
        for text in ["Từ response HTTP tới claim về quyền truy cập",
                     "## PentestGPT: từ task tree đến vòng lặp thực thi",
                     "TỪ Ý TƯỞNG SANG THỰC TIỄN",
                     "Caption: từ dữ liệu đến quyết định"]:
            with self.subTest(text=text):
                self.assertTrue(matches(PATTERN, text))

    def test_literal_uses_are_candidates_not_automatic_edits(self):
        for text in ["Khoảng từ 10 đến 20 ms", "Gói tin đi từ client tới server",
                     "Chuyển dữ liệu từ CSV sang Parquet"]:
            with self.subTest(text=text):
                self.assertTrue(matches(PATTERN, text))

    def test_no_cross_sentence_or_substring_matches(self):
        for text in ["HTTP 200 nhưng chắc gì đã vào được",
                     "Đọc output từ tool. Đến bước sau, kiểm tra quyền.",
                     "Đọc output từ tool; tới bước sau mới kiểm tra.",
                     "prefix_từ A đến B"]:
            with self.subTest(text=text):
                self.assertFalse(matches(PATTERN, text))

def group(header):
    """Patterns of the blacklist group whose header line starts with `# --- header`."""
    lines = BLACKLIST.splitlines()
    start = next(i for i, line in enumerate(lines) if line.startswith("# --- " + header))
    out = []
    for line in lines[start + 1:]:
        if line.startswith("# ---"):
            break
        if line.strip() and not line.lstrip().startswith("#"):
            out.append(line)
    return out


# Each group: sentences an author flagged (must hit) and close neighbours that read fine (must not).
GROUP_CASES = {
    "Nhãn nói điều hiển nhiên": (
        ["Video: The PagerDuty Platform Overview, 99 giây",
         "Video: What is PagerDuty Process Automation?, 142 giây",
         "Video trên trang AIOps (YouTube, cần mạng)"],
        ["Video Paige điều tra một incident",
         "Request timeout sau 30 giây, client retry.",
         "Video YouTube, cần mạng khi trình chiếu."]),
    "Binary contrast dịch sát": (
        ["Đây không phải lỗi của compiler, mà là lỗi của người viết.",
         "không phải là thiếu GPU. Đó là thiếu dữ liệu sạch.",
         "Nó không chỉ chậm hơn mà còn tốn RAM hơn."],
        ["Server không phản hồi trong 5 giây.",
         "Mô hình không hội tụ, nên tôi giảm learning rate.",
         "Không có W thì tính thế nào"]),
    "Tem kiểm định": (
        ["Trạng thái ghi nhận ngày 18/10/2026",
         "Trạng thái đối chiếu code trên origin/main, kiểm ngày 2026-09-27."],
        ["Bài đăng ngày 18/10/2026.", "Giá tháng 10/2026 là 15 USD."]),
    "Tự khẳng định đã làm": (
        ["SPEAR full paper đã đọc 9 trang", "Tôi đã kiểm lại hai lần."],
        ["Paper dài 9 trang."]),
    "Lộ prompt": (
        ["Nguồn sơ đồ: QACI-Offensive-Agent-v3", "Phạm vi: phòng lab / eval được cấp phép", "Bản draft"],
        ["Phạm vi của bài là Linux."]),
    "Tên file, công cụ làm bài": (
        ["Source: osi-position.drawio", "Hình vẽ bằng matplotlib"],
        ["Tôi dùng matplotlib để vẽ hình phân phối."]),
    "Username, chi tiết hậu trường": (
        ["Trong thread trên r/LocalLLaMA, tiensss yêu cầu", "theo u/tiensss",
         "Ban đầu đề cương thế này, nhưng cuối cùng thế này"],
        ["Nhiều người dùng trên r/LocalLLaMA yêu cầu", "Ban đầu tôi dùng SGD."]),
    "Giả cụ thể": (
        ["mình ngồi debug lúc 11 giờ đêm", "cho tới tối thứ sáu năm ngoái", "hôm thứ ba tuần trước"],
        ["Cron chạy lúc 2 giờ mỗi ngày.", "Job chạy mỗi 2 giờ."]),
    "Tính từ tự chứng nhận": (
        ["So sánh công bằng", "phân tích khách quan"],
        ["So sánh hai cách lưu cây"]),
    "Giọng biên bản và vế đuôi giải thích": (
        ["HTTP 200 chưa chứng minh quyền truy cập", "Accuracy cao không đồng nghĩa với model tốt",
         "Latency giảm 30%, cho thấy cache đã có tác dụng."],
        ["HTTP 200 nhưng chắc gì đã vào được"]),
    "Chỉ tay vào hình": (
        ["Đọc đường dữ liệu trên Figure 2", "nhìn cột thứ ba trong bảng 1"],
        ["Đường latency gãy ở 64 KB."]),
    "Kết bài theo khuôn": (
        ["mình muốn được cãi lại", "Nếu bạn đọc tới đây, cảm ơn bạn. Thật.", "Rồi mình tắt máy, đi pha trà."],
        ["Cảm ơn thầy Sơn đã dẫn đường cho đám nhỏ."]),
    "Heading và title": (
        ["## Tầng 0, hiện trạng: một hoá đơn bằng giờ người",
         "x^x = 49 trong bài Medium 1.4K clap"],
        ["## Chi phí vận hành hiện tại", "## Không có W thì tính thế nào",
         "## Con số 98% đang đo cái gì?"]),
}


class NewGroups(unittest.TestCase):
    def test_flagged_sentences_hit_their_group(self):
        for header, (positives, _) in GROUP_CASES.items():
            patterns = group(header)
            self.assertTrue(patterns, header)
            for text in positives:
                with self.subTest(group=header, text=text):
                    self.assertTrue(any(matches(p, text) for p in patterns))

    def test_neighbours_stay_quiet(self):
        for header, (_, negatives) in GROUP_CASES.items():
            patterns = group(header)
            for text in negatives:
                with self.subTest(group=header, text=text):
                    self.assertFalse(any(matches(p, text) for p in patterns))


if __name__ == "__main__":
    unittest.main()

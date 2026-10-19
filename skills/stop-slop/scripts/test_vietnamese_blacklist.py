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

if __name__ == "__main__":
    unittest.main()

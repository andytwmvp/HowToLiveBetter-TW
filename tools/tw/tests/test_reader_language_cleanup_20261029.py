"""台灣閱讀入口及正文不顯示內部編修紀錄。"""
import hashlib
import json
from pathlib import Path
import re
import sys
import unittest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools/tw"))
from retroactive_audit import validate_reader_copy_cleanup_history, validate_recheck_history


class ReaderLanguageCleanupTests(unittest.TestCase):
    def read(self, path):
        return (ROOT / path).read_text(encoding="utf-8")

    def test_recent_article_cleanup_matches_runtime_and_keeps_review_history(self):
        runtime = json.loads(self.read("localization/tw-edition/runtime.json"))
        register = json.loads(self.read("localization/retroactive-review-register-20261019.json"))
        items = {item["id"]: item for item in runtime["items"]}
        substantive = {row["id"]: row for row in register["substantive_rechecks"]}
        for item_id in ("TW-01-015", "TW-16-005", "TW-16-011", "TW-17-011", "TW-24-014", "TW-24-006", "TW-13-042"):
            item = items[item_id]
            body_sha = hashlib.sha256(item["body"].encode("utf-8")).hexdigest()
            with self.subTest(item_id=item_id):
                markdown = self.read(item["target_path"])
                self.assertEqual(markdown, item["body"])
                self.assertNotIn("逐來源實讀範圍", item["body"])
                self.assertNotIn("前後SHA", item["body"])
                self.assertNotIn("本篇核對現行法", item["body"])
                self.assertNotIn("尚未經醫療、社工、法律及急救專業人員獨立審閱", item["body"])
                matches = [row for row in register["reader_copy_cleanups"]
                           if row.get("id") == item_id and row.get("after_sha256") == body_sha]
                self.assertEqual(len(matches), 1)
                self.assertEqual(matches[0]["transform"], "reader_copy_cleanup_v3")
                validate_reader_copy_cleanup_history(ROOT, matches[0], item)
                if item_id in substantive:
                    validate_recheck_history(ROOT, substantive[item_id], item)

    def test_entry_points_use_reader_language_without_batch_status(self):
        paths = ("README.md", "REPOSITORY_GUIDE.md", "locales/zh-TW/README.md")
        for path in paths:
            text = self.read(path)
            with self.subTest(path=path):
                self.assertNotIn("tw-bootstrap-v1", text)
                self.assertNotRegex(text, r"本批證據|累計\d+篇|PR #\d+|CI 成功|下方為原作")
        self.assertIn("台灣生活中的實際做法", self.read("README.md"))
        self.assertIn("在電腦上開啟台灣生活指南", self.read("REPOSITORY_GUIDE.md"))
        review = json.loads(self.read("localization/reviews/TW-13-042.json"))
        self.assertIn("AI輔助", review["reviewer"])

    def test_source_preview_interface_uses_taiwan_phrasing(self):
        text = self.read("source.html")
        self.assertIn("正在載入內容…", text)
        self.assertNotIn("正在讀取正文", text)
        for phrase in ("搜索條目", "打開篩選", "薈萃/RCT", "高效益人生指南",
                       "不代表臺灣現行生活建議", "原作正文與標籤來自"):
            with self.subTest(phrase=phrase):
                self.assertNotIn(phrase, text)
        for phrase in ("搜尋原作內容", "開啟篩選", "原作成本效益", "家有長輩",
                       "要找台灣生活中的實際做法", "台灣文章目錄"):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)
        self.assertIn('目前顯示 <b id="cnt">–</b> 則，共 <span id="tot">–</span> 則', text)
        self.assertIn("本指南依臺灣生活情境整理", json.loads(
            self.read("localization/tw-edition/runtime.json"))["scope"])


if __name__ == "__main__":
    unittest.main()

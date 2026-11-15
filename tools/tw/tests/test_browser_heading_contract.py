"""Reader heading parity follows official runtime content rather than fixed counts."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from browser_heading_contract import heading_map_issues, runtime_heading_map


class BrowserHeadingContractTests(unittest.TestCase):
    def test_runtime_and_reader_may_grow_together_without_test_edits(self):
        item = {
            "id": "TW-99-001",
            "title": "測試指引",
            "target_path": "locales/zh-TW/book/ch99/TW-99-001.md",
            "body": (
                "# 測試指引\n\n"
                "## 先確認安全\n\n先離開危險現場。\n\n"
                "## 新增的台灣情境\n\n說明讀者可採取的做法。\n\n"
                "## 參考資料\n\n來源。\n"
            ),
        }

        expected = runtime_heading_map([item])
        rendered = {"TW-99-001": ["先確認安全", "新增的台灣情境", "參考資料"]}

        self.assertEqual(heading_map_issues(expected, rendered), [])

    def test_missing_or_reordered_runtime_heading_fails(self):
        item = {
            "id": "TW-99-002",
            "title": "測試指引",
            "target_path": "locales/zh-TW/book/ch99/TW-99-002.md",
            "body": "# 測試指引\n\n## 必要步驟\n\n內容。\n\n## 參考資料\n\n來源。\n",
        }
        expected = runtime_heading_map([item])

        missing = heading_map_issues(expected, {"TW-99-002": ["參考資料"]})
        reordered = heading_map_issues(
            expected, {"TW-99-002": ["參考資料", "必要步驟"]}
        )

        self.assertTrue(any("小標或順序與runtime不一致" in issue for issue in missing))
        self.assertTrue(any("小標或順序與runtime不一致" in issue for issue in reordered))

    def test_missing_and_unexpected_articles_fail(self):
        issues = heading_map_issues(
            {"TW-99-003": ["參考資料"]},
            {"TW-99-004": ["其他文章"]},
        )

        self.assertEqual(
            issues,
            [
                "TW-99-003: runtime文章未顯示",
                "TW-99-004: 閱讀出口出現非runtime文章",
            ],
        )


if __name__ == "__main__":
    unittest.main()

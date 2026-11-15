"""Generic rendered-body integrity, distinct from per-topic content requirements."""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from body_structure_test_support import body_structure_issues
from review_contract import ROOT, validate_runtime


REQUIRED_HEADINGS = {
    "TW-01-020": ("流行現況與數據限制",),
    "TW-02-047": ("生淡水魚與中華肝吸蟲：特定暴露，不是所有生魚片",),
    "TW-07-014": ("臺灣的求職統計", "臺灣求職資源"),
    "TW-13-004": ("台灣發生頻率資料的限制",),
    "TW-13-005": ("台灣發生頻率資料的限制",),
    "TW-13-008": ("台灣的已診斷發生率與限制",),
    "TW-13-010": ("台灣研究資料與限制",),
    "TW-13-027": ("旅外沙漠或偏遠道路的提醒",),
    "TW-13-031": ("遇見台灣黑熊", "遇見野豬", "遇見犬隻或犬群"),
    "TW-13-036": ("台灣案件統計能說明什麼", "脫身與報案"),
    "TW-13-037": (
        "發生頻率與統計限制",
        "目擊時怎麼做",
        "目擊者心理支持與法律界線",
    ),
    "TW-13-048": (
        "恆牙的現場處理",
        "乳牙或不確定牙齒種類",
        "台灣牙科急診與費用",
    ),
    "TW-15-011": ("預售屋賣方洽辦貸款的差額規則",),
    "TW-15-013": ("臺灣預售契約的時程與遲延處理",),
    "TW-19-009": ("離開特定有害作業後的追蹤健檢",),
    "TW-23-010": ("把技能放回實際工作裡評估", "查臺灣的職訓課程"),
    "TW-26-003": ("經營影音服務另看許可範圍",),
    "TW-NAV-010": (
        "第一步：把「在家維持生活」和「帶包離開」分開",
        "第二步：用一次採買清單與固定複查減少成本",
        "第三步：建立不同危機的決策分流",
        "第四步：先照顧需要特別安排的人與離線資訊",
        "第五步：留出身心支持與變動時效的空間",
        "延伸資料",
    ),
}


class BodyStructureContractTests(unittest.TestCase):
    def test_every_published_body_has_complete_rendered_sections_and_registered_sources(self):
        runtime = validate_runtime()
        known_source_ids = {source["id"] for source in runtime["sources"]}
        for item in runtime["items"]:
            if not item.get("target_path"):
                continue
            with self.subTest(id=item["id"]):
                errors = body_structure_issues(
                    item,
                    known_source_ids=known_source_ids,
                    required_headings=REQUIRED_HEADINGS.get(item["id"], ()),
                )
                self.assertEqual(errors, [], item["id"])

    def test_a_valid_additional_section_keeps_required_sections_valid(self):
        item = {
            "id": "TW-99-001",
            "title": "測試指引",
            "target_path": "locales/zh-TW/book/ch99/TW-99-001.md",
            "source_ids": ["source-a"],
            "body": (
                "# 測試指引\n\n<!-- TW-ID: TW-99-001 -->\n\n"
                "## 必要的第一步\n\n先確認現場安全。\n\n"
                "## 新增的在地情境\n\n補充適用情況。\n\n"
                "## 參考資料\n\n[主管機關](https://example.gov.tw/guide)\n"
            ),
        }
        self.assertEqual(
            body_structure_issues(
                item,
                known_source_ids={"source-a"},
                required_headings=("必要的第一步",),
            ),
            [],
        )

    def test_missing_required_section_and_unknown_source_are_reported(self):
        item = {
            "id": "TW-99-002",
            "title": "測試指引",
            "target_path": "locales/zh-TW/book/ch99/TW-99-002.md",
            "source_ids": ["missing-source"],
            "body": (
                "# 測試指引\n\n<!-- TW-ID: TW-99-002 -->\n\n"
                "## 參考資料\n\n[主管機關](https://example.gov.tw/guide)\n"
            ),
        }
        errors = body_structure_issues(
            item,
            known_source_ids={"registered-source"},
            required_headings=("必要的第一步",),
        )
        self.assertTrue(any("缺少必要段落標題" in error for error in errors))
        self.assertTrue(any("來源登錄缺少 ID" in error for error in errors))

    def test_empty_section_is_rejected(self):
        item = {
            "id": "TW-99-003",
            "title": "測試指引",
            "target_path": "locales/zh-TW/book/ch99/TW-99-003.md",
            "body": (
                "# 測試指引\n\n<!-- TW-ID: TW-99-003 -->\n\n"
                "## 必要的第一步\n\n## 參考資料\n\n來源說明。\n"
            ),
        }
        self.assertTrue(
            any("沒有正文內容" in error for error in body_structure_issues(item))
        )


if __name__ == "__main__":
    unittest.main()

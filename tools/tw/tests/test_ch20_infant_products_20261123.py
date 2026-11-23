"""第20章嬰幼兒用品首次發布契約。"""
import hashlib
import json
import re
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools/tw"))
from ci_language_policy import audit_drafts
from review_contract import publication_report, validate_runtime
from source_bundle_test_support import source_bundle_ids_added_since

BASE = "f17c744aa6d3474e1f086eab4a2642614522954c"
DATE = "2026-11-23"
DUE = "2027-02-23"
BUNDLE = "localization/tw-edition/sources/ch20-infant-products-20261123.json"
STAGE = "localization/ch20-infant-products-20261123.json"
REGISTER = "localization/retroactive-review-register-20261019.json"
ARTICLES = {
    "TW-20-010": {
        "title": "尿布依寶寶體型選合適尺寸，便後儘快更換並留意皮膚",
        "path": "locales/zh-TW/book/ch20/TW-20-010.md",
        "sources": ["tw20_bsmi_diaper_sample_2026", "tw20_hpa_diaper_bowel_care", "tw20_vghtpe_diaper_care_2026"],
    },
    "TW-20-011": {
        "title": "大型嬰兒用品先列需求，再借用或買二手；安全資料不明就別用",
        "path": "locales/zh-TW/book/ch20/TW-20-011.md",
        "sources": ["tw20_bsmi_infant_crib_selection_2025", "tw20_bsmi_infant_crib_rules_2024", "tw20_bsmi_child_seat_safety_2025", "tw20_bsmi_child_product_recalls"],
    },
    "TW-20-015": {
        "title": "不用帶輪學步車教嬰兒走路，改在安全地面活動並看顧",
        "path": "locales/zh-TW/book/ch20/TW-20-015.md",
        "sources": ["tw20_hpa_infant_home_safety", "tw20_bsmi_walker_rules_2025"],
    },
}
NEW_SOURCES = {source for row in ARTICLES.values() for source in row["sources"]}


def read(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def git_bytes(revision, path):
    result = subprocess.run(["git", "show", f"{revision}:{path}"], cwd=ROOT, capture_output=True)
    return result.stdout if result.returncode == 0 else None


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


class Chapter20InfantProductsPublicationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.runtime = validate_runtime()
        cls.items = {row["id"]: row for row in cls.runtime["items"]}
        cls.sources = {row["id"]: row for row in cls.runtime["sources"]}
        cls.manifest = {row["id"]: row for row in read("localization/manifest.json")["entries"]}
        cls.reviews = {key: read(f"localization/reviews/{key}.json") for key in ARTICLES}
        cls.bodies = {key: (ROOT / spec["path"]).read_text(encoding="utf-8") for key, spec in ARTICLES.items()}
        cls.bundle = read(BUNDLE)
        cls.stage = read(STAGE)
        cls.register = read(REGISTER)
        cls.base_register = json.loads(git_bytes(BASE, REGISTER))
        cls.base_runtime = json.loads(git_bytes(BASE, "localization/tw-edition/runtime.json"))
        cls.base_coverage = json.loads(git_bytes(BASE, "localization/tw-edition/coverage.json"))

    def test_first_publication_preserves_fixed_ids_and_history(self):
        self.assertEqual(self.stage["baseline_main_sha"], BASE)
        baseline = {row["id"]: row for row in json.loads(git_bytes(BASE, "localization/manifest.json"))["entries"]}
        for key, spec in ARTICLES.items():
            old = baseline[key]
            self.assertEqual((old["status"], old["target_path"], old["sources"]), ("pending", None, []))
            self.assertIsNone(git_bytes(BASE, spec["path"]))
            current = self.manifest[key]
            self.assertEqual((current["status"], current["treatment"], current["verified_at"]), ("verified", "taiwan_independent_rewrite", DATE))
            self.assertEqual((current["upstream_commit"], current["upstream_text_sha256"]), (old["upstream_commit"], old["upstream_text_sha256"]))
            self.assertEqual((current["target_path"], current["sources"]), (spec["path"], spec["sources"]))
        for key, baseline_value in self.base_register.items():
            if key == "substantive_rechecks":
                self.assertEqual(
                    self.register[key][:len(baseline_value)], baseline_value,
                    "首次發布不可改寫或刪除既有實質再審歷史",
                )
            else:
                self.assertEqual(self.register[key], baseline_value, f"首次發布不應改動歷史登錄欄位：{key}")
        base_ids = [row["id"] for row in self.base_runtime["items"]]
        current_ids = [row["id"] for row in self.runtime["items"]]
        self.assertEqual([key for key in current_ids if key in set(base_ids)], base_ids)
        self.assertTrue(set(ARTICLES).issubset(set(current_ids)))

    def test_reader_runtime_sources_review_and_sha_match(self):
        chapter = (ROOT / "locales/zh-TW/book/ch20/README.md").read_text(encoding="utf-8")
        chapter_ids = [int(n) for n in re.findall(r"TW-20-(\d{3})\.md", chapter)]
        runtime_ids = sorted(
            int(item["id"].rsplit("-", 1)[1])
            for item in self.runtime["items"]
            if item["id"].startswith("TW-20-") and item.get("target_path", "").startswith("locales/zh-TW/book/ch20/")
        )
        self.assertEqual(chapter_ids, runtime_ids)
        for key, spec in ARTICLES.items():
            with self.subTest(id=key):
                body = self.bodies[key]
                digest = sha(body.encode("utf-8"))
                item, entry, review = self.items[key], self.manifest[key], self.reviews[key]
                self.assertEqual((item["body"], item["target_path"], item["title"]), (body, spec["path"], spec["title"]))
                self.assertEqual((item["source_ids"], item["review_status"]), (spec["sources"], "source_checked"))
                self.assertEqual((item["reviewed_at"], item["review_due_at"]), (DATE, DUE))
                self.assertEqual((review["target_sha256"], review["source_reviewed_sha256"], review["after_sha256"]), (digest, digest, digest))
                self.assertIsNone(review["before_sha256"])
                self.assertEqual(review["source_bundle_path"], BUNDLE)
                self.assertEqual(review["source_bundle_sha256"], sha((ROOT / BUNDLE).read_bytes()))
                self.assertEqual(review["source_ids"], spec["sources"])
                self.assertTrue(review["professional_review"]["required"])
                self.assertFalse(review["professional_review"]["obtained"])
                self.assertTrue(review["professional_review"]["scope"])
                self.assertTrue(review["unresolved_questions"])
                self.assertEqual({row["source_id"] for row in review["source_checks"]}, set(spec["sources"]))
                linked_urls = set(re.findall(r"\]\((https://[^)]+)\)", body))
                self.assertEqual(linked_urls, {self.sources[sid]["url"] for sid in spec["sources"]})
                self.assertNotRegex(body, r"(批次摘要|AI協助|本次.{0,12}(?:審查|再審|核對)|CI\s*(?:成功|通過)|PR\s*#\d+|待專業審閱|fork管理|原作固定ID|本輪|本批)")
                self.assertNotRegex(body, r"(繁體字形轉換稿|臺灣改寫與來源重核|內部審閱|管理說明)")

    def test_frequency_and_taiwan_context_are_explicit(self):
        diapers = self.bodies["TW-20-010"]
        self.assertIn("20款", diapers)
        self.assertIn("1款中文標示不符合", diapers)
        self.assertIn("不是尿布疹病例統計", diapers)
        self.assertIn("不是標檢局公告應施檢驗品目", diapers)
        self.assertNotIn("2小時", diapers)
        stats = self.reviews["TW-20-010"]["statistics_assessed"]
        self.assertEqual([(row["numerator"], row["denominator"]) for row in stats], [(20, 20), (1, 20)])
        for row in stats:
            self.assertIn("市購", row["data_type"])
            self.assertTrue(row["limitations"])
            self.assertIn("全市場", " ".join(row["limitations"]))
        self.assertIn("三天", diapers)

        equipment = self.bodies["TW-20-011"]
        self.assertIn("碰撞史不明", equipment)
        self.assertIn("即使外觀看不出損傷也不要繼續使用", equipment)
        self.assertIn("符合現行安全要求", equipment)
        self.assertIn("商品召回訊息", equipment)
        self.assertEqual(self.reviews["TW-20-011"]["statistics_assessed"], [])

        walker = self.bodies["TW-20-015"]
        self.assertIn("這不是台灣事故統計", walker)
        self.assertIn("2025-01-17", self.reviews["TW-20-015"]["legal_date_assessment"]["assessment"])
        self.assertIn("本文是安全建議，不把學步車描述成法律全面禁用的用品", walker)
        self.assertEqual(self.reviews["TW-20-015"]["statistics_assessed"], [])

    def test_sources_coverage_and_first_publication_scope(self):
        self.assertEqual(self.bundle["checked_at"], DATE)
        self.assertEqual({row[0] for row in self.bundle["sources"]}, NEW_SOURCES)
        self.assertEqual(len(self.bundle["sources"]), len(NEW_SOURCES))
        self.assertTrue(NEW_SOURCES.issubset(source_bundle_ids_added_since(ROOT, BASE)))
        coverage = read("localization/tw-edition/coverage.json")
        self.assertEqual(coverage, audit_drafts())
        self.assertFalse(coverage["publication_ready"])
        publication = publication_report(ROOT)
        self.assertEqual(publication["publication_completed_entries"], 351)
        self.assertFalse(publication["publication_ready"])
        self.assertEqual(self.stage["counts_before"]["publication_completed_entries"], self.base_coverage["publication_completed_entries"])
        self.assertEqual(self.stage["counts_after"]["publication_completed_entries"], publication["publication_completed_entries"])
        self.assertEqual(self.stage["counts_before"]["runtime_items"], len(self.base_runtime["items"]))
        self.assertEqual(self.stage["counts_after"]["runtime_items"], len(self.runtime["items"]))
        self.assertEqual(self.stage["counts_before"]["substantive_rechecks"], self.stage["counts_after"]["substantive_rechecks"])
        self.assertEqual(self.stage["work_type"], "first_formal_publication_not_historical_substantive_re_review")


if __name__ == "__main__":
    unittest.main()

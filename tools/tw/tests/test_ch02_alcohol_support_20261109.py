"""第2章減酒求助正文、來源、補助規則與歷史草稿追蹤契約。"""
import hashlib
import json
import re
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ci_language_policy import audit_drafts
from review_contract import ROOT, validate_runtime

BASE = "592f56f73d7b7cc440b53bb3e6c6c80d471783e0"
DATE = "2026-11-09"
DUE = "2027-02-09"
ARTICLE_PATH = "locales/zh-TW/book/ch02/TW-02-021.md"
SOURCE_PATH = "localization/tw-edition/sources/ch02-alcohol-support-20261109.json"
BATCH_PATH = "localization/ch02-alcohol-support-20261109.json"
SOURCE_IDS = {
    "tw02_mohw_alcohol_center_20261109",
    "tw02_mohw_alcohol_plan_115_20261109",
    "tw02_mohw_alcohol_plan_116_20261109",
    "tw02_springer_audit_2018_2026",
}


def read_json(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def json_at(revision, path):
    raw = subprocess.check_output(
        ["git", "show", f"{revision}:{path}"], cwd=ROOT, text=True
    )
    return json.loads(raw)


class ChapterTwoAlcoholSupportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.runtime = validate_runtime()
        cls.items = {item["id"]: item for item in cls.runtime["items"]}
        cls.sources = {source["id"]: source for source in cls.runtime["sources"]}
        cls.manifest = {
            entry["id"]: entry for entry in read_json("localization/manifest.json")["entries"]
        }
        cls.review = read_json("localization/reviews/TW-02-021.json")
        cls.batch = read_json(BATCH_PATH)
        cls.source_bundle = read_json(SOURCE_PATH)
        cls.coverage = read_json("localization/tw-edition/coverage.json")
        cls.body = (ROOT / ARTICLE_PATH).read_text(encoding="utf-8")

    def test_first_formal_publication_matches_manifest_runtime_review_and_hashes(self):
        item = self.items["TW-02-021"]
        entry = self.manifest["TW-02-021"]
        digest = hashlib.sha256((ROOT / ARTICLE_PATH).read_bytes()).hexdigest()

        self.assertEqual(self.batch["baseline_main_sha"], BASE)
        self.assertEqual(self.batch["reviewed_at"], DATE)
        self.assertEqual(self.batch["review_due_at"], DUE)
        self.assertEqual(entry["status"], "verified")
        self.assertEqual(entry["verified_at"], DATE)
        self.assertEqual(entry["target_path"], ARTICLE_PATH)
        self.assertEqual(entry["sources"], item["source_ids"])
        self.assertEqual(item["body"], self.body)
        self.assertEqual(item["review_status"], "source_checked")
        self.assertEqual(item["reviewed_at"], DATE)
        self.assertEqual(item["review_due_at"], DUE)
        self.assertEqual(self.review["target_sha256"], digest)
        self.assertEqual(self.review["source_reviewed_sha256"], digest)
        self.assertIsNone(self.review["before_sha256"])
        self.assertEqual(self.review["after_sha256"], digest)
        self.assertEqual(self.batch["items"][0]["after_sha256"], digest)
        self.assertEqual(self.review["source_ids"], item["source_ids"])
        self.assertEqual(self.batch["items"][0]["source_ids"], item["source_ids"])

    def test_all_sources_are_registered_and_support_the_reader_links(self):
        item = self.items["TW-02-021"]
        review_checks = self.review["source_checks"]
        source_urls = {self.sources[source_id]["url"] for source_id in item["source_ids"]}
        body_urls = set(re.findall(r"\]\((https?://[^)]+)\)", self.body))

        self.assertEqual(set(item["source_ids"]), SOURCE_IDS)
        self.assertEqual({row[0] for row in self.source_bundle["sources"]}, SOURCE_IDS)
        self.assertEqual({check["source_id"] for check in review_checks}, SOURCE_IDS)
        self.assertEqual({check["url"] for check in review_checks}, source_urls)
        self.assertEqual(body_urls, source_urls)
        for source_id in item["source_ids"]:
            self.assertTrue(self.sources[source_id]["supports"])
            self.assertTrue(self.sources[source_id]["accessed_at"])

    def test_reader_copy_gives_safe_actions_cost_limits_and_taiwan_statistics(self):
        self.assertIn("不要為了完成飲酒紀錄而延後求助", self.body)
        self.assertIn("立即撥119", self.body)
        self.assertIn("0800-255959", self.body)
        self.assertIn("2026年1月1日至12月31日", self.body)
        self.assertIn("2027年1月1日至12月31日", self.body)
        self.assertIn("每人每年累計補助上限新臺幣4萬元", self.body)
        self.assertIn("採部分補助", self.body)
        self.assertIn("15,028名18至64歲成人", self.body)
        self.assertIn("6.21%", self.body)
        self.assertIn("篩檢分類，不是醫師診斷", self.body)
        self.assertIn("論文摘要未列加權分子與加權母數", self.body)
        self.assertNotIn("談幾分鐘", self.body)
        self.assertNotIn("每週少喝20克純酒精", self.body)
        self.assertNotIn("每治療12人", self.body)
        self.assertNotRegex(
            self.body,
            r"(批次摘要|本次.{0,12}(?:AI|審查|再審|核對)|CI\s*(?:成功|通過)|PR\s*#\d+|專業審閱仍待|fork管理)",
        )

    def test_statistics_and_professional_review_limits_are_recorded(self):
        statistic = self.review["statistics_assessed"][0]
        self.assertEqual(statistic["value"], "加權盛行率6.21%")
        self.assertEqual(statistic["period"].split("；")[0], "調查資料為2018年")
        self.assertIn("15,028", statistic["population"])
        self.assertIn("未報告", statistic["numerator"])
        self.assertIn("不能換算個人發病機率", statistic["limitations"])
        self.assertEqual(self.review["professional_review"]["required"], True)
        self.assertEqual(self.review["professional_review"]["obtained"], False)
        self.assertEqual(self.batch["professional_review"], self.review["professional_review"])

    def test_historical_draft_and_its_append_only_review_are_unchanged(self):
        review_path = "localization/reviews/drafts/TW-02-021.json"
        register_path = "localization/retroactive-review-register-20261019.json"
        chapter_path = "localization/tw-edition/chapters/02.json"
        previous_review = json_at(BASE, review_path)
        previous_register = json_at(BASE, register_path)
        previous_chapter = json_at(BASE, chapter_path)
        current_register = read_json(register_path)
        current_chapter = read_json(chapter_path)

        self.assertEqual(read_json(review_path), previous_review)
        self.assertEqual(current_register["draft_substantive_rechecks"], previous_register["draft_substantive_rechecks"])
        self.assertEqual(current_chapter["entries"][20], previous_chapter["entries"][20])
        self.assertEqual(self.review["prior_structured_draft_sha256"], previous_review["after_sha256"])
        self.assertEqual(
            self.review["prior_structured_draft_review"]["sha256"],
            hashlib.sha256((ROOT / review_path).read_bytes()).hexdigest(),
        )
        self.assertGreater(self.review["reviewed_at"], previous_review["reviewed_at"])

    def test_coverage_matches_live_draft_and_publication_audits(self):
        report = audit_drafts()
        self.assertEqual(self.coverage, report)
        after = self.batch["counts_after"]
        self.assertEqual(after["core_reviewed"], 298)
        self.assertEqual(after["runtime_items"], 309)
        self.assertEqual(after["runtime_sources"], 1207)
        self.assertEqual(after["source_registry"], 1290)
        self.assertEqual(after["json_files_checked"], 595)
        self.assertGreaterEqual(self.coverage["core_reviewed_entries"], after["core_reviewed"])
        self.assertGreaterEqual(len(self.runtime["items"]), after["runtime_items"])
        self.assertGreaterEqual(len(self.runtime["sources"]), after["runtime_sources"])
        self.assertGreaterEqual(self.coverage["registry_sources"], after["source_registry"])
        self.assertGreaterEqual(self.coverage["json_files_checked"], after["json_files_checked"])
        self.assertFalse(self.coverage["publication_ready"])


if __name__ == "__main__":
    unittest.main()

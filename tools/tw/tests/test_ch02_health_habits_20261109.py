"""第2章五篇健康生活正文的來源、雜湊與正式閱讀一致性契約。"""
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

BASE = "5571669a51ac5d3999b0249c584a905cb631ee07"
DATE = "2026-11-09"
DUE = "2027-02-09"
ITEM_IDS = ("TW-02-007", "TW-02-010", "TW-02-011", "TW-02-012", "TW-02-013")
BATCH_PATH = "localization/ch02-health-habits-20261109.json"
SOURCE_PATH = "localization/tw-edition/sources/ch02-health-habits-20261109.json"
OLD_DRAFT_HASHES = {
    "TW-02-007": "c2ef0059dd98184eb06c49ffdc5e3935575842a20a8c4e82ec34739bba177a67",
    "TW-02-010": "224ee4ecf047ce6a16b46f6a5643e2726da62bfdfd5787db9c11a99883625e16",
    "TW-02-011": "4b8d12e575954d086a2f207648589ec6663e25a07ed41b44c0ba8ea3963182da",
    "TW-02-012": "136deb73b9a97c264724d729016eb389f95e078377be1230e8631a09989b87d2",
    "TW-02-013": "43f9c3ca11d5762d8cf2c3ba0d3e61809ea7c55db71defd79428edb0f5455373",
}


def read_json(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def base_json(path):
    return json.loads(subprocess.check_output(
        ["git", "show", f"{BASE}:{path}"], cwd=ROOT, text=True
    ))


class ChapterTwoHealthHabitsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.runtime = validate_runtime()
        cls.items = {row["id"]: row for row in cls.runtime["items"]}
        cls.sources = {row["id"]: row for row in cls.runtime["sources"]}
        cls.manifest = {row["id"]: row for row in read_json("localization/manifest.json")["entries"]}
        cls.reviews = {item_id: read_json(f"localization/reviews/{item_id}.json") for item_id in ITEM_IDS}
        cls.batch = read_json(BATCH_PATH)
        cls.batch_items = {row["id"]: row for row in cls.batch["items"]}
        cls.bundle = read_json(SOURCE_PATH)
        cls.coverage = read_json("localization/tw-edition/coverage.json")
        cls.register = read_json("localization/retroactive-review-register-20261019.json")
        cls.readme = (ROOT / "locales/zh-TW/book/ch02/README.md").read_text(encoding="utf-8")

    def test_publication_hashes_sources_and_manifest_are_consistent(self):
        self.assertEqual(self.batch["baseline_main_sha"], BASE)
        self.assertEqual((self.batch["reviewed_at"], self.batch["review_due_at"]), (DATE, DUE))
        self.assertEqual(set(self.batch_items), set(ITEM_IDS))
        self.assertEqual(self.bundle["checked_at"], DATE)
        self.assertTrue(self.batch["professional_review"]["required"])
        self.assertFalse(self.batch["professional_review"]["obtained"])

        bundled_sources = {row[0]: row for row in self.bundle["sources"]}
        for item_id in ITEM_IDS:
            with self.subTest(item_id=item_id):
                item = self.items[item_id]
                manifest = self.manifest[item_id]
                review = self.reviews[item_id]
                batch = self.batch_items[item_id]
                raw = (ROOT / item["target_path"]).read_bytes()
                body = raw.decode("utf-8")
                digest = hashlib.sha256(raw).hexdigest()
                self.assertEqual(manifest["status"], "verified")
                self.assertEqual(manifest["treatment"], "taiwan_independent_rewrite")
                self.assertEqual(manifest["verified_at"], DATE)
                self.assertEqual(manifest["target_path"], item["target_path"])
                self.assertEqual(manifest["sources"], item["source_ids"])
                self.assertEqual(item["body"], body)
                self.assertEqual(item["review_status"], "source_checked")
                self.assertEqual((item["reviewed_at"], item["review_due_at"]), (DATE, DUE))
                self.assertEqual(review["target_sha256"], digest)
                self.assertEqual(review["source_reviewed_sha256"], digest)
                self.assertIsNone(batch["before_sha256"])
                self.assertEqual(batch["after_sha256"], digest)
                self.assertEqual(review["source_ids"], item["source_ids"])
                self.assertEqual(batch["source_ids"], item["source_ids"])
                self.assertEqual(review["reviewed_at"], DATE)
                self.assertEqual(review["review_due_at"], DUE)
                self.assertTrue(review["professional_review"]["required"])
                self.assertFalse(review["professional_review"]["obtained"])
                self.assertIsNone(review["prior_structured_draft_sha256"])
                self.assertIsNone(review["prior_structured_draft_review"])
                self.assertEqual(review["prior_chapter_draft_sha256"], OLD_DRAFT_HASHES[item_id])
                self.assertEqual(batch["prior_chapter_draft_sha256"], OLD_DRAFT_HASHES[item_id])

                body_urls = set(re.findall(r"\]\((https?://[^)]+)\)", body))
                source_urls = {self.sources[sid]["url"] for sid in item["source_ids"]}
                review_urls = {row["url"] for row in review["source_checks"]}
                self.assertEqual(body_urls, source_urls)
                self.assertEqual(review_urls, source_urls)
                self.assertEqual({row["source_id"] for row in review["source_checks"]}, set(item["source_ids"]))
                for sid in item["source_ids"]:
                    self.assertIn(sid, bundled_sources)
                    _, title, url, supports = bundled_sources[sid]
                    source = self.sources[sid]
                    self.assertEqual((source["title"], source["url"], source["supports"]), (title, url, supports))
                    self.assertEqual(source["accessed_at"], DATE)
                self.assertNotRegex(
                    body,
                    r"(批次摘要|AI協助|本次.{0,12}(?:審查|再審|核對)|CI\s*(?:成功|通過)|PR\s*#\d+|專業審閱仍待|待專業審閱|fork管理)",
                )
                self.assertIn(f"{item_id}.md", self.readme)

    def test_statistics_keep_population_and_denominator_limits(self):
        for item_id in ITEM_IDS:
            with self.subTest(item_id=item_id):
                review = self.reviews[item_id]
                statistics = review["statistics_assessed"]
                if not statistics:
                    self.assertIn("未找到", review["frequency_assessment"])
                    continue
                for stat in statistics:
                    for key in (
                        "period", "geographic_scope", "population", "numerator", "denominator",
                        "event_definition", "data_type", "limitations", "source_ids",
                    ):
                        self.assertTrue(stat[key], (item_id, stat.get("topic"), key))
                    self.assertTrue(set(stat["source_ids"]).issubset(review["source_ids"]))
        self.assertIn("不是國健署每週150分鐘活動建議的達標率", self.items["TW-02-011"]["body"])
        self.assertIn("不是所有同年齡台灣人的盛行率", self.items["TW-02-012"]["body"])
        self.assertIn("不能當成目前飲用率", self.items["TW-02-007"]["body"])
        self.assertIn("未加權分母", self.items["TW-02-007"]["body"])

    def test_baseline_drafts_and_historical_register_are_preserved(self):
        base_chapter = subprocess.check_output(
            ["git", "show", f"{BASE}:localization/tw-edition/chapters/02.json"], cwd=ROOT
        )
        old_chapter = json.loads(base_chapter)
        current_chapter = read_json("localization/tw-edition/chapters/02.json")
        old_rows = {row[0]: row for row in old_chapter["entries"]}
        current_rows = {row[0]: row for row in current_chapter["entries"]}
        topic_fidelity_rows = {25, 36, 47}
        self.assertEqual(set(current_rows), set(old_rows))
        for number, row in old_rows.items():
            if number not in topic_fidelity_rows:
                self.assertEqual(current_rows[number], row)
        self.assertIn("日本研究有觀察到死亡率關聯", current_rows[25][1])
        self.assertIn("日本研究探討心血管與健康老化", current_rows[36][1])
        self.assertIn("生淡水魚的中華肝吸蟲風險", current_rows[47][1])
        self.assertIn("文化脈絡與觀察性證據", current_chapter["intro"])
        base_register = base_json("localization/retroactive-review-register-20261019.json")
        base_ids = [row["id"] for row in base_register["substantive_rechecks"]]
        current_ids = [row["id"] for row in self.register["substantive_rechecks"]]
        self.assertEqual(current_ids[: len(base_ids)], base_ids)
        self.assertTrue(set(ITEM_IDS).isdisjoint(current_ids))
        topic_rechecks = [
            row for row in self.register["substantive_rechecks"]
            if row["reviewed_at"] == "2026-11-12" and row["id"] in {"TW-02-025", "TW-02-047"}
        ]
        self.assertEqual({row["id"] for row in topic_rechecks}, {"TW-02-025", "TW-02-047"})

    def test_coverage_counts_match_actual_incremental_publication(self):
        before = self.batch["counts_before"]
        self.assertEqual(before["core_reviewed"], 292)
        self.assertEqual(before["runtime_items"], 303)
        self.assertEqual(before["runtime_sources"], 1186)
        self.assertEqual(before["source_registry"], 1269)
        self.assertEqual(before["json_files_checked"], 585)
        self.assertEqual(before["substantive_rechecks"], 379)
        self.assertGreaterEqual(self.coverage["publication_completed_entries"], before["core_reviewed"] + len(ITEM_IDS))
        self.assertGreaterEqual(len(self.runtime["items"]), before["runtime_items"] + len(ITEM_IDS))
        self.assertGreaterEqual(len(self.runtime["sources"]), before["runtime_sources"] + len(self.batch["new_source_ids"]))
        self.assertGreaterEqual(self.coverage["registry_sources"], before["source_registry"] + len(self.batch["new_source_ids"]))
        self.assertGreaterEqual(self.coverage["json_files_checked"], before["json_files_checked"] + len(ITEM_IDS) + 2)
        self.assertEqual(self.coverage["unique_draft_entries"], 498)
        self.assertEqual(self.coverage["entries_without_any_draft"], 267)
        self.assertEqual(self.coverage["unresolved_reference_occurrences"], audit_drafts()["unresolved_reference_occurrences"])
        self.assertGreaterEqual(len(self.register["substantive_rechecks"]), before["substantive_rechecks"])
        self.assertFalse(self.coverage["publication_ready"])


if __name__ == "__main__":
    unittest.main()

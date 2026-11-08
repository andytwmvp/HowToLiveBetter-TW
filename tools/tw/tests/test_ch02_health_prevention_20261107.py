"""第2章四篇健康預防內容的首發來源與閱讀一致性契約。"""
import hashlib
import json
import re
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from review_contract import ROOT, validate_runtime

BASE = "c735834dde3fc678f018f2e4e5fb8e7d6319188c"
DATE = "2026-11-07"
DUE = "2027-02-07"
SOURCE_REFRESH_DATE = "2026-11-08"
SOURCE_REFRESH_DUE = "2027-02-08"
REFRESHED_SOURCE_ID = "tw02_mohw_betel_cessation_20261107"
BATCH_PATH = "localization/ch02-health-prevention-20261107.json"
SOURCE_PATH = "localization/tw-edition/sources/ch02-health-prevention-20261107.json"
ITEM_IDS = ("TW-02-008", "TW-02-009", "TW-02-019", "TW-02-045")
EXPECTED_SOURCES = {
    "tw02_hpa_betel_hazard_20261107",
    "tw02_mohw_oral_screen_20261107",
    "tw02_mohw_betel_cessation_20261107",
    "tw02_hpa_oral_warning_20261107",
    "tw02_mohw_cancer_registry_2023_20261107",
    "tw02_hpa_sodium_intake_20261107",
    "tw02_hpa_ckd_diet_20261107",
    "tw02_ntuh_hyperkalemia_diet_20261107",
    "tw02_neal_salt_substitute_trial_2021",
    "tw02_hpa_alcohol_survey_2021",
    "tw02_who_alcohol_cancer_2025",
    "tw02_mohw_alcohol_pressure_20261107",
    "tw02_mohw_alcohol_hotline_20261107",
    "tw02_mohw_alcohol_treatment_20261107",
    "tw02_hpa_prediabetes_survey_2017_2020",
    "tw02_hpa_prediabetes_guidance_20261107",
    "tw02_hpa_adult_preventive_20261107",
    "tw02_hpa_diabetes_prevalence_20261103",
}
OLD_DRAFT_HASHES = {
    "TW-02-008": "a02deb0cc89c8c3ad41d5653a64c24e29e779fe559258d7543c4bc2eb6a6e400",
    "TW-02-045": "8cc784062751293c9f3a3e0876c793eadced2bbd47f9280285ec3d79296ca31c",
}


def read_json(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def base_json(path):
    return json.loads(subprocess.check_output(
        ["git", "show", f"{BASE}:{path}"], cwd=ROOT, text=True
    ))


class ChapterTwoHealthPreventionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.runtime = validate_runtime()
        cls.items = {item["id"]: item for item in cls.runtime["items"]}
        cls.sources = {source["id"]: source for source in cls.runtime["sources"]}
        cls.manifest = {
            item["id"]: item for item in read_json("localization/manifest.json")["entries"]
        }
        cls.reviews = {
            item_id: read_json(f"localization/reviews/{item_id}.json")
            for item_id in ITEM_IDS
        }
        cls.batch = read_json(BATCH_PATH)
        cls.batch_items = {item["id"]: item for item in cls.batch["items"]}
        cls.source_bundle = read_json(SOURCE_PATH)
        cls.coverage = read_json("localization/tw-edition/coverage.json")
        cls.readme = (ROOT / "locales/zh-TW/book/ch02/README.md").read_text(encoding="utf-8")
        cls.register = read_json("localization/retroactive-review-register-20261019.json")

    def test_first_publications_have_hash_source_and_manifest_parity(self):
        self.assertEqual(self.batch["baseline_main_sha"], BASE)
        self.assertEqual(self.batch["reviewed_at"], DATE)
        self.assertEqual(self.batch["review_due_at"], DUE)
        self.assertEqual(set(self.batch_items), set(ITEM_IDS))
        self.assertEqual(set(self.batch["new_source_ids"]), EXPECTED_SOURCES)
        self.assertTrue(self.batch["professional_review"]["required"])
        self.assertFalse(self.batch["professional_review"]["obtained"])

        for item_id in ITEM_IDS:
            with self.subTest(item_id=item_id):
                item = self.items[item_id]
                manifest = self.manifest[item_id]
                batch = self.batch_items[item_id]
                review = self.reviews[item_id]
                raw = (ROOT / item["target_path"]).read_bytes()
                body = raw.decode("utf-8")
                digest = hashlib.sha256(raw).hexdigest()

                self.assertEqual(manifest["status"], "verified")
                self.assertEqual(manifest["treatment"], "taiwan_independent_rewrite")
                expected_reviewed_at = SOURCE_REFRESH_DATE if item_id == "TW-02-008" else DATE
                self.assertEqual(manifest["verified_at"], expected_reviewed_at)
                self.assertEqual(manifest["sources"], item["source_ids"])
                self.assertEqual(manifest["target_path"], item["target_path"])
                self.assertEqual(item["body"], body)
                self.assertEqual(item["review_status"], "source_checked")
                expected_review_due_at = SOURCE_REFRESH_DUE if item_id == "TW-02-008" else DUE
                self.assertEqual(item["reviewed_at"], expected_reviewed_at)
                self.assertEqual(item["review_due_at"], expected_review_due_at)
                self.assertEqual(review["target_sha256"], digest)
                self.assertEqual(review["source_reviewed_sha256"], digest)
                self.assertIsNone(batch["before_sha256"])
                if item_id == "TW-02-008":
                    refresh = review["source_revision_history"][-1]
                    self.assertEqual(batch["after_sha256"], refresh["prior_source"]["target_sha256"])
                    self.assertEqual(refresh["current_source"]["target_sha256"], digest)
                    self.assertEqual(review["source_checks"], [
                        refresh["current_check"] if row["source_id"] == REFRESHED_SOURCE_ID else row
                        for row in batch["source_checks"]
                    ])
                else:
                    self.assertEqual(batch["after_sha256"], digest)
                    self.assertEqual(review["source_checks"], batch["source_checks"])
                self.assertEqual(batch["status"], "ai_source_checked_professional_pending")
                self.assertEqual(batch["source_ids"], item["source_ids"])
                self.assertEqual(review["source_ids"], item["source_ids"])
                self.assertEqual(review["reviewed_at"], expected_reviewed_at)
                self.assertEqual(review["review_due_at"], expected_review_due_at)
                self.assertFalse(review["professional_review"]["obtained"])

                body_urls = set(re.findall(r"\]\((https?://[^)]+)\)", body))
                source_urls = {self.sources[sid]["url"] for sid in item["source_ids"]}
                review_urls = {check["url"] for check in review["source_checks"]}
                self.assertEqual(body_urls, source_urls)
                self.assertEqual(review_urls, source_urls)
                self.assertEqual(
                    {check["source_id"] for check in review["source_checks"]},
                    set(item["source_ids"]),
                )
                self.assertNotRegex(
                    body,
                    r"(批次摘要|未宣稱閱讀|本次.{0,12}(?:AI|審查|再審|核對)|CI\s*(?:成功|通過)|PR\s*#\d+|專業審閱仍待|fork管理|待專業審閱)",
                )

    def test_old_structured_drafts_are_unchanged_and_not_counted_as_history_rechecks(self):
        for item_id, expected_hash in OLD_DRAFT_HASHES.items():
            with self.subTest(item_id=item_id):
                path = f"localization/reviews/drafts/{item_id}.json"
                current = (ROOT / path).read_bytes()
                prior = subprocess.check_output(["git", "show", f"{BASE}:{path}"], cwd=ROOT)
                self.assertEqual(hashlib.sha256(current).hexdigest(), expected_hash)
                self.assertEqual(current, prior)
                self.assertEqual(
                    self.reviews[item_id]["prior_structured_draft_sha256"], expected_hash
                )
                old = json.loads(prior)
                self.assertEqual(old["reviewed_at"], "2026-10-31")
                self.assertEqual(self.batch_items[item_id]["prior_structured_draft_sha256"], expected_hash)

        for item_id in ("TW-02-009", "TW-02-019"):
            self.assertIsNone(self.reviews[item_id]["prior_structured_draft_sha256"])
            self.assertIsNone(self.batch_items[item_id]["prior_structured_draft_sha256"])

        base_register = base_json("localization/retroactive-review-register-20261019.json")
        base_rechecks = base_register["substantive_rechecks"]
        current_rechecks = self.register["substantive_rechecks"]
        self.assertEqual(current_rechecks[:len(base_rechecks)], base_rechecks)
        self.assertTrue(set(ITEM_IDS).isdisjoint(
            row["id"] for row in current_rechecks
        ))

    def test_betel_referral_source_refresh_is_append_only_and_hash_linked(self):
        item_id = "TW-02-008"
        source_id = REFRESHED_SOURCE_ID
        review = self.reviews[item_id]
        history = review["source_revision_history"]
        self.assertEqual(len(history), 1)
        refresh = history[0]
        self.assertEqual(refresh["updated_at"], SOURCE_REFRESH_DATE)
        self.assertEqual(refresh["source_id"], source_id)
        self.assertEqual(refresh["prior_source"]["url"],
                         "https://dep.mohw.gov.tw/DOOH/fp-7148-83616-124.html")
        self.assertIn("115年7月31日更新", refresh["prior_source"]["supports"])
        self.assertEqual(refresh["current_source"]["url"],
                         "https://dep.mohw.gov.tw/DOOH/cp-7148-87465-124.html")
        self.assertIn("115年8月19日更新", refresh["current_source"]["supports"])
        self.assertEqual(refresh["prior_source"]["target_sha256"],
                         self.batch_items[item_id]["after_sha256"])
        self.assertEqual(refresh["current_source"]["target_sha256"], review["target_sha256"])
        self.assertEqual(refresh["prior_source"]["reviewed_at"], DATE)
        self.assertEqual(refresh["current_source"]["reviewed_at"], SOURCE_REFRESH_DATE)
        self.assertIn("115-08-19", refresh["reason"])

        current_source = self.sources[source_id]
        self.assertEqual(current_source["url"], refresh["current_source"]["url"])
        body = self.items[item_id]["body"]
        self.assertIn(current_source["url"], body)
        self.assertNotIn(refresh["prior_source"]["url"], body)

        batch_updates = self.batch["follow_up_source_updates"]
        self.assertEqual(len(batch_updates), 1)
        self.assertEqual(batch_updates[0]["prior_source"], refresh["prior_source"])
        self.assertEqual(batch_updates[0]["current_source"], refresh["current_source"])
        self.assertEqual(batch_updates[0]["source_id"], source_id)
        self.assertIn("115年7月31日更新", self.batch_items[item_id]["source_checks"][2]["claim"])

    def test_source_bundle_statistics_and_taiwan_context_are_recorded(self):
        rows = self.source_bundle["sources"]
        self.assertEqual({row[0] for row in rows}, EXPECTED_SOURCES)
        for sid, title, url, supports in rows:
            source = self.sources[sid]
            self.assertEqual((source["title"], source["url"], source["supports"]),
                             (title, url, supports))
            expected_accessed_at = SOURCE_REFRESH_DATE if sid == REFRESHED_SOURCE_ID else DATE
            self.assertEqual(source["accessed_at"], expected_accessed_at)
            self.assertTrue(supports)

        for item_id in ITEM_IDS:
            item = self.batch_items[item_id]
            self.assertTrue(item["taiwan_context"])
            self.assertTrue(item["frequency_assessment"])
            self.assertTrue(item["statistics_assessed"])
            for statistic in item["statistics_assessed"]:
                for key in (
                    "period", "geographic_scope", "population", "numerator", "denominator",
                    "event_definition", "data_type", "limitations", "source_ids",
                ):
                    self.assertTrue(statistic[key], (item_id, statistic.get("topic"), key))

        oral = self.items["TW-02-008"]["body"]
        self.assertIn("每2年1次", oral)
        self.assertIn("8,522例新登記癌症", oral)
        self.assertIn("不是檳榔可歸因病例數", oral)
        salt = self.items["TW-02-009"]["body"]
        self.assertIn("19歲以上成人每日平均鈉攝取量超過3,000毫克", salt)
        self.assertIn("不代表每個人的攝取量", salt)
        self.assertIn("20,995名", salt)
        self.assertIn("中國農村600個村", salt)
        self.assertIn("不能直接換算成台灣一般家庭", salt)
        alcohol = self.items["TW-02-019"]["body"]
        self.assertIn("4,596人", alcohol)
        self.assertIn("加權估計的飲酒盛行率為24.4%", alcohol)
        self.assertIn("不能當成2026年的飲酒比例", alcohol)
        prediabetes = self.items["TW-02-045"]["body"]
        self.assertIn("盛行率約25%", prediabetes)
        self.assertIn("沒有列出這項估計的原始分子、未加權樣本分母或信賴區間", prediabetes)
        self.assertIn("並非糖尿病前期", prediabetes)
        self.assertIn("不能拿來當作較新的同一指標", prediabetes)

    def test_counts_derive_from_baseline_and_reader_navigation_is_synchronized(self):
        base_runtime = base_json("localization/tw-edition/runtime.json")
        base_coverage = base_json("localization/tw-edition/coverage.json")
        base_register = base_json("localization/retroactive-review-register-20261019.json")
        base_sources = {source["id"] for source in base_runtime["sources"]}
        current_sources = {source["id"] for source in self.runtime["sources"]}
        self.assertEqual(len(base_runtime["items"]), 299)
        self.assertEqual(len(base_runtime["sources"]), 1164)
        self.assertTrue(base_sources.issubset(current_sources))
        self.assertTrue(EXPECTED_SOURCES.issubset(current_sources - base_sources))
        self.assertEqual(self.batch["counts_before"]["core_reviewed"], 288)
        self.assertEqual(self.batch["counts_before"]["runtime_items"], 299)
        self.assertEqual(self.batch["counts_before"]["runtime_sources"], 1164)
        self.assertEqual(self.batch["counts_before"]["source_registry"], 1247)
        self.assertEqual(self.batch["counts_before"]["json_files_checked"], 577)
        self.assertEqual(self.batch["counts_before"]["substantive_rechecks"],
                         len(base_register["substantive_rechecks"]))
        self.assertEqual(self.batch["counts_after"]["core_reviewed"], 292)
        self.assertEqual(self.batch["counts_after"]["runtime_items"],
                         len(base_runtime["items"]) + len(ITEM_IDS))
        self.assertEqual(self.batch["counts_after"]["runtime_sources"],
                         len(base_runtime["sources"]) + len(EXPECTED_SOURCES))
        self.assertEqual(self.batch["counts_after"]["source_registry"],
                         base_coverage["registry_sources"] + len(EXPECTED_SOURCES))
        self.assertEqual(self.batch["counts_after"]["json_files_checked"],
                         base_coverage["json_files_checked"] + 6)
        self.assertEqual(self.batch["counts_after"]["substantive_rechecks"],
                         len(base_register["substantive_rechecks"]))
        self.assertGreaterEqual(self.coverage["core_reviewed_entries"],
                                self.batch["counts_after"]["core_reviewed"])
        self.assertGreaterEqual(self.coverage["publication_completed_entries"],
                                self.batch["counts_after"]["core_reviewed"])
        self.assertFalse(self.coverage["publication_ready"])
        self.assertEqual(self.coverage["publication_total_entries"], 765)
        self.assertEqual(sum(self.coverage["unresolved_source_ids"].values()),
                         self.coverage["unresolved_reference_occurrences"])
        self.assertGreaterEqual(len(self.runtime["items"]),
                                self.batch["counts_after"]["runtime_items"])
        self.assertGreaterEqual(len(self.runtime["sources"]),
                                self.batch["counts_after"]["runtime_sources"])
        self.assertGreaterEqual(self.coverage["registry_sources"],
                                self.batch["counts_after"]["source_registry"])
        self.assertGreaterEqual(self.coverage["json_files_checked"],
                                self.batch["counts_after"]["json_files_checked"])
        self.assertGreaterEqual(len(self.register["substantive_rechecks"]),
                                self.batch["counts_after"]["substantive_rechecks"])
        for item_id in ITEM_IDS:
            self.assertIn(f"{item_id}.md)", self.readme)


if __name__ == "__main__":
    unittest.main()

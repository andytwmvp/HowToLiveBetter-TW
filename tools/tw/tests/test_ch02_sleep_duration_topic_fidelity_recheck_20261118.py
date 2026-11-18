"""TW-02-013睡眠時數與規律作息主題保真度再審契約。"""
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
from recheck_history_assertions import assert_append_only_rechecks
from review_contract import validate_runtime

BASE = "0ec4aa20cf8272582f6625a9edeb755a4fc0d972"
ITEM_ID = "TW-02-013"
TARGET = "locales/zh-TW/book/ch02/TW-02-013.md"
BATCH_PATH = "localization/ch02-sleep-duration-topic-fidelity-recheck-20261118.json"
BUNDLE_PATH = "localization/tw-edition/sources/ch02-sleep-duration-topic-fidelity-recheck-20261118.json"
REGISTER_PATH = "localization/retroactive-review-register-20261019.json"
REVIEW_PATH = "localization/reviews/TW-02-013.json"
NEW_SOURCE_IDS = {
    "tw02_cappuccio_sleep_mortality_meta_2010",
    "tw02_yin_sleep_mortality_dose_response_2017",
    "tw02_taiwan_sleep_mortality_cohort_2026",
    "tw02_windred_sleep_regularity_mortality_2024",
    "tw02_kumar_social_jetlag_cvd_2026",
}


def read(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def git_bytes(revision, path):
    return subprocess.check_output(["git", "show", f"{revision}:{path}"], cwd=ROOT)


def sha(data):
    return hashlib.sha256(data).hexdigest()


class SleepDurationTopicFidelityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.runtime = validate_runtime()
        cls.items = {item["id"]: item for item in cls.runtime["items"]}
        cls.sources = {source["id"]: source for source in cls.runtime["sources"]}
        cls.manifest = {entry["id"]: entry for entry in read("localization/manifest.json")["entries"]}
        cls.register = read(REGISTER_PATH)
        cls.batch = read(BATCH_PATH)
        cls.batch_item = cls.batch["items"][0]
        cls.review = read(REVIEW_PATH)
        cls.bundle = read(BUNDLE_PATH)
        cls.body = (ROOT / TARGET).read_text(encoding="utf-8")

        added_revisions = subprocess.check_output(
            ["git", "log", "--reverse", "--diff-filter=A", "--format=%H", f"{BASE}..HEAD", "--", BATCH_PATH],
            cwd=ROOT,
            text=True,
        ).splitlines()
        if len(added_revisions) != 1:
            raise AssertionError(f"預期批次證據只新增一次，實際 revisions={added_revisions}")
        cls.batch_revision = added_revisions[0]
        cls.batch_runtime = json.loads(git_bytes(cls.batch_revision, "localization/tw-edition/runtime.json"))
        cls.batch_items = {item["id"]: item for item in cls.batch_runtime["items"]}
        cls.batch_sources = {source["id"]: source for source in cls.batch_runtime["sources"]}
        cls.batch_manifest = {
            entry["id"]: entry
            for entry in json.loads(git_bytes(cls.batch_revision, "localization/manifest.json"))["entries"]
        }
        cls.batch_register = json.loads(git_bytes(cls.batch_revision, REGISTER_PATH))
        cls.batch_review_bytes = git_bytes(cls.batch_revision, REVIEW_PATH)
        cls.batch_review = json.loads(cls.batch_review_bytes)
        cls.batch_body_bytes = git_bytes(cls.batch_revision, TARGET)
        cls.batch_body = cls.batch_body_bytes.decode("utf-8")
        cls.batch_chapter = json.loads(git_bytes(cls.batch_revision, "localization/tw-edition/chapters/02.json"))
        cls.batch_coverage = json.loads(git_bytes(cls.batch_revision, "localization/tw-edition/coverage.json"))

    def test_review_is_append_only_and_bound_to_previous_body_and_review(self):
        base_body = git_bytes(BASE, TARGET)
        base_review = git_bytes(BASE, REVIEW_PATH)
        previous_review = json.loads(base_review)
        self.assertEqual(self.batch["baseline_main_sha"], BASE)
        self.assertEqual(self.batch_item["before_sha256"], sha(base_body))
        self.assertEqual(self.batch_item["previous_body"], base_body.decode("utf-8"))
        self.assertEqual(self.batch_item["prior_review_sha256"], sha(base_review))
        self.assertEqual(self.batch_item["previous_review_snapshot"], previous_review)
        self.assertEqual(self.batch_item["after_sha256"], sha(self.batch_body_bytes))
        self.assertEqual(self.batch_item["review_sha256"], sha(self.batch_review_bytes))

        prior_revision = self.batch_item.get("prior_revision")
        if prior_revision is None:
            row = self.recheck_row()
            prior_revision = row["prior_revision"]
        self.assertEqual(
            prior_revision,
            subprocess.check_output(["git", "log", "-1", "--format=%H", BASE, "--", TARGET], cwd=ROOT, text=True).strip(),
        )
        prior_body = git_bytes(prior_revision, TARGET)
        prior_review_bytes = git_bytes(prior_revision, REVIEW_PATH)
        self.assertEqual(sha(prior_body), self.batch_item["before_sha256"])
        self.assertEqual(sha(prior_review_bytes), self.batch_item["prior_review_sha256"])

        base_register = json.loads(git_bytes(BASE, REGISTER_PATH))
        row = next(
            record for record in self.batch_register["substantive_rechecks"]
            if record["id"] == ITEM_ID and record["reviewed_at"] == "2026-11-19"
        )
        appended = assert_append_only_rechecks(
            self,
            base_register["substantive_rechecks"],
            self.register["substantive_rechecks"],
            expected_rows=(row,),
        )
        item_rechecks = [record for record in appended if record["id"] == ITEM_ID]
        self.assertTrue(item_rechecks)
        self.assertEqual(item_rechecks[0], row)
        for previous, following in zip(item_rechecks, item_rechecks[1:]):
            self.assertEqual(following["before_sha256"], previous["after_sha256"])
        current_sha = sha((ROOT / TARGET).read_bytes())
        self.assertEqual(item_rechecks[-1]["after_sha256"], current_sha)
        self.assertEqual(self.items[ITEM_ID]["body"], (ROOT / TARGET).read_text(encoding="utf-8"))
        self.assertEqual(self.review["target_sha256"], current_sha)
        self.assertEqual(row["before_sha256"], sha(base_body))
        self.assertEqual(row["after_sha256"], sha(self.batch_body_bytes))
        self.assertEqual(row["previous_body"], base_body.decode("utf-8"))
        self.assertEqual(row["previous_review_snapshot"], previous_review)
        self.assertEqual(row["status"], "ai_source_rechecked_professional_pending")
        self.assertEqual(row["reviewed_at"], "2026-11-19")
        self.assertEqual(row["review_due_at"], "2027-02-19")
        self.assertEqual(row["source_bundle_path"], BUNDLE_PATH)
        self.assertEqual(row["source_bundle_sha256"], sha((ROOT / BUNDLE_PATH).read_bytes()))
        self.assertEqual(row["review_sha256"], sha((ROOT / REVIEW_PATH).read_bytes()))

    def recheck_row(self):
        return next(
            row for row in self.batch_register["substantive_rechecks"]
            if row["id"] == ITEM_ID and row["reviewed_at"] == "2026-11-19"
        )

    def test_restored_research_and_taiwan_actions_are_in_the_reader_body(self):
        item = self.batch_items[ITEM_ID]
        body = self.batch_body
        self.assertEqual(item["body"], body)
        self.assertIn("7至9小時", body)
        self.assertIn("Cappuccio", body)
        self.assertIn("1,382,999人、112,566例死亡", body)
        self.assertIn("Yin", body)
        self.assertIn("台灣2026年一項社區世代研究", body)
        self.assertIn("3,305名", body)
        self.assertIn("規律作息", body)
        self.assertIn("社會時差", body)
        self.assertIn("群體關聯", body)
        self.assertIn("不能證明", body)
        self.assertIn("不是台灣居民的個人發生機率", body)
        self.assertIn("不要開車、騎機車或操作危險機具", body)
        self.assertIn("不能證明睡得久會造成死亡", body)
        self.assertNotRegex(
            body,
            r"(本批|本次再審|AI協助|PR\s*#\d+|CI\s*(?:通過|成功)|待專業審閱|fork管理)",
        )

    def test_sources_manifest_review_and_question_are_synchronized(self):
        item = self.batch_items[ITEM_ID]
        manifest = self.batch_manifest[ITEM_ID]
        source_ids = item["source_ids"]
        review = self.batch_review
        body = self.batch_body
        self.assertEqual(source_ids, manifest["sources"])
        self.assertEqual(source_ids, review["source_ids"])
        self.assertEqual(review["target_sha256"], sha(self.batch_body_bytes))
        self.assertEqual(review["source_reviewed_sha256"], sha(self.batch_body_bytes))
        self.assertEqual(review["reviewed_at"], "2026-11-19")
        self.assertEqual(review["review_due_at"], "2027-02-19")
        self.assertEqual(item["question"], self.batch_item["current_question"])
        self.assertTrue(review["professional_review"]["required"])
        self.assertFalse(review["professional_review"]["obtained"])

        expected_source_ids = set(source_ids)
        bundle_sources = {row[0]: row for row in self.bundle["sources"]}
        self.assertEqual(set(bundle_sources), NEW_SOURCE_IDS)
        self.assertEqual(set(self.batch_item["new_source_ids"]), NEW_SOURCE_IDS)
        self.assertEqual(review["source_bundle_sha256"], sha((ROOT / BUNDLE_PATH).read_bytes()))
        checks = {row["source_id"]: row for row in review["source_checks"]}
        self.assertEqual(set(checks), expected_source_ids)
        self.assertEqual({row["url"] for row in checks.values()}, {self.batch_sources[sid]["url"] for sid in source_ids})
        body_urls = set(re.findall(r"\]\((https?://[^)]+)\)", body))
        self.assertEqual(body_urls, {self.batch_sources[sid]["url"] for sid in source_ids})

        for sid in NEW_SOURCE_IDS:
            source = self.batch_sources[sid]
            _, title, url, supports = bundle_sources[sid]
            self.assertEqual((source["title"], source["url"], source["supports"]), (title, url, supports))
            expected_access_date = "2026-11-19" if sid == "tw02_windred_sleep_regularity_mortality_2024" else "2026-11-18"
            self.assertEqual(source["accessed_at"], expected_access_date)
            self.assertEqual(checks[sid]["accessed_at"], expected_access_date)

        question_change = review["topic_fidelity_review"]["question_change"]
        self.assertEqual(question_change["decision"], "restore_or_expand_original_research_question_without_replacing_it_with_a_superficially_similar_local_safety_topic")
        self.assertEqual(question_change["previous_question"], self.batch_item["previous_question"])
        self.assertEqual(question_change["current_question"], item["question"])

    def test_statistics_identify_denominators_periods_and_limits(self):
        statistics = self.batch_review["statistics_assessed"]
        self.assertEqual(len(statistics), 5)
        required = (
            "value", "unit", "period", "geographic_scope", "population", "numerator",
            "denominator", "denominator_definition", "event_definition", "data_type", "limitations",
        )
        for stat in statistics:
            for key in required:
                self.assertIn(key, stat)
                self.assertTrue(stat[key], (stat["topic"], key))
            self.assertTrue(set(stat["source_ids"]).issubset(self.batch_review["source_ids"]))
        taiwan = next(stat for stat in statistics if stat["topic"].startswith("台灣Chin-Shan"))
        self.assertEqual(taiwan["value"]["total_participants"], 3305)
        self.assertIn("各組人數", taiwan["limitations"])
        windred = next(stat for stat in statistics if stat["topic"].startswith("UK Biobank睡眠規律性"))
        self.assertEqual(windred["value"]["all_cause_deaths"], 1859)
        self.assertNotEqual(windred["value"]["sample_size_reported_in_abstract"], windred["value"]["sample_size_reported_in_results"])
        self.assertEqual(windred["value"]["full_adjusted_model_participants"], 46721)
        self.assertEqual(windred["value"]["highest_regularity_vs_lowest_full_adjusted_HR"], 0.70)
        self.assertEqual(windred["value"]["highest_regularity_vs_lowest_full_adjusted_95_CI"], [0.59, 0.83])
        self.assertIn("全因死亡危險比（HR）為0.70", self.batch_body)
        self.assertNotIn("機率降低30%", self.batch_body)
        self.assertNotIn("20%至48%", self.batch_body)
        self.assertEqual(self.batch_review["follow_up_verification"]["checked_at"], "2026-11-19")
        self.assertEqual(self.batch_review["source_checks"][6]["url"], "https://pmc.ncbi.nlm.nih.gov/articles/PMC10782501/")
        social = next(stat for stat in statistics if stat["topic"].startswith("UK Biobank工作日"))
        self.assertEqual(social["value"]["incident_CVD_events"], 3853)
        self.assertIn("未列中位追蹤", social["limitations"])

    def test_chapter_summary_and_coverage_are_live(self):
        chapter = self.batch_chapter
        row = next(row for row in chapter["entries"] if row[0] == 13)
        self.assertIn("睡眠長短", row[1])
        self.assertIn("長期健康關聯", row[2])
        self.assertIn("輪班", row[3])
        coverage = read("localization/tw-edition/coverage.json")
        self.assertEqual(coverage, audit_drafts())
        self.assertEqual(self.batch_coverage["publication_completed_entries"], self.batch["counts_after"]["publication_completed_entries"])
        self.assertEqual(self.batch["counts_before"]["publication_completed_entries"], self.batch["counts_after"]["publication_completed_entries"])
        self.assertEqual(self.batch["counts_after"]["runtime_sources"], len(self.batch_runtime["sources"]))
        self.assertEqual(self.batch["counts_after"]["runtime_sources"], self.batch["counts_before"]["runtime_sources"] + len(NEW_SOURCE_IDS))
        self.assertEqual(self.batch["counts_after"]["source_registry"], self.batch_coverage["registry_sources"])
        self.assertEqual(self.batch["counts_after"]["source_registry"], self.batch["counts_before"]["source_registry"] + len(NEW_SOURCE_IDS))
        self.assertEqual(self.batch["counts_after"]["coverage_json_files"], self.batch_coverage["json_files_checked"])
        self.assertEqual(self.batch["counts_after"]["coverage_json_files"], self.batch["counts_before"]["coverage_json_files"] + 2)
        self.assertEqual(self.batch["counts_before"]["review_rechecks"], len(json.loads(git_bytes(BASE, REGISTER_PATH))["substantive_rechecks"]))
        self.assertEqual(self.batch["counts_after"]["review_rechecks"], len(self.batch_register["substantive_rechecks"]))
        self.assertEqual(self.batch["counts_after"]["review_rechecks"], self.batch["counts_before"]["review_rechecks"] + 1)
        self.assertFalse(self.batch_coverage["publication_ready"])
        self.assertFalse(coverage["publication_ready"])
        current_chapter = read("localization/tw-edition/chapters/02.json")
        current_row = next(row for row in current_chapter["entries"] if row[0] == 13)
        current_item = self.items[ITEM_ID]
        self.assertEqual(current_row[1], current_item["title"])


if __name__ == "__main__":
    unittest.main()

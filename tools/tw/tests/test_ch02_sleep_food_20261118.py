"""第2章乳品、雞蛋、午睡及睡眠回補首次發布契約。"""
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
from source_bundle_test_support import source_bundle_ids_added_since

BASE = "c396867f415b8de6448992476e8f0abccc5e0084"
DATE = "2026-11-18"
DUE = "2027-02-18"
ITEM_IDS = ("TW-02-034", "TW-02-035", "TW-02-037", "TW-02-038")
BATCH_PATH = "localization/ch02-sleep-food-20261118.json"
SOURCE_PATH = "localization/tw-edition/sources/ch02-sleep-food-20261118.json"
REGISTER_PATH = "localization/retroactive-review-register-20261019.json"
STRUCTURED_DRAFT_SHA256 = {
    "TW-02-034": "8e3742168a7873d4b58a297083bd5e03f62d3c6e487742f95d7fc182bd877202",
    "TW-02-035": "4d0725e27b4629cb7c1aaa91e1ee58870fd269775eda40697af6ff0e3ef2c299",
    "TW-02-037": "c797f6191b18184bbfa2e4b361dc2917b9fa1870ded340fd9f11fbfabb698b39",
    "TW-02-038": "b7cf3879953957ab706cf05a453059dae9088313802af90a9b794ca0193dcf4e",
}


def read_json(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def git_bytes(revision, path):
    result = subprocess.run(
        ["git", "show", f"{revision}:{path}"],
        cwd=ROOT,
        capture_output=True,
    )
    return result.stdout if result.returncode == 0 else None


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


class ChapterTwoSleepFoodPublicationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.runtime = validate_runtime()
        cls.items = {row["id"]: row for row in cls.runtime["items"]}
        cls.sources = {row["id"]: row for row in cls.runtime["sources"]}
        cls.manifest = {
            row["id"]: row for row in read_json("localization/manifest.json")["entries"]
        }
        cls.reviews = {
            item_id: read_json(f"localization/reviews/{item_id}.json")
            for item_id in ITEM_IDS
        }
        cls.batch = read_json(BATCH_PATH)
        cls.batch_items = {row["id"]: row for row in cls.batch["items"]}
        cls.bundle = read_json(SOURCE_PATH)
        cls.coverage = read_json("localization/tw-edition/coverage.json")
        cls.register = read_json(REGISTER_PATH)
        cls.chapter = read_json("localization/tw-edition/chapters/02.json")
        cls.readme = (ROOT / "locales/zh-TW/book/ch02/README.md").read_text(encoding="utf-8")

    def test_first_publication_baseline_and_structured_draft_history(self):
        base_manifest = read_json_from_git(BASE, "localization/manifest.json")
        base_chapter = read_json_from_git(BASE, "localization/tw-edition/chapters/02.json")
        self.assertEqual(self.batch["baseline_main_sha"], BASE)
        self.assertEqual((self.batch["reviewed_at"], self.batch["review_due_at"]), (DATE, DUE))
        self.assertEqual(set(self.batch_items), set(ITEM_IDS))
        self.assertEqual(self.bundle["checked_at"], DATE)
        self.assertFalse(self.batch["professional_review"]["obtained"])

        base_entries = {row["id"]: row for row in base_manifest["entries"]}
        current_rows = {
            f"TW-02-{row[0]:03}": row for row in self.chapter["entries"]
        }
        prior_rows = {
            f"TW-02-{row[0]:03}": row for row in base_chapter["entries"]
        }
        for item_id in ITEM_IDS:
            with self.subTest(item_id=item_id):
                self.assertEqual(base_entries[item_id]["status"], "pending")
                self.assertIsNone(base_entries[item_id]["target_path"])
                self.assertEqual(base_entries[item_id]["sources"], [])
                self.assertIsNone(git_bytes(BASE, self.reviews[item_id]["target_path"]))
                self.assertIsNone(git_bytes(BASE, f"localization/reviews/{item_id}.json"))
                self.assertEqual(current_rows[item_id], prior_rows[item_id])
                row_hash = digest(json.dumps(
                    prior_rows[item_id], ensure_ascii=False, separators=(",", ":")
                ).encode("utf-8"))
                self.assertEqual(row_hash, STRUCTURED_DRAFT_SHA256[item_id])
                self.assertEqual(self.reviews[item_id]["prior_structured_draft_sha256"], row_hash)
                self.assertIsNone(self.reviews[item_id]["prior_chapter_draft_sha256"])

    def test正文_manifest_runtime_review_hashes_and_navigation_match(self):
        for item_id in ITEM_IDS:
            with self.subTest(item_id=item_id):
                item = self.items[item_id]
                entry = self.manifest[item_id]
                review = self.reviews[item_id]
                batch = self.batch_items[item_id]
                raw = (ROOT / item["target_path"]).read_bytes()
                body = raw.decode("utf-8")
                sha = digest(raw)

                self.assertEqual(entry["status"], "verified")
                self.assertEqual(entry["treatment"], "taiwan_independent_rewrite")
                self.assertEqual(entry["verified_at"], DATE)
                self.assertEqual(entry["target_path"], item["target_path"])
                self.assertEqual(entry["sources"], item["source_ids"])
                self.assertEqual(item["body"], body)
                self.assertEqual((item["reviewed_at"], item["review_due_at"]), (DATE, DUE))
                self.assertEqual(item["review_status"], "source_checked")
                self.assertEqual(review["target_sha256"], sha)
                self.assertEqual(review["source_reviewed_sha256"], sha)
                self.assertEqual(batch["before_sha256"], None)
                self.assertEqual(batch["after_sha256"], sha)
                self.assertEqual(batch["source_ids"], item["source_ids"])
                self.assertEqual(review["source_ids"], item["source_ids"])
                self.assertEqual(review["reviewed_at"], DATE)
                self.assertEqual(review["review_due_at"], DUE)
                self.assertTrue(review["professional_review"]["required"])
                self.assertFalse(review["professional_review"]["obtained"])
                self.assertIn("未取得獨立相關專業審閱", review["reviewer"])
                self.assertEqual(batch["topic_fidelity_review"], review["topic_fidelity_review"])
                self.assertEqual(self.readme.count(f"{item_id}.md"), 1)
                self.assertNotRegex(
                    body,
                    r"(批次摘要|AI協助|本次.{0,12}(?:審查|再審|核對)|CI\s*(?:成功|通過)|PR\s*#\d+|待專業審閱|fork管理)",
                )

    def test_body_links_sources_checks_and_new_source_bundle_are_exact(self):
        bundled = {row[0]: row for row in self.bundle["sources"]}
        self.assertEqual(set(bundled), set(self.batch["new_source_ids"]))
        self.assertEqual(
            [row[0] for row in self.bundle["sources"]], self.batch["new_source_ids"]
        )
        self.assertEqual(
            set(self.batch["new_source_ids"]),
            set(source_bundle_ids_added_since(ROOT, BASE)),
        )
        baseline_runtime = read_json_from_git(BASE, "localization/tw-edition/runtime.json")
        old_source_ids = {row["id"] for row in baseline_runtime["sources"]}
        added_runtime_sources = set(self.sources) - old_source_ids
        self.assertEqual(added_runtime_sources, set(self.batch["new_source_ids"]))

        for item_id in ITEM_IDS:
            with self.subTest(item_id=item_id):
                item = self.items[item_id]
                review = self.reviews[item_id]
                body = item["body"]
                body_urls = set(re.findall(r"\]\((https?://[^)]+)\)", body))
                expected_urls = {self.sources[sid]["url"] for sid in item["source_ids"]}
                checks = {row["source_id"]: row for row in review["source_checks"]}
                self.assertEqual(body_urls, expected_urls)
                self.assertEqual(set(checks), set(item["source_ids"]))
                for sid in item["source_ids"]:
                    source = self.sources[sid]
                    check = checks[sid]
                    self.assertEqual(check["url"], source["url"])
                    self.assertEqual(check["title"], source["title"])
                    self.assertLessEqual(check["accessed_at"], DATE)
                    self.assertTrue(check["claim"])
                    self.assertTrue(check["supporting_passage"])
                    if sid in bundled:
                        self.assertEqual(source["accessed_at"], DATE)
                        self.assertEqual(
                            bundled[sid],
                            [source[k] for k in ("id", "title", "url", "supports")],
                        )

    def test_taiwan_statistics_have_correct_denominators_and_topic_limits(self):
        dairy = self.reviews["TW-02-034"]
        dairy_stats = {row["topic"]: row for row in dairy["statistics_assessed"]}
        self.assertEqual(
            {topic: dairy_stats[topic]["value"] for topic in (
                "台灣19至44歲男性每日乳品不足一份的調查比例",
                "台灣45至64歲男性每日乳品不足一份的調查比例",
                "台灣19至44歲女性每日乳品不足一份的調查比例",
                "台灣45至64歲女性每日乳品不足一份的調查比例",
            )},
            {
                "台灣19至44歲男性每日乳品不足一份的調查比例": "92.1%",
                "台灣45至64歲男性每日乳品不足一份的調查比例": "95.3%",
                "台灣19至44歲女性每日乳品不足一份的調查比例": "91.8%",
                "台灣45至64歲女性每日乳品不足一份的調查比例": "93.1%",
            },
        )
        self.assertEqual(dairy_stats["台灣19至44歲男性每日乳品不足一份的調查比例"]["denominator"],
                         "表列未加權樣本945人；加權估計母群分母未列原始人數")
        self.assertIn("95.3%", self.items["TW-02-034"]["body"])
        self.assertIn("92.1%", self.items["TW-02-034"]["body"])
        self.assertIn("91.8%", self.items["TW-02-034"]["body"])
        self.assertIn("93.1%", self.items["TW-02-034"]["body"])
        milk = next(row for row in dairy["statistics_assessed"] if row["topic"] == "每日牛奶攝取200公克與全因死亡")
        self.assertEqual(milk["value"], {"HR": 0.98, "95_CI": [0.93, 1.02]})
        self.assertIn("證據確定性極低", milk["limitations"])

        egg = self.reviews["TW-02-035"]["statistics_assessed"][0]
        self.assertEqual(egg["value"]["quality"], "critically low")
        self.assertIn("整體品質極低", self.items["TW-02-035"]["body"])
        self.assertEqual(egg["value"]["included_meta_analyses"], 14)
        self.assertEqual(egg["value"]["observational"], 10)
        self.assertEqual(egg["value"]["interventional"], 4)
        nap = self.reviews["TW-02-037"]["statistics_assessed"][0]
        self.assertEqual(nap["value"]["cohort"], 1338)
        self.assertEqual(nap["value"]["deaths"], 926)
        self.assertEqual(nap["value"]["adjusted_HR_per_hour"], 1.13)
        sleep_stats = self.reviews["TW-02-038"]["statistics_assessed"]
        acute_sleep = sleep_stats[0]
        self.assertEqual(acute_sleep["value"]["participants"], 85618)
        self.assertEqual(acute_sleep["value"]["person_nights"], 574230)
        self.assertEqual(acute_sleep["value"]["data_collection_start"], "2013-06-01")
        self.assertEqual(acute_sleep["value"]["data_collection_end"], "2015-12-23")
        self.assertEqual(acute_sleep["value"]["deaths"], 3549)
        self.assertEqual(
            acute_sleep["value"]["groups"]["SR_without_rebound"]["adjusted_HR"], 1.15
        )
        self.assertEqual(
            acute_sleep["value"]["groups"]["severe_SR_without_rebound"]["adjusted_HR"], 1.42
        )
        self.assertFalse(
            acute_sleep["value"]["groups"]["SR_with_rebound"]["significant_vs_regular_sleep"]
        )
        self.assertFalse(
            acute_sleep["value"]["groups"]["severe_SR_with_rebound"]["significant_vs_regular_sleep"]
        )
        self.assertIn("3,549 人死亡", self.items["TW-02-038"]["body"])
        self.assertIn("跨所有限制後夜平均睡眠超過估計需求", self.items["TW-02-038"]["body"])
        self.assertEqual(sleep_stats[1]["value"]["mortality_analysis_n"], 73513)
        weekend = sleep_stats[1]
        self.assertEqual(weekend["value"]["mortality_analysis_n"], 73513)
        self.assertEqual(weekend["value"]["mortality_events"], 2776)
        self.assertEqual(weekend["value"]["incident_CVD_analysis_n"], 70518)
        self.assertEqual(weekend["value"]["incident_CVD_primary_analysis_events"], 9092)
        self.assertEqual(weekend["value"]["table_1_descriptive_sample_n"], 73513)
        self.assertEqual(weekend["value"]["table_1_descriptive_CVD_events"], 12108)
        self.assertEqual(sum(weekend["value"]["table_1_CVD_events_by_weekend_sleep_group"].values()), 12108)
        self.assertIn("2,776 人死亡", self.items["TW-02-038"]["body"])
        self.assertIn("9,092 件事件", self.items["TW-02-038"]["body"])
        self.assertIn("12,108 件心血管事件", self.items["TW-02-038"]["body"])
        self.assertIn("不能把兩個事件數混作同一分母", self.items["TW-02-038"]["body"])
        weekend_check = next(
            row for row in self.reviews["TW-02-038"]["source_checks"]
            if row["source_id"] == "tw02_weekend_catchup_sleep_2024"
        )
        self.assertIn("9,092件", weekend_check["supporting_passage"])
        self.assertIn("12,108件", weekend_check["supporting_passage"])

        for item_id in ITEM_IDS:
            for statistic in self.reviews[item_id]["statistics_assessed"]:
                for key in (
                    "value", "unit", "period", "geographic_scope", "population", "numerator",
                    "denominator", "denominator_definition", "event_definition", "data_type",
                    "limitations", "source_ids", "accessed_at",
                ):
                    self.assertTrue(statistic.get(key), (item_id, statistic.get("topic"), key))
                self.assertLessEqual(statistic["accessed_at"], DATE)
                self.assertTrue(set(statistic["source_ids"]).issubset(self.items[item_id]["source_ids"]))

        self.assertIn("延壽建議", self.reviews["TW-02-034"]["topic_fidelity_review"]["reader_content_decision"])
        self.assertIn("午睡時長處方", self.reviews["TW-02-037"]["topic_fidelity_review"]["historical_claim_decisions"][0]["reason"])
        self.assertIn("不同研究", self.reviews["TW-02-038"]["topic_fidelity_review"]["reader_content_decision"])

    def test_coverage_batch_counts_and_recheck_history_are_consistent(self):
        base_coverage = read_json_from_git(BASE, "localization/tw-edition/coverage.json")
        base_runtime = read_json_from_git(BASE, "localization/tw-edition/runtime.json")
        base_register = read_json_from_git(BASE, REGISTER_PATH)
        current_register = read_json(REGISTER_PATH)
        self.assertEqual(current_register, base_register)
        self.assertEqual(self.coverage, audit_drafts())
        self.assertFalse(self.coverage["publication_ready"])
        self.assertEqual(self.coverage["core_reviewed_entries"], 321)

        before = self.batch["counts_before"]
        after = self.batch["counts_after"]
        self.assertEqual(before["core_reviewed"], base_coverage["core_reviewed_entries"])
        self.assertEqual(before["runtime_items"], len(base_runtime["items"]))
        self.assertEqual(before["runtime_sources"], len(base_runtime["sources"]))
        self.assertEqual(before["source_registry"], base_coverage["registry_sources"])
        self.assertEqual(before["json_files_checked"], base_coverage["json_files_checked"])
        self.assertEqual(before["substantive_rechecks"], len(base_register["substantive_rechecks"]))
        self.assertEqual(after["core_reviewed"], before["core_reviewed"] + len(ITEM_IDS))
        self.assertEqual(after["runtime_items"], before["runtime_items"] + len(ITEM_IDS))
        self.assertEqual(after["runtime_sources"], before["runtime_sources"] + len(self.batch["new_source_ids"]))
        self.assertEqual(after["source_registry"], before["source_registry"] + len(self.batch["new_source_ids"]))
        self.assertEqual(after["json_files_checked"], before["json_files_checked"] + len(ITEM_IDS) + 2)
        self.assertEqual(after["substantive_rechecks"], before["substantive_rechecks"])
        self.assertEqual(after["core_reviewed"], self.coverage["publication_completed_entries"])
        self.assertEqual(after["runtime_sources"], len(self.runtime["sources"]))
        self.assertEqual(after["source_registry"], self.coverage["registry_sources"])
        self.assertEqual(after["json_files_checked"], self.coverage["json_files_checked"])
        self.assertFalse(after["publication_ready"])


def read_json_from_git(revision, path):
    raw = git_bytes(revision, path)
    if raw is None:
        raise AssertionError(f"missing base file: {revision}:{path}")
    return json.loads(raw)


if __name__ == "__main__":
    unittest.main()

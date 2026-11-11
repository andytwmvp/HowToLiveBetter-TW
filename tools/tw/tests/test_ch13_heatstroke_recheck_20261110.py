"""第13章熱傷害條目的急救安全、監測統計與歷史追溯契約。"""
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
from retroactive_audit import validate_recheck_history
from review_contract import publication_report, validate_runtime


BASE = "a5482a74c68ef521a3f306bd758398053436b8b9"
ITEM_ID = "TW-13-022"
BODY_PATH = "locales/zh-TW/book/ch13/TW-13-022.md"
REVIEW_PATH = "localization/reviews/TW-13-022.json"
BATCH_PATH = "localization/ch13-heatstroke-recheck-20261110.json"
REGISTER_PATH = "localization/retroactive-review-register-20261019.json"
EXPECTED_SOURCE_IDS = (
    "ch13_heat_hpa_firstaid_20261110",
    "ch13_heat_niosh_20261110",
    "ch13_heat_monitor_csv_20261110",
)


def read(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def read_at(revision, path):
    return json.loads(subprocess.check_output(["git", "show", f"{revision}:{path}"], cwd=ROOT))


def git_bytes(revision, path):
    return subprocess.check_output(["git", "show", f"{revision}:{path}"], cwd=ROOT)


def sha256(data):
    return hashlib.sha256(data).hexdigest()


class HeatstrokeRecheckTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.runtime = validate_runtime()
        cls.items = {item["id"]: item for item in cls.runtime["items"]}
        cls.sources = {source["id"]: source for source in cls.runtime["sources"]}
        cls.manifest = {
            item["id"]: item for item in read("localization/manifest.json")["entries"]
        }
        cls.review = read(REVIEW_PATH)
        cls.register = read(REGISTER_PATH)
        cls.batch = read(BATCH_PATH)
        cls.item = cls.items[ITEM_ID]
        cls.entry = cls.manifest[ITEM_ID]
        cls.history = [
            row for row in cls.register["substantive_rechecks"]
            if row["id"] == ITEM_ID and row["reviewed_at"] == "2026-11-10"
        ]
        cls.tracked = next(
            row for row in cls.register["tracked_formal_items"] if row["id"] == ITEM_ID
        )

    def test_recheck_preserves_body_review_and_append_only_history(self):
        body_bytes = (ROOT / BODY_PATH).read_bytes()
        body = body_bytes.decode("utf-8")
        body_sha = sha256(body_bytes)
        baseline_runtime = read_at(BASE, "localization/tw-edition/runtime.json")
        previous_item = next(item for item in baseline_runtime["items"] if item["id"] == ITEM_ID)
        previous_review = git_bytes(BASE, REVIEW_PATH)
        previous_review_json = json.loads(previous_review)
        batch_item = self.batch["items"][0]

        self.assertEqual(self.batch["baseline_main_sha"], BASE)
        self.assertEqual(self.batch["reviewed_at"], "2026-11-10")
        self.assertEqual(self.batch["review_due_at"], "2027-02-10")
        self.assertEqual(self.batch["new_source_ids"], list(EXPECTED_SOURCE_IDS))
        self.assertEqual(self.batch["source_records_reused"], [])
        self.assertEqual(self.batch["source_records_retired_from_item"], [
            "ch13_heat_ntuh", "ch13_heat_niosh", "ch13_heat_hpa_20250822"
        ])
        self.assertEqual(len(self.history), 1)
        record = self.history[0]
        self.assertEqual(record["prior_revision"], BASE)
        self.assertEqual(record["previous_body"], previous_item["body"])
        self.assertEqual(record["before_sha256"], sha256(previous_item["body"].encode("utf-8")))
        self.assertEqual(record["prior_review_sha256"], sha256(previous_review))
        self.assertEqual(record["prior_reviewed_at"], previous_review_json["reviewed_at"])
        self.assertEqual(record["after_sha256"], body_sha)
        self.assertEqual(batch_item["before_sha256"], record["before_sha256"])
        self.assertEqual(batch_item["after_sha256"], body_sha)
        self.assertEqual(batch_item["prior_review_sha256"], record["prior_review_sha256"])
        self.assertEqual(batch_item["review_sha256"], sha256((ROOT / REVIEW_PATH).read_bytes()))
        self.assertEqual(self.item["body"], body)
        self.assertEqual(self.entry["target_path"], BODY_PATH)
        self.assertEqual(self.entry["sources"], list(EXPECTED_SOURCE_IDS))
        self.assertEqual(self.entry["verified_at"], self.review["reviewed_at"])
        self.assertEqual(self.item["source_ids"], self.entry["sources"])
        self.assertEqual(self.review["target_sha256"], body_sha)
        self.assertEqual(self.review["source_reviewed_sha256"], body_sha)
        self.assertEqual(self.review["source_checks"], record["source_checks"])
        self.assertEqual(self.review["limits"], record["limits"])
        self.assertEqual(self.review["review_due_at"], "2027-02-10")
        self.assertEqual(record["status"], "ai_source_rechecked_professional_pending")
        self.assertEqual(self.tracked["new_standard_substantive_review"], record["status"])
        self.assertEqual(self.tracked["frequency_applicability"],
                         "relevant_but_no_individual_exposure_denominator; legal_status_reviewed_separately")
        validate_recheck_history(ROOT, record, self.item)

    def test_reader_copy_leads_with_safe_taiwan_first_aid(self):
        body = self.item["body"]
        self.assertLess(body.index("打119"), body.index("2,919人次"))
        for phrase in (
            "冷水浸泡降溫最快", "扶穩頭部", "口鼻持續離水", "沒有抽搐或呼吸不穩",
            "冷水淋濕皮膚並搧風", "不要餵水或灌水", "側躺並維持呼吸道暢通",
            "沒有正常呼吸", "退燒藥", "酒精",
        ):
            self.assertIn(phrase, body)
        self.assertNotRegex(body, r"本批|本次再審|來源實質再核對|PR\s*#|CI\s*(?:通過|成功)|專業審閱仍待")
        body_urls = set(re.findall(r"\]\((https://[^)]+)\)", body))
        runtime_urls = {self.sources[source_id]["url"] for source_id in EXPECTED_SOURCE_IDS}
        self.assertEqual(body_urls, runtime_urls)
        self.assertEqual(
            {check["url"] for check in self.review["source_checks"]}, runtime_urls
        )

    def test_statistics_keep_scope_period_denominator_and_csv_fingerprint(self):
        records = self.history[0]["statistics_assessed"]
        self.assertEqual(len(records), 3)
        expected = {
            "2024全年": "3942",
            "2025全年": "3496",
            "2026-01-01至2026-10-26": "2919",
        }
        for stat in records:
            with self.subTest(period=stat["period"]):
                self.assertEqual(stat["value"], expected[stat["period"]])
                self.assertIsNone(stat["denominator"])
                for field in (
                    "unit", "geographic_scope", "population", "numerator",
                    "denominator_definition", "event_definition", "data_type",
                    "source_ids", "accessed_at", "limitations",
                ):
                    self.assertTrue(stat.get(field), field)
                self.assertIn("部分院所", stat["limitations"])
                self.assertIn("多類熱傷害", stat["limitations"])
        source = next(self.sources[source_id] for source_id in EXPECTED_SOURCE_IDS
                      if source_id.endswith("monitor_csv_20261110"))
        self.assertIn("de59b386382753110b1b0be3ded3debba2102661385b614a0e6921af11ae76b8", source["supports"])
        self.assertEqual(self.batch["items"][0]["stats_resource_sha256"],
                         "de59b386382753110b1b0be3ded3debba2102661385b614a0e6921af11ae76b8")
        self.assertEqual(self.batch["items"][0]["stats_resource_rows_including_header"], 29309)
        self.assertEqual(self.batch["items"][0]["stats_rows_by_year"], {
            "2024": 2586,
            "2025": 2460,
            "2026_through_2026-10-26": 2047,
        })
        self.assertEqual(self.batch["items"][0]["stats_encounters_by_year"], {
            "2024": 3942,
            "2025": 3496,
            "2026_through_2026-10-26": 2919,
        })
        self.assertIn("不能據此推算個人發生率", self.item["body"])

    def test_live_coverage_and_review_tracking_match_the_batch(self):
        coverage = read("localization/tw-edition/coverage.json")
        baseline_coverage = read_at(BASE, "localization/tw-edition/coverage.json")
        baseline_manifest = read_at(BASE, "localization/manifest.json")
        baseline_register = read_at(BASE, REGISTER_PATH)
        self.assertEqual(self.batch["counts_before"]["manifest_entries"],
                         len(baseline_manifest["entries"]))
        self.assertEqual(self.batch["counts_before"]["runtime_items"],
                         len(baseline_runtime_items := read_at(BASE, "localization/tw-edition/runtime.json")["items"]))
        self.assertEqual(self.batch["counts_before"]["runtime_sources"],
                         len(read_at(BASE, "localization/tw-edition/runtime.json")["sources"]))
        self.assertEqual(self.batch["counts_before"]["review_rechecks"],
                         len(baseline_register["substantive_rechecks"]))
        self.assertEqual(self.batch["counts_before"]["coverage_json_files"],
                         baseline_coverage["json_files_checked"])
        counts_before = self.batch["counts_before"]
        counts_after = self.batch["counts_after"]
        self.assertEqual(counts_after["manifest_entries"], counts_before["manifest_entries"])
        self.assertEqual(counts_after["runtime_items"], counts_before["runtime_items"])
        self.assertEqual(counts_after["runtime_sources"],
                         counts_before["runtime_sources"] + len(self.batch["new_source_ids"]))
        self.assertEqual(counts_after["review_rechecks"],
                         counts_before["review_rechecks"] + len(self.history))
        source_bundle = f"localization/tw-edition/sources/{Path(BATCH_PATH).name}"
        batch_json_paths = {BATCH_PATH, source_bundle} | {
            row["review_path"] for row in self.batch["items"] if row.get("review_path")
        }
        baseline_json_paths = set(subprocess.check_output(
            ["git", "ls-tree", "-r", "--name-only", BASE, "--", "localization"],
            cwd=ROOT,
            text=True,
        ).splitlines())
        added_json_files = len(batch_json_paths - baseline_json_paths)
        self.assertEqual(counts_after["coverage_json_files"],
                         counts_before["coverage_json_files"] + added_json_files)
        self.assertEqual(counts_after["registry_sources"],
                         counts_before["registry_sources"] + len(self.batch["new_source_ids"]))
        self.assertGreaterEqual(len(self.manifest), counts_after["manifest_entries"])
        self.assertGreaterEqual(len(self.runtime["items"]), counts_after["runtime_items"])
        self.assertGreaterEqual(len(self.runtime["sources"]), counts_after["runtime_sources"])
        self.assertGreaterEqual(len(self.register["substantive_rechecks"]), counts_after["review_rechecks"])
        self.assertGreaterEqual(coverage["json_files_checked"], counts_after["coverage_json_files"])
        self.assertGreaterEqual(coverage["registry_sources"], counts_after["registry_sources"])
        self.assertEqual(coverage, audit_drafts())
        self.assertEqual(coverage["publication_completed_entries"],
                         publication_report()["publication_completed_entries"])
        self.assertGreaterEqual(coverage["core_reviewed_entries"],
                                baseline_coverage["core_reviewed_entries"])
        self.assertFalse(coverage["publication_ready"])
        self.assertGreaterEqual(len(self.runtime["items"]), len(baseline_runtime_items))


if __name__ == "__main__":
    unittest.main()

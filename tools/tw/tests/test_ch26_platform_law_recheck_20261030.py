"""第26章支付、兒少工作與個資事故四篇歷史再審契約。"""
import hashlib
import json
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from reader_copy_test_support import (
    assert_body_version_matches_review_or_cleanup,
    assert_reader_limits_match_review_or_cleanup,
)
from retroactive_audit import validate_recheck_history
from review_contract import ROOT, validate_runtime


EVIDENCE_PATH = "localization/ch26-platform-law-recheck-20261030.json"
ITEM_IDS = {"TW-26-001", "TW-26-008", "TW-26-010", "TW-26-012"}


def read(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def read_at(revision, path):
    raw = subprocess.check_output(
        ["git", "show", f"{revision}:{path}"], cwd=ROOT
    )
    return json.loads(raw)


class PlatformLawRecheckTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.evidence = read(EVIDENCE_PATH)
        cls.baseline = cls.evidence["baseline_main_sha"]
        cls.runtime = validate_runtime()
        cls.items = {item["id"]: item for item in cls.runtime["items"]}
        cls.sources = {source["id"]: source for source in cls.runtime["sources"]}
        cls.manifest = {
            item["id"]: item for item in read("localization/manifest.json")["entries"]
        }
        cls.reviews = {
            item_id: read(f"localization/reviews/{item_id}.json")
            for item_id in ITEM_IDS
        }
        register = read("localization/retroactive-review-register-20261019.json")
        cls.records = {item["id"]: item for item in register["substantive_rechecks"]}
        cls.evidence_items = {
            item["id"]: item for item in cls.evidence["items"]
        }

    def test_progress_counts_are_reconciled_to_latest_baseline(self):
        self.assertEqual(set(self.evidence_items), ITEM_IDS)
        self.assertIn("未新增核心條目", self.evidence["scope"])

        before_coverage = read_at(
            self.baseline, "localization/tw-edition/coverage.json"
        )
        before_runtime = read_at(
            self.baseline, "localization/tw-edition/runtime.json"
        )
        before_register = read_at(
            self.baseline, "localization/retroactive-review-register-20261019.json"
        )
        counts_before = self.evidence["counts_before"]
        counts_after = self.evidence["counts_after"]
        coverage = read("localization/tw-edition/coverage.json")
        current_register = read("localization/retroactive-review-register-20261019.json")

        self.assertEqual(
            counts_before["core_completed"],
            before_coverage["publication_completed_entries"],
        )
        self.assertEqual(counts_before["runtime_items"], len(before_runtime["items"]))
        self.assertEqual(
            counts_before["runtime_sources_before"], len(before_runtime["sources"])
        )
        self.assertEqual(
            counts_before["substantive_rechecks_before"],
            len(before_register["substantive_rechecks"]),
        )
        self.assertEqual(
            counts_after["core_completed"], coverage["publication_completed_entries"]
        )
        self.assertEqual(counts_after["core_total"], coverage["publication_total_entries"])
        self.assertEqual(counts_after["runtime_items"], len(self.runtime["items"]))
        self.assertEqual(counts_after["runtime_sources"], len(self.runtime["sources"]))
        self.assertEqual(
            counts_after["substantive_rechecks"],
            len(current_register["substantive_rechecks"]),
        )
        self.assertEqual(counts_after["json_files"], coverage["json_files_checked"])
        self.assertEqual(counts_after["registry_sources"], coverage["registry_sources"])
        self.assertEqual(
            counts_after["unresolved_source_ids"], len(coverage["unresolved_source_ids"])
        )
        self.assertEqual(
            counts_after["unresolved_reference_occurrences"],
            coverage["unresolved_reference_occurrences"],
        )
        self.assertFalse(counts_after["publication_ready"])
        self.assertFalse(coverage["publication_ready"])

    def test_articles_reviews_sources_and_history_align(self):
        for item_id in ITEM_IDS:
            with self.subTest(item=item_id):
                item = self.items[item_id]
                evidence = self.evidence_items[item_id]
                review = self.reviews[item_id]
                record = self.records[item_id]
                manifest_item = self.manifest[item_id]
                body_bytes = (ROOT / manifest_item["target_path"]).read_bytes()
                body_sha = hashlib.sha256(body_bytes).hexdigest()
                body = body_bytes.decode("utf-8")

                self.assertEqual(body, item["body"])
                self.assertEqual(body_sha, evidence["after_sha256"])
                self.assertEqual(body_sha, review["target_sha256"])
                self.assertEqual(body_sha, review["source_reviewed_sha256"])
                self.assertEqual(body_sha, record["after_sha256"])
                self.assertEqual(review["reviewed_at"], evidence["reviewed_at"])
                self.assertEqual(review["review_due_at"], evidence["review_due_at"])
                self.assertEqual(record["review_due_at"], evidence["review_due_at"])
                self.assertEqual(record["status"], "ai_source_rechecked_professional_pending")
                self.assertEqual(manifest_item["verified_at"], self.evidence["reviewed_at"])
                self.assertEqual(item["source_ids"], evidence["source_ids"])
                self.assertEqual(record["source_ids"], evidence["source_ids"])
                self.assertEqual(review["source_checks"], evidence["source_checks"])
                self.assertEqual(record["source_checks"], evidence["source_checks"])
                self.assertEqual(record["limits"], review["limits"])
                self.assertEqual(
                    {check["url"] for check in review["source_checks"]},
                    {self.sources[source_id]["url"] for source_id in item["source_ids"]},
                )
                self.assertEqual(
                    set(manifest_item["sources"]),
                    {self.sources[source_id]["url"] for source_id in item["source_ids"]},
                )
                assert_body_version_matches_review_or_cleanup(
                    self, item_id, evidence["after_sha256"], body_sha
                )
                assert_reader_limits_match_review_or_cleanup(
                    self, item_id, review["limits"][0]
                )
                old_item = next(
                    row for row in read_at(self.baseline, "localization/tw-edition/runtime.json")["items"]
                    if row["id"] == item_id
                )
                self.assertEqual(
                    hashlib.sha256(old_item["body"].encode("utf-8")).hexdigest(),
                    evidence["before_sha256"],
                )
                prior_review = subprocess.check_output(
                    ["git", "show", f"{self.baseline}:localization/reviews/{item_id}.json"],
                    cwd=ROOT,
                )
                self.assertEqual(
                    hashlib.sha256(prior_review).hexdigest(),
                    evidence["prior_review_sha256"],
                )
                validate_recheck_history(ROOT, record, item)

    def test_new_sources_are_additive_and_have_claim_level_limits(self):
        prior_sources = {
            source["id"]: source
            for source in read_at(
                self.baseline, "localization/tw-edition/runtime.json"
            )["sources"]
        }
        source_ids = set(self.sources)
        added_ids = source_ids - set(prior_sources)
        self.assertEqual(added_ids, set(self.evidence["new_source_ids"]))
        for source_id, source in prior_sources.items():
            with self.subTest(source=source_id):
                self.assertEqual(self.sources[source_id], source)

        for item in self.evidence["items"]:
            for statistic in item["statistics_assessed"]:
                with self.subTest(item=item["id"], statistic=statistic["name"]):
                    self.assertIn("data_type", statistic)
                    self.assertIn("limitations", statistic)
                    self.assertIsNone(statistic["denominator"])
                    self.assertTrue(statistic["denominator_definition"])

    def test_reader_copy_is_local_and_uses_the_measurement_period_for_payment_deadline(self):
        bodies = {item_id: self.items[item_id]["body"] for item_id in ITEM_IDS}
        for item_id, body in bodies.items():
            with self.subTest(item=item_id):
                for phrase in ("本批", "累計", "實質再審", "AI來源實質再審", "下方為原作"):
                    self.assertNotIn(phrase, body)

        payment = bodies["TW-26-001"]
        self.assertIn("一年日平均餘額", payment)
        self.assertIn("計算期間末日的次日起算6個月", payment)
        self.assertNotIn("自逾額日起", payment)
        minors = bodies["TW-26-008"]
        for phrase in ("開始工作日前90日至20日", "工作開始後10日內", "每次許可最長1年"):
            self.assertIn(phrase, minors)
        self.assertIn("不能說未成年人付款就一定可退款", minors)
        transfer = bodies["TW-26-010"]
        self.assertIn("2025年11月11日公布", transfer)
        self.assertIn("尚未施行", transfer)
        incident = bodies["TW-26-012"]
        self.assertIn("204件政府資安事件通報", incident)
        self.assertIn("其中95件包含攻防演練", incident)
        self.assertIn("沒有全行業通用的「72小時」期限", incident)


if __name__ == "__main__":
    unittest.main()

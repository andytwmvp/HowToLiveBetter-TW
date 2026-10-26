# -*- coding: utf-8 -*-
"""第7章健保、職訓、身障支持與無住處安全四篇歷史實質再審。"""
import hashlib
import json
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import retroactive_audit as audit
from review_contract import ROOT, publication_report, validate_runtime

BASE = "d7da29e335ae04ef3c5912b29be5d2ff6b25bad6"
IDS = ("TW-07-021", "TW-07-018", "TW-07-013", "TW-07-008")
NEW_SOURCE_IDS = {
    "ch07_disability_law_current_2026",
    "ch07_disability_law_history_2026",
    "ch07_mohw_aids_guide_2026",
    "ch07_aids_ntpc_recheck_2026",
    "bli_training_allowance_2026",
    "bli_employment_insurance_law_current",
    "bli_employment_insurance_history_2026",
    "bli_jobtraining_admin_2024",
    "bli_jobtraining_monthly_2026",
    "nhi_class_priority_2025",
    "bli_labor_continuation_15y_2025",
    "bli_labor_continuation_rules",
}


def read(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


class Ch07IncomeBenefitsSafetyRecheckTests(unittest.TestCase):
    def test_history_and_reader_contracts_are_synchronized(self):
        old_runtime = json.loads(subprocess.check_output(
            ["git", "show", f"{BASE}:localization/tw-edition/runtime.json"], cwd=ROOT))
        old_sources = {row["id"]: row for row in old_runtime["sources"]}
        runtime = validate_runtime()
        sources = {row["id"]: row for row in runtime["sources"]}
        items = {row["id"]: row for row in runtime["items"]}
        manifest = {row["id"]: row for row in read("localization/manifest.json")["entries"]}
        register = read("localization/retroactive-review-register-20261019.json")
        records = {row["id"]: row for row in register["substantive_rechecks"]}

        self.assertEqual(
            old_runtime["sources"],
            [row for row in runtime["sources"] if row["id"] in old_sources],
        )
        self.assertTrue(NEW_SOURCE_IDS <= set(sources) - set(old_sources))
        for item_id in IDS:
            with self.subTest(item_id=item_id):
                item = items[item_id]
                row = records[item_id]
                review = read(f"localization/reviews/{item_id}.json")
                prior_review = subprocess.check_output(
                    ["git", "show", f"{BASE}:localization/reviews/{item_id}.json"], cwd=ROOT)
                body_bytes = (ROOT / item["target_path"]).read_bytes()
                body_sha = hashlib.sha256(body_bytes).hexdigest()
                old_item = next(value for value in old_runtime["items"] if value["id"] == item_id)

                self.assertEqual(row["prior_revision"], BASE)
                self.assertEqual(row["prior_review_sha256"], hashlib.sha256(prior_review).hexdigest())
                self.assertEqual(row["before_sha256"], hashlib.sha256(old_item["body"].encode()).hexdigest())
                self.assertEqual(row["after_sha256"], body_sha)
                self.assertNotEqual(row["before_sha256"], row["after_sha256"])
                self.assertEqual(item["body"], body_bytes.decode("utf-8"))
                self.assertEqual(review["target_sha256"], body_sha)
                self.assertEqual(review["source_checks"], row["source_checks"])
                self.assertEqual(review["limits"], row["limits"])
                self.assertEqual(review["limits"][0], item["limits"])
                self.assertEqual(manifest[item_id]["sources"], item["source_ids"])
                self.assertEqual({sources[sid]["url"] for sid in item["source_ids"]},
                                 {check["url"] for check in review["source_checks"]})
                self.assertEqual(item["reviewed_at"], "2026-10-26")
                self.assertEqual(item["review_due_at"], "2027-01-31")
                self.assertEqual(row["status"], "ai_source_rechecked_professional_pending")
                for check in review["source_checks"]:
                    self.assertGreaterEqual(len(check["supporting_passage"]), 50)
                    self.assertIn("非逐字引文", check["supporting_passage"])
                    self.assertNotIn(check["claim"], check["supporting_passage"])
                    self.assertTrue(check["retrieval_method"].strip())
                audit.validate_recheck_history(ROOT, row, item)

    def test_statistics_keep_period_units_and_denominator_limits(self):
        evidence = read("localization/ch07-benefits-safety-recheck-20261026.json")
        stats = {row["source_id"]: row for row in evidence["statistics"]}
        training = stats["bli_jobtraining_admin_2024"]
        self.assertEqual(training["period"], "民國113年（2024）")
        self.assertEqual(training["unit"], "人")
        self.assertEqual(training["values"]["all_persons"], 8334)
        self.assertEqual(training["values"]["male_persons"], 3156)
        self.assertEqual(training["values"]["female_persons"], 5178)
        self.assertIsNone(training["denominator"]["validated_matching_denominator"])
        self.assertIn("核准率", training["limitations"])

        monthly = stats["bli_jobtraining_monthly_2026"]
        self.assertEqual(monthly["unit"], "件、新臺幣元")
        self.assertIn("再次核付", monthly["numerator_definition"])
        self.assertIsNone(monthly["denominator"]["validated_matching_denominator"])

        homeless = stats["ch07_homeless_admin_2024"]
        self.assertEqual(homeless["values"]["listed_homeless_persons"], 2991)
        self.assertEqual(homeless["values"]["listed_persons_with_disability"], 625)
        self.assertIsNone(homeless["denominator"]["validated_matching_denominator"])
        body = next(row["body"] for row in validate_runtime()["items"]
                    if row["id"] == "TW-07-021")
        self.assertIn("不能換算個人遇到無處可住的機率", body)
        self.assertIn("不是年度新發生率", homeless["limitations"])

    def test_batch_counts_and_nonpublication_status(self):
        evidence = read("localization/ch07-benefits-safety-recheck-20261026.json")
        source_batch = read("localization/tw-edition/sources/ch07-benefits-safety-recheck-20261026.json")
        runtime = validate_runtime()
        coverage = read("localization/tw-edition/coverage.json")
        report = publication_report()
        self.assertEqual({row[0] for row in source_batch["sources"]}, NEW_SOURCE_IDS)
        self.assertEqual(evidence["base_main_sha"], BASE)
        self.assertEqual(evidence["scope"]["new_core_ids"], [])
        self.assertEqual(evidence["counts_before"]["substantive_rechecks"], 155)
        self.assertEqual(evidence["counts_after"]["substantive_rechecks"], 159)
        self.assertEqual(evidence["counts_before"]["source_registry"], 821)
        self.assertEqual(evidence["counts_before"]["coverage_snapshot_registry_sources"], 820)
        self.assertEqual(evidence["counts_before"]["core_completed"], 278)
        self.assertEqual(evidence["counts_after"]["core_completed"], 278)
        self.assertEqual(evidence["counts_after"]["runtime_sources"], len(runtime["sources"]))
        self.assertEqual(evidence["counts_after"]["source_registry"], coverage["registry_sources"])
        self.assertEqual(coverage["core_reviewed_entries"], report["publication_completed_entries"])
        self.assertFalse(coverage["publication_ready"])
        self.assertFalse(report["publication_ready"])


if __name__ == "__main__":
    unittest.main()

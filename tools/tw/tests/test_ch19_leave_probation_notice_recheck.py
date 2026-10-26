# -*- coding: utf-8 -*-
"""第19章特休、試用期、預告工資及離職原因歷史實質再審。"""
import hashlib
import json
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import retroactive_audit as audit
from review_contract import ROOT, publication_report, validate_runtime

BASE = "e0d5245f98bca06be161f7bbbdd888eac7770b70"
IDS = ("TW-19-007", "TW-19-003", "TW-19-005", "TW-19-002")
NEW_SOURCE_IDS = {
    "mol_special_leave_2025",
    "mol_special_leave_wage_2026",
    "mol_probation_limit_faq_2026",
    "ey_minimum_wage_2027",
    "mol_minimum_wage_2027_notice",
    "mol_notice_pay_2026",
    "mol_separation_certificate_2026",
    "mol_disputes_table_3_14_2024",
}


def read(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


class Ch19LeaveProbationNoticeRecheckTests(unittest.TestCase):
    def test_review_history_and_reader_outputs_are_synchronized(self):
        old_runtime = json.loads(subprocess.check_output(
            ["git", "show", f"{BASE}:localization/tw-edition/runtime.json"], cwd=ROOT))
        prior_sources = {row["id"]: row for row in old_runtime["sources"]}
        runtime = validate_runtime()
        sources = {row["id"]: row for row in runtime["sources"]}
        new_sources = read("localization/tw-edition/sources/ch19-leave-probation-recheck-20261026.json")["sources"]
        new_source_registry = {row[0]: row for row in new_sources}
        items = {row["id"]: row for row in runtime["items"]}
        manifest = {row["id"]: row for row in read("localization/manifest.json")["entries"]}
        register = read("localization/retroactive-review-register-20261019.json")
        rechecks = {row["id"]: row for row in register["substantive_rechecks"]}
        chapter = read("localization/tw-edition/chapters/19.json")
        chapter_entries = {f"TW-19-{row[0]:03}": row for row in chapter["entries"]}

        self.assertEqual(old_runtime["sources"], [row for row in runtime["sources"] if row["id"] in prior_sources])
        # Later batches may append sources to the shared runtime. Keep this
        # historical contract scoped to the IDs introduced by this chapter-19 batch.
        self.assertTrue(NEW_SOURCE_IDS <= set(sources) - set(prior_sources))
        self.assertEqual(new_source_registry["ey_minimum_wage_2027"][2], sources["ey_minimum_wage_2027"]["url"])
        self.assertIn("2026-10-14", new_source_registry["ey_minimum_wage_2027"][3])
        self.assertNotIn("2026-10-01核定", new_source_registry["ey_minimum_wage_2027"][3])

        for item_id in IDS:
            with self.subTest(item_id=item_id):
                item = items[item_id]
                record = rechecks[item_id]
                review = read(f"localization/reviews/{item_id}.json")
                prior_review = subprocess.check_output(
                    ["git", "show", f"{BASE}:localization/reviews/{item_id}.json"], cwd=ROOT)
                body_bytes = (ROOT / item["target_path"]).read_bytes()
                digest = hashlib.sha256(body_bytes).hexdigest()
                self.assertEqual(record["prior_revision"], BASE)
                self.assertEqual(record["prior_review_sha256"], hashlib.sha256(prior_review).hexdigest())
                self.assertEqual(record["before_sha256"], hashlib.sha256(
                    next(row["body"] for row in old_runtime["items"] if row["id"] == item_id).encode()).hexdigest())
                self.assertEqual(record["after_sha256"], digest)
                self.assertEqual(item["body"], body_bytes.decode("utf-8"))
                self.assertEqual(review["target_sha256"], digest)
                self.assertEqual(review["source_checks"], record["source_checks"])
                self.assertEqual(review["limits"], record["limits"])
                self.assertTrue(item["limits"].strip())
                self.assertEqual(manifest[item_id]["sources"], item["source_ids"])
                self.assertEqual(
                    {sources[sid]["url"] for sid in item["source_ids"]},
                    {check["url"] for check in review["source_checks"]},
                )
                self.assertEqual(item["reviewed_at"], "2026-10-26")
                self.assertEqual(item["review_due_at"], "2027-01-31")
                self.assertEqual(record["status"], "ai_source_rechecked_professional_pending")
                for check in review["source_checks"]:
                    self.assertGreaterEqual(len(check["supporting_passage"]), 50)
                    self.assertIn("非逐字引文", check["supporting_passage"])
                    self.assertNotIn(check["claim"], check["supporting_passage"])
                    self.assertTrue(check["retrieval_method"].strip())
                audit.validate_recheck_history(ROOT, record, item)

        for item_id in ("TW-19-002", "TW-19-003", "TW-19-005", "TW-19-007"):
            row = chapter_entries[item_id]
            self.assertEqual(len(row), 8)
            self.assertEqual(type(row[0]), int)
            self.assertTrue(row[5].strip())

    def test_frequency_values_and_limits_are_not_overclaimed(self):
        items = {row["id"]: row for row in validate_runtime()["items"]}
        evidence = read("localization/ch19-leave-probation-notice-recheck-20261026.json")
        stats = {row["source_id"]: row for row in evidence["statistics"]}
        table = stats["mol_disputes_table_3_14_2024"]
        self.assertEqual(table["period"], "2024")
        self.assertEqual(table["values"]["leave_dispute_table_total"], 338)
        self.assertEqual(table["values"]["leave_dispute_workers"], 336)
        self.assertEqual(table["values"]["leave_dispute_worker_organizations"], 2)
        self.assertEqual(table["values"]["contract_dispute_workers"], 2145)
        self.assertEqual(table["values"]["contract_nature_dispute_workers"], 553)
        self.assertEqual(table["values"]["reinstatement_dispute_workers"], 1592)
        self.assertIsNone(table["denominator"]["validated_matching_denominator"])
        self.assertIn("不是特休專項", items["TW-19-002"]["body"])
        self.assertIn("不是違法判決", items["TW-19-002"]["body"])
        self.assertIn("2027-01-01", items["TW-19-003"]["body"])
        self.assertIn("30,900", items["TW-19-003"]["body"])
        self.assertIn("205元", items["TW-19-003"]["body"])
        self.assertNotIn("2026-10-01核定", items["TW-19-003"]["body"])
        self.assertIn("沒有全國試用期約定比例", items["TW-19-003"]["body"])
        self.assertIn("未找到全國統計中單列", items["TW-19-005"]["body"])
        self.assertIn("確定日起15日內返還", items["TW-19-007"]["body"])
        self.assertIn("不能當作被迫簽署的發生率", items["TW-19-007"]["body"])

    def test_progress_source_counts_and_publication_gate(self):
        evidence = read("localization/ch19-leave-probation-notice-recheck-20261026.json")
        coverage = read("localization/tw-edition/coverage.json")
        self.assertEqual(evidence["base_main_sha"], BASE)
        self.assertEqual(evidence["scope"]["new_core_ids"], [])
        self.assertEqual(evidence["counts_before"]["substantive_rechecks"], 151)
        self.assertEqual(evidence["counts_after"]["substantive_rechecks"], 155)
        self.assertEqual(evidence["counts_before"]["core_completed"], 278)
        self.assertEqual(evidence["counts_after"]["core_completed"], 278)
        self.assertEqual(evidence["counts_after"]["runtime_sources"], 740)
        self.assertEqual(evidence["counts_after"]["source_registry"], 821)
        self.assertEqual(evidence["counts_after"]["json_files_checked"], 452)
        self.assertEqual(evidence["counts_after"]["unresolved_source_ids"], 115)
        self.assertEqual(evidence["counts_after"]["unresolved_reference_occurrences"], 306)
        self.assertEqual(coverage["publication_completed_entries"], 278)
        self.assertFalse(coverage["publication_ready"])
        self.assertFalse(publication_report()["publication_ready"])


if __name__ == "__main__":
    unittest.main()

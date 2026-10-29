import hashlib
import json
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from reader_copy_test_support import assert_body_version_matches_review_or_cleanup, assert_reader_limits_match_review_or_cleanup
import retroactive_audit as audit
from review_contract import ROOT, publication_report, validate_runtime

BASE = "2b0264bb53cf62f9e5c5798ff9c4bdf8bcf4c2c7"
IDS = ("TW-07-005", "TW-07-012", "TW-07-019", "TW-07-020")
NEW_SOURCE_IDS = {
    "private_jobseeker_fee_standard",
    "npa_fakejob_victims_2025_q2",
    "cib_fakejob_warning_20260718",
    "mol_unemployment_services_2025",
    "aftercare_protection_act",
    "aftercare_association_home",
    "fsc_insurance_act_current",
    "foi_life_claim_disputes_2025",
    "fcpa_article13_current",
    "foi_dispute_process_current",
}


def read(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def prior_json(path):
    return json.loads(subprocess.check_output(["git", "show", f"{BASE}:{path}"], cwd=ROOT))


class Ch07EmploymentReentryInsuranceRecheckTests(unittest.TestCase):
    def test_sources_review_history_and_reader_artifacts_are_synchronized(self):
        old_runtime = prior_json("localization/tw-edition/runtime.json")
        old_sources = {row["id"]: row for row in old_runtime["sources"]}
        runtime = validate_runtime()
        sources = {row["id"]: row for row in runtime["sources"]}
        self.assertEqual(
            old_runtime["sources"],
            [row for row in runtime["sources"] if row["id"] in old_sources],
        )
        self.assertTrue(NEW_SOURCE_IDS.issubset(set(sources) - set(old_sources)))

        source_rows = read(
            "localization/tw-edition/sources/ch07-employment-reentry-insurance-recheck-20261026.json"
        )["sources"]
        catalog = {row[0]: row for row in source_rows}
        self.assertEqual(NEW_SOURCE_IDS, set(catalog))
        for source_id in NEW_SOURCE_IDS:
            self.assertEqual(catalog[source_id][2], sources[source_id]["url"])
            self.assertEqual(sources[source_id]["accessed_at"], "2026-10-26")

        entries = {row["id"]: row for row in read("localization/manifest.json")["entries"]}
        register = read("localization/retroactive-review-register-20261019.json")
        rechecks = {row["id"]: row for row in register["substantive_rechecks"]}
        evidence = read("localization/ch07-employment-reentry-insurance-recheck-20261026.json")
        evidence_articles = {row["id"]: row for row in evidence["articles"]}
        self.assertTrue(set(IDS).issubset(rechecks))

        for item_id in IDS:
            with self.subTest(item_id=item_id):
                item = next(row for row in runtime["items"] if row["id"] == item_id)
                record = rechecks[item_id]
                review = read(f"localization/reviews/{item_id}.json")
                old_item = next(row for row in old_runtime["items"] if row["id"] == item_id)
                old_review = subprocess.check_output(
                    ["git", "show", f"{BASE}:localization/reviews/{item_id}.json"], cwd=ROOT
                )
                body = (ROOT / item["target_path"]).read_bytes()
                digest = hashlib.sha256(body).hexdigest()

                self.assertEqual(record["prior_revision"], BASE)
                self.assertEqual(record["prior_review_sha256"], hashlib.sha256(old_review).hexdigest())
                self.assertEqual(record["before_sha256"], hashlib.sha256(old_item["body"].encode()).hexdigest())
                assert_body_version_matches_review_or_cleanup(self, item_id, record["after_sha256"], digest)
                self.assertEqual(evidence_articles[item_id]["after_sha256"], record["after_sha256"])
                self.assertNotEqual(old_item["body"], body.decode("utf-8"))
                self.assertEqual(item["body"], body.decode("utf-8"))
                self.assertEqual(review["target_sha256"], digest)
                self.assertEqual(review["source_checks"], record["source_checks"])
                self.assertEqual(review["limits"], record["limits"])
                assert_reader_limits_match_review_or_cleanup(self, item["id"], record["limits"][0])
                self.assertEqual(item["reviewed_at"], "2026-10-26")
                self.assertEqual(item["review_due_at"], "2027-01-31")
                self.assertEqual(record["status"], "ai_source_rechecked_professional_pending")
                self.assertEqual(entries[item_id]["sources"], item["source_ids"])
                self.assertEqual(entries[item_id]["verified_at"], "2026-10-26")
                self.assertEqual(
                    {sources[source_id]["url"] for source_id in item["source_ids"]},
                    {check["url"] for check in review["source_checks"]},
                )
                for check in review["source_checks"]:
                    self.assertGreaterEqual(len(check["supporting_passage"]), 50)
                    self.assertIn("非逐字引文", check["supporting_passage"])
                    self.assertNotIn(check["claim"], check["supporting_passage"])
                    self.assertTrue(check["retrieval_method"].strip())
                audit.validate_recheck_history(ROOT, record, item)

        retired = {
            row["id"]: row
            for item_id in IDS
            for row in rechecks[item_id]["retired_sources"]
        }
        self.assertEqual(set(retired), {"ch07_reentry", "ch07_reentry_choice", "debtcleanup", "ch07_insurance", "jobservice"})
        for source_id, row in retired.items():
            self.assertEqual(sources[source_id], old_sources[source_id])
            self.assertEqual(
                row["prior_source_sha256"],
                hashlib.sha256(json.dumps(old_sources[source_id], ensure_ascii=False, sort_keys=True).encode()).hexdigest(),
            )

    def test_statistics_risk_wording_and_batch_counts(self):
        evidence = read("localization/ch07-employment-reentry-insurance-recheck-20261026.json")
        stats = {row["source_id"]: row for row in evidence["statistics"]}
        fakejob = stats["npa_fakejob_victims_2025_q2"]
        self.assertEqual(fakejob["period"], "2025-04-01至2025-06-30（114年第2季）")
        self.assertEqual(fakejob["numerator"], 1911)
        self.assertEqual(fakejob["denominator"], 54996)
        self.assertEqual(fakejob["value"]["share_percent"], 3.47)
        self.assertIn("不能作個人假求職受害率", fakejob["denominator_note"])
        self.assertIsNone(stats["ch07_cib_fakejob_case_20260907"]["denominator"])

        foi = stats["foi_life_claim_disputes_2025"]
        self.assertEqual(foi["period"], "2025-01-01至2025-12-31")
        self.assertEqual(foi["numerator"], 549)
        self.assertEqual(foi["denominator"], 8238)
        self.assertEqual(foi["value"]["category_share_percent"], 6.66)
        self.assertIn("非所有保單理賠", foi["denominator_note"])

        items = {row["id"]: row for row in validate_runtime()["items"]}
        self.assertIn("549件", items["TW-07-020"]["body"])
        self.assertIn("8,238件", items["TW-07-020"]["body"])
        self.assertIn("6.66%", items["TW-07-020"]["body"])
        self.assertIn("1,911名", items["TW-07-005"]["body"])
        self.assertIn("54,996名", items["TW-07-005"]["body"])
        self.assertIn("3.47%", items["TW-07-005"]["body"])
        self.assertIn("資料未提供求職者、應徵次數或接觸假職缺人數作分母", items["TW-07-005"]["body"])
        self.assertIn("不得把年度法院收案件數、受保護對象類別或單一分會成果當作個人成功率或再犯機率", items["TW-07-019"]["body"])
        self.assertIn("30日內處理", items["TW-07-020"]["body"])
        self.assertIn("60日內", items["TW-07-020"]["body"])

        self.assertEqual(evidence["base_main_sha"], BASE)
        self.assertEqual(evidence["scope"]["new_core_ids"], [])
        self.assertEqual(evidence["counts_before"]["core_completed"], 278)
        self.assertEqual(evidence["counts_after"]["core_completed"], 278)
        self.assertEqual(evidence["counts_before"]["substantive_rechecks"], 174)
        self.assertEqual(evidence["counts_after"]["substantive_rechecks"], 178)
        self.assertEqual(evidence["counts_after"]["runtime_sources"], 782)
        self.assertEqual(evidence["counts_after"]["source_registry"], 863)
        self.assertEqual(evidence["counts_after"]["json_files_checked"], 468)
        self.assertEqual(evidence["counts_after"]["unresolved_source_ids"], 115)
        self.assertEqual(evidence["counts_after"]["unresolved_reference_occurrences"], 306)
        self.assertTrue(evidence["professional_review_pending"])
        self.assertFalse(evidence["publication_ready"])
        self.assertFalse(read("localization/tw-edition/coverage.json")["publication_ready"])
        self.assertFalse(publication_report()["publication_ready"])


if __name__ == "__main__":
    unittest.main()

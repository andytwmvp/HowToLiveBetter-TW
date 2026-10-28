# -*- coding: utf-8 -*-
"""第7章社福、健保及重病費用四篇歷史實質再審。"""
import hashlib
import json
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from reader_copy_test_support import assert_body_version_matches_review_or_cleanup
import retroactive_audit as audit
from review_contract import ROOT, publication_report, validate_runtime

BASE = "9714ed9e20980b3fa3221643003ed8cf6bc81eb9"
IDS = ("TW-07-004", "TW-07-006", "TW-07-009", "TW-07-010")
NEW_SOURCE_IDS = {
    "ch07_homeless_admin_2024",
    "nhi_enrollment_priority",
    "nhi_interruption",
}


def read(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


class Ch07SocialSafetyHealthRecheckTests(unittest.TestCase):
    def test_rechecks_preserve_history_and_sync_all_reader_contracts(self):
        old_runtime = json.loads(subprocess.check_output(
            ["git", "show", f"{BASE}:localization/tw-edition/runtime.json"], cwd=ROOT))
        old_sources = {row["id"]: row for row in old_runtime["sources"]}
        runtime = validate_runtime()
        items = {row["id"]: row for row in runtime["items"]}
        sources = {row["id"]: row for row in runtime["sources"]}
        manifest = {row["id"]: row for row in read("localization/manifest.json")["entries"]}
        records = {row["id"]: row for row in read(
            "localization/retroactive-review-register-20261019.json")["substantive_rechecks"]}

        self.assertEqual(
            old_runtime["sources"],
            [row for row in runtime["sources"] if row["id"] in old_sources],
        )
        self.assertEqual(old_sources["catastrophic"], sources["catastrophic"])
        self.assertTrue(NEW_SOURCE_IDS <= (set(sources) - set(old_sources)))
        for item_id in IDS:
            with self.subTest(item_id=item_id):
                item = items[item_id]
                row = records[item_id]
                review = read(f"localization/reviews/{item_id}.json")
                old_item = next(value for value in old_runtime["items"] if value["id"] == item_id)
                old_review = subprocess.check_output(
                    ["git", "show", f"{BASE}:localization/reviews/{item_id}.json"], cwd=ROOT)
                markdown = (ROOT / item["target_path"]).read_bytes()
                digest = hashlib.sha256(markdown).hexdigest()

                self.assertEqual(row["prior_revision"], BASE)
                self.assertEqual(row["prior_review_sha256"], hashlib.sha256(old_review).hexdigest())
                self.assertEqual(row["before_sha256"],
                                 hashlib.sha256(old_item["body"].encode("utf-8")).hexdigest())
                assert_body_version_matches_review_or_cleanup(self, item_id, row["after_sha256"], digest)
                self.assertNotEqual(row["before_sha256"], row["after_sha256"])
                self.assertEqual(item["body"], markdown.decode("utf-8"))
                self.assertEqual(review["target_sha256"], digest)
                self.assertEqual(review["source_checks"], row["source_checks"])
                self.assertEqual(review["limits"], row["limits"])
                self.assertEqual(manifest[item_id]["sources"], item["source_ids"])
                self.assertEqual(
                    {sources[source_id]["url"] for source_id in item["source_ids"]},
                    {check["url"] for check in review["source_checks"]},
                )
                self.assertEqual(item["reviewed_at"], "2026-10-25")
                self.assertEqual(item["review_due_at"], "2027-01-31")
                self.assertEqual(row["status"], "ai_source_rechecked_professional_pending")
                for check in review["source_checks"]:
                    self.assertGreaterEqual(len(check["supporting_passage"]), 50)
                    self.assertIn("非逐字引文", check["supporting_passage"])
                    self.assertNotIn(check["claim"], check["supporting_passage"])
                    self.assertTrue(check["retrieval_method"].strip())
                audit.validate_recheck_history(ROOT, row, item)

    def test_source_batch_and_progress_snapshot(self):
        source_file = read(
            "localization/tw-edition/sources/ch07-social-safety-health-recheck-20261025.json")
        self.assertEqual({row[0] for row in source_file["sources"]}, NEW_SOURCE_IDS)
        runtime = validate_runtime()
        register = read("localization/retroactive-review-register-20261019.json")
        coverage = read("localization/tw-edition/coverage.json")
        report = publication_report()
        evidence = read("localization/ch07-social-safety-health-recheck-20261025.json")
        self.assertGreaterEqual(len(runtime["sources"]), evidence["counts_after"]["runtime_sources"])
        self.assertGreaterEqual(len(register["substantive_rechecks"]),
                                evidence["counts_after"]["substantive_rechecks"])
        self.assertGreaterEqual(coverage["registry_sources"], evidence["counts_after"]["source_registry"])
        self.assertGreaterEqual(coverage["registry_sources"], len(runtime["sources"]))
        self.assertEqual(coverage["core_reviewed_entries"], report["publication_completed_entries"])
        self.assertGreaterEqual(report["publication_completed_entries"], evidence["counts_after"]["core_completed"])
        self.assertFalse(coverage["publication_ready"])
        self.assertFalse(report["publication_ready"])
        self.assertEqual(evidence["base_main_sha"], BASE)
        self.assertEqual(evidence["scope"]["new_core_ids"], [])
        self.assertEqual(evidence["counts_before"]["substantive_rechecks"], 124)
        self.assertEqual(evidence["counts_after"]["substantive_rechecks"], 128)
        self.assertEqual(evidence["counts_before"]["core_completed"], 278)
        self.assertEqual(evidence["counts_after"]["core_completed"], 278)
        self.assertEqual(evidence["counts_after"]["source_registry"], 761)

    def test_frequency_boundaries_and_corrected_major_illness_source(self):
        items = {row["id"]: row for row in validate_runtime()["items"]}
        homeless = items["TW-07-004"]["body"]
        self.assertIn("113年遊民人口2,991人", homeless)
        self.assertIn("625人為身心障礙者", homeless)
        self.assertIn("沒有可供估算個人暴露率的居住人口分母", homeless)
        self.assertIn("113保護專線", homeless)
        self.assertIn("119", homeless)

        urgent = items["TW-07-006"]["body"]
        self.assertIn("於24小時內安排實地訪視", urgent)
        self.assertIn("核定機關當日核定後起算", urgent)
        self.assertIn("屬預期效益，不是當年度實際受理或核准人數", urgent)

        nhi = items["TW-07-009"]["body"]
        for phrase in ("受僱者由工作單位", "依法可依附配偶或直系血親", "補辦投保後再依程序申請退費", "不推算離職者個人的中斷投保機率"):
            self.assertIn(phrase, nhi)

        major = items["TW-07-010"]["body"]
        self.assertIn("https://www.nhi.gov.tw/ch/cp-6089-0c619-2957-1.html", major)
        self.assertNotIn("https://www.nhi.gov.tw/ch/cp-5185-17079-2744-1.html", major)
        rows = {row["id"]: row for row in read(
            "localization/retroactive-review-register-20261019.json")["substantive_rechecks"]}
        retired = rows["TW-07-010"]["retired_sources"]
        self.assertEqual(retired[0]["id"], "catastrophic")
        self.assertEqual(retired[0]["replacement_ids"], ["rights_major_scope"])
        old_runtime = json.loads(subprocess.check_output(
            ["git", "show", f"{BASE}:localization/tw-edition/runtime.json"], cwd=ROOT))
        old_source = next(source for source in old_runtime["sources"] if source["id"] == "catastrophic")
        old_digest = hashlib.sha256(json.dumps(
            old_source, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()
        self.assertEqual(retired[0]["prior_source_sha256"], old_digest)


if __name__ == "__main__":
    unittest.main()

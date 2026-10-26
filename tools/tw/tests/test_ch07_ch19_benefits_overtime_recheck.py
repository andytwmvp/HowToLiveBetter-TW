# -*- coding: utf-8 -*-
"""第7、19章法扶、社會救助、加班費及資遣費歷史實質再審。"""
import hashlib
import json
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import retroactive_audit as audit
from review_contract import ROOT, publication_report, validate_runtime

BASE = "a090c0121f35dfde3b097666cb1b6c292dbe494a"
IDS = ("TW-07-003", "TW-07-007", "TW-19-001", "TW-19-004")
NEW_SOURCE_IDS = {
    "laf_application_2026",
    "laf_phone_advice_2026",
    "laf_inperson_advice_2026",
    "laf_means_test_2026",
    "mohw_2026_social_assistance_limits",
    "mohw_low_income_2026q2_stats",
    "mohw_middlelow_2026q2_stats",
    "mol_overtime_survey_2025",
    "mol_disputes_yearbook_2024",
}


def read(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


class Ch07Ch19BenefitsOvertimeRecheckTests(unittest.TestCase):
    def test_rechecks_preserve_history_and_sync_reader_contracts(self):
        old_runtime = json.loads(subprocess.check_output(
            ["git", "show", f"{BASE}:localization/tw-edition/runtime.json"], cwd=ROOT))
        old_sources = {row["id"]: row for row in old_runtime["sources"]}
        old_items = {row["id"]: row for row in old_runtime["items"]}
        runtime = validate_runtime()
        current_sources = {row["id"]: row for row in runtime["sources"]}
        items = {row["id"]: row for row in runtime["items"]}
        manifest = {row["id"]: row for row in read("localization/manifest.json")["entries"]}
        records = {row["id"]: row for row in read(
            "localization/retroactive-review-register-20261019.json")["substantive_rechecks"]}
        self.assertEqual(old_runtime["sources"], [row for row in runtime["sources"] if row["id"] in old_sources])
        self.assertTrue(NEW_SOURCE_IDS <= set(current_sources) - set(old_sources))

        for item_id in IDS:
            with self.subTest(item_id=item_id):
                item = items[item_id]
                row = records[item_id]
                review = read(f"localization/reviews/{item_id}.json")
                prior_review = subprocess.check_output(
                    ["git", "show", f"{BASE}:localization/reviews/{item_id}.json"], cwd=ROOT)
                body_bytes = (ROOT / item["target_path"]).read_bytes()
                digest = hashlib.sha256(body_bytes).hexdigest()
                self.assertEqual(row["prior_revision"], BASE)
                self.assertEqual(row["prior_review_sha256"], hashlib.sha256(prior_review).hexdigest())
                self.assertEqual(row["before_sha256"], hashlib.sha256(old_items[item_id]["body"].encode()).hexdigest())
                self.assertEqual(row["after_sha256"], digest)
                self.assertNotEqual(row["before_sha256"], row["after_sha256"])
                self.assertEqual(item["body"], body_bytes.decode("utf-8"))
                self.assertEqual(review["target_sha256"], digest)
                self.assertEqual(review["source_checks"], row["source_checks"])
                self.assertEqual(row["limits"], review["limits"])
                self.assertEqual(review["limits"][0], item["limits"])
                self.assertEqual(manifest[item_id]["sources"], item["source_ids"])
                self.assertEqual(
                    {current_sources[sid]["url"] for sid in item["source_ids"]},
                    {check["url"] for check in review["source_checks"]},
                )
                self.assertEqual(item["reviewed_at"], "2026-10-26")
                self.assertEqual(item["review_due_at"], "2027-01-31")
                self.assertEqual(row["status"], "ai_source_rechecked_professional_pending")
                for check in review["source_checks"]:
                    self.assertGreaterEqual(len(check["supporting_passage"]), 50)
                    self.assertIn("非逐字引文", check["supporting_passage"])
                    self.assertNotIn(check["claim"], check["supporting_passage"])
                    self.assertTrue(check["retrieval_method"].strip())
                audit.validate_recheck_history(ROOT, row, item)

    def test_statistics_keep_population_scope_and_denominator_limits(self):
        items = {row["id"]: row for row in validate_runtime()["items"]}
        evidence = read("localization/ch07-ch19-benefits-overtime-recheck-20261026.json")
        stats = {row["source_id"]: row for row in evidence["statistics"]}
        low = stats["mohw_low_income_2026q2_stats"]
        self.assertEqual(low["period"], "2026年第2季季末")
        self.assertEqual(low["values"]["low_income_households"], 142278)
        self.assertEqual(low["values"]["low_income_persons"], 252349)
        self.assertIsNone(low["denominator"]["validated_matching_denominator"])
        self.assertIn("不一致", low["limitations"])
        self.assertIn("結果不一致", items["TW-07-007"]["body"])
        self.assertIn("91,067戶、228,217人", items["TW-07-007"]["body"])
        self.assertNotIn("1.44%戶", items["TW-07-007"]["body"])

        overtime = stats["mol_overtime_survey_2025"]
        self.assertEqual(overtime["values"]["valid_samples"], 4029)
        self.assertEqual(overtime["values"]["reported_any_overtime_pct"], 36.3)
        self.assertEqual(overtime["values"]["average_overtime_hours_per_month_among_overtime_reporters"], 16.2)
        self.assertEqual(overtime["values"]["always_compensated_overtime_reporters_pct"], 88.1)
        self.assertIsNone(overtime["denominator"]["weighted_numerators"])
        for phrase in ("4,029份有效樣本", "36.3%", "16.2小時", "88.1%", "2,139人", "沒有全體勞工工時或加班暴露分母", "不等於已證明違法"):
            self.assertIn(phrase, items["TW-19-001"]["body"])
        for phrase in ("9,223人", "不是所有離職者", "離職人口與新舊制年資分母", "平均工資", "30日內"):
            self.assertIn(phrase, items["TW-19-004"]["body"])
        for phrase in ("轉2", "轉3", "20分鐘", "預約本身不是展延證明", "沒有可配對的全國"):
            self.assertIn(phrase, items["TW-07-003"]["body"])
        for phrase in ("再依語音提示選一般民眾服務", "補班週六亦提供服務", "非補班週六", "年度臨時停辦請查看官網公告"):
            self.assertIn(phrase, items["TW-07-003"]["body"])

    def test_sources_progress_and_nonpublication_status_are_registered(self):
        batch = read("localization/tw-edition/sources/ch07-ch19-benefits-overtime-recheck-20261026.json")
        self.assertEqual({row[0] for row in batch["sources"]}, NEW_SOURCE_IDS)
        sources = {row["id"]: row for row in validate_runtime()["sources"]}
        for source_id, title, url, supports in batch["sources"]:
            self.assertEqual(sources[source_id]["title"], title)
            self.assertEqual(sources[source_id]["url"], url)
            self.assertEqual(sources[source_id]["supports"], supports)
        evidence = read("localization/ch07-ch19-benefits-overtime-recheck-20261026.json")
        coverage = read("localization/tw-edition/coverage.json")
        self.assertEqual(evidence["base_main_sha"], BASE)
        self.assertEqual(evidence["scope"]["new_core_ids"], [])
        self.assertEqual(evidence["counts_before"]["substantive_rechecks"], 147)
        self.assertEqual(evidence["counts_after"]["substantive_rechecks"], 151)
        self.assertEqual(evidence["counts_before"]["core_completed"], 278)
        self.assertEqual(evidence["counts_after"]["core_completed"], 278)
        self.assertEqual(evidence["counts_after"]["runtime_sources"], 732)
        self.assertEqual(evidence["counts_after"]["source_registry"], 813)
        self.assertEqual(evidence["counts_after"]["json_files_checked"], 450)
        self.assertEqual(coverage["publication_completed_entries"], 278)
        self.assertFalse(coverage["publication_ready"])
        self.assertFalse(publication_report()["publication_ready"])


if __name__ == "__main__":
    unittest.main()

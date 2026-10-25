"""第19章職災給付、失能及薪資申報四篇歷史再審。"""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import retroactive_audit as audit
from review_contract import ROOT

BASE = "646cf6ca0a65d439234ec82d0e9d3c34f25ccd5d"
IDS = ("TW-19-013", "TW-19-014", "TW-19-015", "TW-19-021")
NEW_SOURCE_IDS = {
    "bli_injury_unreported_details_20261025",
    "bli_injury_disability_benefit_20261025",
    "bli_injury_death_benefit_20261025",
    "ch19_lsa_death_disability_compensation_20261025",
    "ch19_lsa_compensation_limitation_20261025",
    "ch19_disaster_insurance_art90_20261025",
    "bli_wage_insurance_reporting_20261025",
    "bli_personal_insurance_pension_query_20261025",
    "nhi_counter_enrollment_record_20261025",
}
EMPLOYMENT_RIGHTS_SOURCE_IDS = {
    "ch19_service_false_info_2026",
    "ch19_service_separation_2026",
    "ch19_contract_faq_2026",
    "ch19_minimum_service_faq",
    "ch19_dispatch_guide_2024",
}


def read(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


class Ch19InsuranceBenefitsRecheckTests(unittest.TestCase):
    def test_rechecks_preserve_original_history_and_sync_current_contracts(self):
        old_runtime = json.loads(subprocess.check_output(
            ["git", "show", BASE + ":localization/tw-edition/runtime.json"], cwd=ROOT))
        old_sources = {s["id"]: s for s in old_runtime["sources"]}
        current_runtime = read("localization/tw-edition/runtime.json")
        current_items = {x["id"]: x for x in current_runtime["items"]}
        current_sources = {s["id"]: s for s in current_runtime["sources"]}
        manifest = {x["id"]: x for x in read("localization/manifest.json")["entries"]}
        register = {x["id"]: x for x in read(
            "localization/retroactive-review-register-20261019.json")["substantive_rechecks"]}

        self.assertEqual(old_runtime["sources"], [s for s in current_runtime["sources"] if s["id"] in old_sources])
        self.assertEqual(
            set(current_sources) - set(old_sources),
            NEW_SOURCE_IDS | EMPLOYMENT_RIGHTS_SOURCE_IDS,
        )
        for item_id in IDS:
            with self.subTest(item_id=item_id):
                item = current_items[item_id]
                row = register[item_id]
                review = read(f"localization/reviews/{item_id}.json")
                old_review = subprocess.check_output(
                    ["git", "show", f"{BASE}:localization/reviews/{item_id}.json"], cwd=ROOT)
                old_item = next(x for x in old_runtime["items"] if x["id"] == item_id)
                current_body = (ROOT / item["target_path"]).read_bytes()
                digest = hashlib.sha256(current_body).hexdigest()

                self.assertEqual(row["prior_revision"], BASE)
                self.assertEqual(row["prior_review_sha256"], hashlib.sha256(old_review).hexdigest())
                self.assertEqual(row["before_sha256"], hashlib.sha256(old_item["body"].encode()).hexdigest())
                self.assertEqual(row["after_sha256"], digest)
                self.assertNotEqual(row["before_sha256"], row["after_sha256"])
                self.assertEqual(item["body"], current_body.decode("utf-8"))
                self.assertEqual(review["target_sha256"], digest)
                self.assertEqual(review["source_checks"], row["source_checks"])
                self.assertEqual(review["limits"], row["limits"])
                self.assertEqual(manifest[item_id]["sources"], item["source_ids"])
                self.assertEqual(
                    {current_sources[sid]["url"] for sid in item["source_ids"]},
                    {check["url"] for check in review["source_checks"]},
                )
                for check in review["source_checks"]:
                    self.assertGreaterEqual(len(check["supporting_passage"]), 50)
                    self.assertIn("非逐字", check["supporting_passage"])
                    self.assertNotIn(check["claim"], check["supporting_passage"])
                    self.assertTrue(check["retrieval_method"].strip())
                audit.validate_recheck_history(ROOT, row, item)

    def test_new_sources_are_registered_once_and_review_is_not_professional_signoff(self):
        source_file = read("localization/tw-edition/sources/ch19-insurance-benefits-recheck-20261025.json")
        self.assertEqual({row[0] for row in source_file["sources"]}, NEW_SOURCE_IDS)
        self.assertEqual(len(source_file["sources"]), 9)
        evidence = read("localization/ch19-insurance-benefits-recheck-20261025.json")
        self.assertEqual(evidence["base_main_sha"], BASE)
        self.assertEqual(evidence["counts_after"]["ai_source_rechecks"], 116)
        self.assertEqual(evidence["counts_after"]["published_items_pending_new_standard_review"], 289)
        self.assertFalse(evidence["coverage_snapshot"]["publication_ready"])
        self.assertIn("專家審閱仍待取得", evidence["professional_review_status"])
        unreported_evidence = next(row for row in evidence["items"] if row["id"] == "TW-19-013")
        self.assertIsInstance(unreported_evidence["changes"], str)

    def test_employer_insurance_offset_and_frequency_denominators_are_accurate(self):
        items = {x["id"]: x for x in read("localization/tw-edition/runtime.json")["items"]}
        death = items["TW-19-015"]["body"]
        self.assertIn("災保法第90條", death)
        self.assertIn("平均工資與平均投保薪資差額", death)
        self.assertIn("雇主已依法投保繳費且保險人核定事故", death)
        self.assertIn("重大職災死亡109人", death)
        self.assertIn("營造業58人", death)
        self.assertIn("沒有工作者或工時分母", death)
        self.assertIn("不能把45個月和保險金直接相加", death)
        unreported = items["TW-19-013"]["body"]
        self.assertIn("按第1級計算", unreported)
        self.assertIn("未申報期間的月投保薪資由保險人按被保險人月薪資總額", unreported)
        self.assertIn("投保單位或被保險人未提具相關薪資資料", unreported)
        self.assertNotIn("雇主和勞工都未提出", unreported)
        self.assertIn("第6條的強制納保", unreported)
        self.assertIn("依《勞動基準法》規定受僱工作的未滿15歲者", unreported)
        disability = items["TW-19-014"]["body"]
        self.assertIn("自得請領日起5年", disability)
        self.assertIn("身心障礙證明與災保永久失能", disability)
        wage = items["TW-19-021"]["body"]
        self.assertIn("調整表一般自送達次月1日生效", wage)
        self.assertIn("勞保局查證後得逕行更正或調整", wage)
        self.assertIn("不能用一般調整申報回溯", wage)
        self.assertIn("應調整之次月1日起生效", wage)


if __name__ == "__main__":
    unittest.main()

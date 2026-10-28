"""2026-10-28地籍、貸款及預售期限歷史實質再審契約。"""
import hashlib
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ci_language_policy import audit_drafts
from retroactive_audit import validate_recheck_history
from review_contract import ROOT, publication_report, validate_runtime


IDS = ("TW-15-006", "TW-15-011", "TW-15-013", "TW-15-014")
NEW_SOURCE_IDS = {
    "ch15_land_registration_rules_20261028",
    "ch15_miaoli_presale_shortfall_20241112",
}
BASE = "f85c55717d5505505d8698ce0239dfc6d2defcd5"


def read(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


class RegistryFinancingPresaleRecheckTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.runtime = validate_runtime()
        cls.items = {item["id"]: item for item in cls.runtime["items"]}
        cls.sources = {source["id"]: source for source in cls.runtime["sources"]}
        cls.manifest = {
            item["id"]: item for item in read("localization/manifest.json")["entries"]
        }
        cls.register = read("localization/retroactive-review-register-20261019.json")
        cls.records = {item["id"]: item for item in cls.register["substantive_rechecks"]}
        cls.batch = read("localization/ch15-registry-financing-presale-recheck-20261028.json")

    def test_articles_sources_reviews_and_historical_hashes_are_synchronized(self):
        self.assertEqual(self.batch["base_main_sha"], BASE)
        for key in IDS:
            with self.subTest(id=key):
                item = self.items[key]
                review = read(f"localization/reviews/{key}.json")
                record = self.records[key]
                body = (ROOT / item["target_path"]).read_text(encoding="utf-8")
                digest = hashlib.sha256(body.encode("utf-8")).hexdigest()
                self.assertEqual(body, item["body"])
                self.assertEqual(review["target_sha256"], digest)
                self.assertEqual(record["after_sha256"], digest)
                self.assertNotEqual(record["before_sha256"], record["after_sha256"])
                self.assertEqual(review["reviewed_at"], "2026-10-28")
                self.assertEqual(review["review_due_at"], "2027-01-31")
                self.assertEqual(item["limits"], review["limits"][0])
                self.assertEqual(record["limits"], review["limits"])
                self.assertEqual(record["source_checks"], review["source_checks"])
                self.assertEqual(
                    {source["url"] for source in review["source_checks"]},
                    {self.sources[source_id]["url"] for source_id in item["source_ids"]},
                )
                self.assertTrue(
                    all(self.sources[source_id]["url"] in body
                        for source_id in item["source_ids"])
                )
                self.assertEqual(
                    self.manifest[key]["sources"],
                    [self.sources[source_id]["url"] for source_id in item["source_ids"]],
                )
                validate_recheck_history(ROOT, record, item)

    def test_source_additions_counts_and_unfinished_publication_state(self):
        catalog = read(
            "localization/tw-edition/sources/ch15-registry-financing-recheck-20261028.json"
        )
        self.assertEqual({row[0] for row in catalog["sources"]}, NEW_SOURCE_IDS)
        self.assertTrue(NEW_SOURCE_IDS.issubset(self.sources))
        self.assertEqual(self.batch["scope"]["new_core_ids"], [])
        before = self.batch["counts_before"]
        after = self.batch["counts_after"]
        self.assertEqual(after["core_reviewed"], before["core_reviewed"])
        self.assertEqual(after["runtime_items"], before["runtime_items"])
        self.assertEqual(after["runtime_sources"], before["runtime_sources"] + 2)
        self.assertEqual(after["registry_sources"], before["registry_sources"] + 2)
        self.assertEqual(after["substantive_rechecks"], before["substantive_rechecks"] + 4)
        self.assertGreaterEqual(len(self.runtime["sources"]), after["runtime_sources"])
        audit = audit_drafts()
        coverage = read("localization/tw-edition/coverage.json")
        self.assertGreaterEqual(audit["json_files_checked"], after["coverage_json_files"])
        self.assertEqual(coverage["json_files_checked"], audit["json_files_checked"])
        self.assertEqual(coverage["registry_sources"], audit["registry_sources"])
        self.assertEqual(coverage["unresolved_source_ids"], audit["unresolved_source_ids"])
        self.assertEqual(coverage["unresolved_reference_occurrences"], audit["unresolved_reference_occurrences"])
        self.assertFalse(self.batch["publication_ready"])
        self.assertFalse(publication_report()["publication_ready"])

    def test_presale_audits_keep_periods_groups_and_denominators_separate(self):
        article = self.items["TW-15-013"]["body"]
        self.assertIn("2026年3至5月查核69個建案", article)
        self.assertIn("地方政府選取的50案有9案", article)
        self.assertIn("750個契約檢核項次中13項不符", article)
        self.assertIn("不是工程實際延誤件數", article)
        self.assertIn("不能和2026年3至5月的抽查樣本直接合併", article)
        current, previous = self.batch["statistics"]["TW-15-013"]
        self.assertEqual(current["period"], "2026-03至2026-05")
        self.assertEqual(current["denominator"], 750)
        self.assertEqual(current["value"]["local_projects"], 50)
        self.assertEqual(current["value"]["noncompliant_projects"], 9)
        self.assertEqual(current["value"]["noncompliant_items"], 13)
        self.assertEqual(current["value"]["official_percentage_rounded"], 1.7)
        self.assertIn("13/750約為1.733%", current["limitations"][-1])
        self.assertIn("非全市場建案", current["denominator_definition"])
        self.assertEqual(previous["period"], "2025-09至2025-12")
        self.assertEqual(previous["value"]["projects"], 72)
        self.assertIsNone(previous["denominator"])
        self.assertIn("不與2026樣本合併", previous["limitations"][0])

    def test_legality_frequency_and_risk_are_separate(self):
        policy = (ROOT / "localization/TAIWAN_REUSE_POLICY.md").read_text(encoding="utf-8")
        self.assertIn("跨領域適配，不限自然環境或安全案例", policy)
        self.assertIn("合法或受規範必須獨立記錄", policy)

        loan = self.items["TW-15-011"]["body"]
        self.assertIn("分母是契約寫明的「預定貸款金額」", loan)
        self.assertIn("差額超過30%時買賣雙方才有該條約定的契約解除權", loan)
        self.assertIn("差額在30%以內若賣方無法提供約定分期", loan)
        self.assertIn("不得少於7年", loan)
        self.assertIn("沒有原承諾年限與條件的相關文件", loan)
        self.assertIn("參照賣方洽定銀行核定的利率及年期", loan)
        self.assertIn("不得以買方違約為由沒收已繳價款", loan)
        self.assertIn("貸款不足不會自動等於無責解除", loan)

        prereg = self.items["TW-15-014"]["body"]
        self.assertIn("預告登記不能排除徵收、法院判決或強制執行", prereg)
        self.assertIn("不以頻率高低替代合法性判斷", prereg)
        self.assertIn("民法第866條", prereg)
        self.assertIn("未找到可比較的全國預告登記件數", prereg)

        deed = self.items["TW-15-006"]["body"]
        self.assertIn("第二類資料", deed)
        self.assertIn("沒有全國一致統計", deed)
        retired = self.records["TW-15-006"]["retired_sources"]
        self.assertEqual(retired[0]["id"], "ch15_records")
        self.assertEqual(retired[0]["replacement_ids"], ["ch15_land_registration_rules_20261028"])


if __name__ == "__main__":
    unittest.main()

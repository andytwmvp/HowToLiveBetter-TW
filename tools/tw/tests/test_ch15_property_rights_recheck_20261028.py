"""2026-10-28房屋交易、租賃與農地使用實質再審契約。"""
import hashlib
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ci_language_policy import audit_drafts
from retroactive_audit import validate_recheck_history
from review_contract import ROOT, publication_report, validate_runtime


IDS = ("TW-15-004", "TW-15-005", "TW-15-009", "TW-15-010")
NEW_SOURCE_IDS = {
    "ch15_agri_farmhouse_law_current_20261028",
    "ch15_agri_development_act_farmhouse_20261028",
    "ch15_presale_current_requirements_20261028",
    "ch15_presale_audit_20260923",
    "ch15_presale_proposed_trust_draft_20260514",
    "ch15_cpc_dispute_portal_20261028",
}


def read(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


class PropertyRightsRecheckTests(unittest.TestCase):
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
        cls.batch = read("localization/ch15-property-rights-recheck-20261028.json")

    def test_articles_reviews_runtime_and_history_are_synchronized(self):
        for key in IDS:
            with self.subTest(id=key):
                item = self.items[key]
                review = read(f"localization/reviews/{key}.json")
                record = self.records[key]
                body = (ROOT / item["target_path"]).read_text(encoding="utf-8")
                digest = hashlib.sha256(body.encode("utf-8")).hexdigest()
                self.assertEqual(body, item["body"])
                self.assertEqual(review["target_sha256"], digest)
                self.assertEqual(item["limits"], review["limits"][0])
                self.assertNotEqual(record["before_sha256"], record["after_sha256"])
                self.assertEqual(record["after_sha256"], digest)
                self.assertEqual(record["limits"], review["limits"])
                self.assertEqual(record["source_checks"], review["source_checks"])
                self.assertEqual(review["review_due_at"], "2027-01-31")
                self.assertEqual(
                    {entry["url"] for entry in review["source_checks"]},
                    {self.sources[source_id]["url"] for source_id in item["source_ids"]},
                )
                self.assertTrue(
                    all("非逐字引文" in entry["supporting_passage"]
                        for entry in review["source_checks"])
                )
                self.assertTrue(
                    all(self.sources[source_id]["url"] in body
                        for source_id in item["source_ids"])
                )
                self.assertEqual(self.manifest[key]["sources"],
                                 [self.sources[sid]["url"] for sid in item["source_ids"]])
                validate_recheck_history(ROOT, record, item)

    def test_taiwan_law_and_legal_status_are_not_reduced_to_frequency(self):
        package = self.items["TW-15-004"]["body"]
        self.assertIn("屋主書面同意", package)
        self.assertIn("三十日內", package)
        self.assertIn("知悉終止租賃契約之次日起五日內", package)
        self.assertIn("營業保證金也不是無上限保險", package)
        self.assertIn("租客／契約分母", package)

        tenancy = self.items["TW-15-005"]["body"]
        self.assertIn("民法第425條", tenancy)
        self.assertIn("超過五年或未定期限", tenancy)
        self.assertIn("民法第866條", tenancy)
        self.assertIn("法院得除去相關權利", tenancy)
        self.assertIn("未找到能統一計算", tenancy)

        farmland = self.items["TW-15-009"]["body"]
        self.assertIn("不是一般購屋流程", farmland)
        self.assertIn("合法建物的住宅或租屋", farmland)
        self.assertIn("0.25公頃", farmland)
        self.assertIn("土地取得與設籍均滿二年", farmland)
        self.assertIn("興建滿五年始得移轉", farmland)
        self.assertIn("集村農舍、離島或法定舊有土地另有規定", farmland)
        self.assertIn("未找到可比較的全國", farmland)

    def test_presale_audit_preserves_sample_and_denominator(self):
        presale = self.items["TW-15-010"]["body"]
        self.assertIn("查核69個建案", presale)
        self.assertIn("地方選案的50案中，9案", presale)
        self.assertIn("750個契約項次，其中13項不符", presale)
        self.assertIn("也不是個人買到問題契約的機率", presale)
        stats = self.batch["statistics"]["TW-15-010"][0]
        self.assertEqual(stats["denominator"], 750)
        self.assertEqual(stats["value"]["local_projects_with_some_noncompliance"], 9)
        self.assertEqual(stats["value"]["noncompliant_checked_items"], 13)
        self.assertEqual(stats["value"]["official_noncompliance_fraction"], 0.017)
        self.assertIn("不是全國預售案、買方", stats["denominator_definition"])
        self.assertEqual(stats["data_type"],
                         "官方行政定型化契約合規抽查；混合銷售排名、地方選案與既往違規業者抽查，不是隨機全市場抽樣")

    def test_sources_counts_and_publication_status(self):
        catalog = read(
            "localization/tw-edition/sources/ch15-property-rights-recheck-20261028.json"
        )
        self.assertEqual({row[0] for row in catalog["sources"]}, NEW_SOURCE_IDS)
        self.assertTrue(NEW_SOURCE_IDS.issubset(self.sources))
        self.assertEqual(self.batch["scope"]["new_core_ids"], [])
        self.assertEqual(self.batch["counts_after"]["core_reviewed"],
                         self.batch["counts_before"]["core_reviewed"])
        self.assertEqual(self.batch["counts_after"]["runtime_sources"],
                         self.batch["counts_before"]["runtime_sources"] + len(NEW_SOURCE_IDS))
        self.assertEqual(self.batch["counts_after"]["registry_sources"],
                         self.batch["counts_before"]["registry_sources"] + len(NEW_SOURCE_IDS))
        self.assertEqual(self.batch["counts_after"]["substantive_rechecks"],
                         self.batch["counts_before"]["substantive_rechecks"] + len(IDS))
        audit = audit_drafts()
        coverage = read("localization/tw-edition/coverage.json")
        # This is a historical batch snapshot; later batches may add evidence
        # JSON and source-catalog rows. The live coverage must match its own audit.
        self.assertGreaterEqual(audit["json_files_checked"],
                                self.batch["counts_after"]["coverage_json_files"])
        self.assertGreaterEqual(audit["registry_sources"],
                                self.batch["counts_after"]["registry_sources"])
        self.assertEqual(coverage["json_files_checked"], audit["json_files_checked"])
        self.assertEqual(coverage["registry_sources"], audit["registry_sources"])
        self.assertEqual(coverage["unresolved_source_ids"], audit["unresolved_source_ids"])
        self.assertEqual(coverage["unresolved_reference_occurrences"], audit["unresolved_reference_occurrences"])
        self.assertFalse(self.batch["publication_ready"])
        self.assertFalse(publication_report()["publication_ready"])

    def test_broad_localization_policy_applies_across_domains(self):
        policy = (ROOT / "localization/TAIWAN_REUSE_POLICY.md").read_text(encoding="utf-8")
        self.assertIn("跨領域適配，不限自然環境或安全案例", policy)
        self.assertIn("任何生活情境", policy)
        self.assertIn("合法或受規範必須獨立記錄", policy)
        self.assertIn("高低頻率", policy)


if __name__ == "__main__":
    unittest.main()

"""2026-10-28住宅交易、房貸與社區管理跨領域歷史實質再審。"""
import hashlib
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from reader_copy_test_support import assert_body_version_matches_review_or_cleanup, assert_reader_limits_match_review_or_cleanup
from ci_language_policy import audit_drafts
from retroactive_audit import validate_recheck_history
from review_contract import ROOT, publication_report, validate_runtime


IDS = ("TW-15-007", "TW-15-012", "TW-15-015", "TW-15-017")
BASE = "94f860d0ea977227c4d0a0c1445c20324a376673"
NEW_SOURCES = {
    "ch15_moi_broker_fee_faq_20261028",
    "ch15_yilan_resale_transaction_safety_20261028",
    "ch15_completed_home_contract_qa_20261028",
    "ch15_moi_completed_contract_20260401",
    "ch15_moi_contract_index_20261028",
    "ch15_fsc_mortgage_cost_guide_20210924",
    "ch15_rental_contract_template_20240708",
    "ch15_ntpc_condo_disputes_2023",
    "ch15_ntpc_condo_mediation_20261028",
}


def read(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


class CrossDomainHousingRecheckTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.runtime = validate_runtime()
        cls.items = {item["id"]: item for item in cls.runtime["items"]}
        cls.sources = {source["id"]: source for source in cls.runtime["sources"]}
        cls.manifest = {
            item["id"]: item for item in read("localization/manifest.json")["entries"]
        }
        cls.register = read("localization/retroactive-review-register-20261019.json")
        cls.records = {
            item["id"]: item for item in cls.register["substantive_rechecks"]
        }
        cls.batch = read("localization/ch15-cross-domain-housing-recheck-20261028.json")

    def test_body_runtime_manifest_review_and_history_are_synchronized(self):
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
                assert_body_version_matches_review_or_cleanup(self, key, record["after_sha256"], digest)
                self.assertNotEqual(record["before_sha256"], record["after_sha256"])
                self.assertEqual(review["reviewed_at"], "2026-10-28")
                self.assertEqual(review["review_due_at"], "2027-01-31")
                assert_reader_limits_match_review_or_cleanup(self, item["id"], review["limits"][0])
                self.assertEqual(record["limits"], review["limits"])
                self.assertEqual(record["source_checks"], review["source_checks"])
                self.assertEqual(record["statistics_assessed"][0]["accessed_at"], "2026-10-28")
                self.assertTrue(record["taiwan_context_assessment"]["independent_of_frequency"])
                self.assertTrue(
                    all(self.sources[source_id]["url"] in body
                        for source_id in item["source_ids"])
                )
                self.assertEqual(
                    self.manifest[key]["sources"],
                    [self.sources[source_id]["url"] for source_id in item["source_ids"]],
                )
                self.assertEqual(
                    {source["url"] for source in review["source_checks"]},
                    {self.sources[source_id]["url"] for source_id in item["source_ids"]},
                )
                validate_recheck_history(ROOT, record, item)

    def test_coverage_and_open_publication_state_match_current_inventory(self):
        audit = audit_drafts()
        coverage = read("localization/tw-edition/coverage.json")
        self.assertEqual(coverage, audit)
        verified = sum(
            entry["status"] == "verified"
            for entry in read("localization/manifest.json")["entries"]
        )
        navigation = sum(item["id"].startswith("TW-NAV-") for item in self.runtime["items"])
        self.assertEqual(coverage["core_reviewed_entries"], verified)
        self.assertEqual(len(self.runtime["items"]), verified + navigation)
        self.assertEqual(len(self.runtime["sources"]), len({source["id"] for source in self.runtime["sources"]}))
        self.assertEqual(
            len(self.register["substantive_rechecks"]),
            len({(row["id"], row["before_sha256"], row["after_sha256"])
                 for row in self.register["substantive_rechecks"]}),
        )
        self.assertFalse(self.batch["publication_ready"])
        self.assertFalse(publication_report()["publication_ready"])

    def test_source_catalog_and_retired_ids_are_auditable(self):
        catalog = read(
            "localization/tw-edition/sources/ch15-cross-domain-housing-recheck-20261028.json"
        )
        self.assertEqual({row[0] for row in catalog["sources"]}, NEW_SOURCES)
        self.assertTrue(NEW_SOURCES.issubset(self.sources))
        self.assertEqual(self.batch["scope"]["new_core_ids"], [])
        for key in IDS:
            with self.subTest(id=key):
                record = self.records[key]
                self.assertTrue(record["previous_review_claims"])
                for retired in record["retired_sources"]:
                    self.assertTrue(retired["reason"])
                    self.assertTrue(retired["replacement_ids"])
                    self.assertEqual(len(retired["prior_source_sha256"]), 64)

    def test_contract_sample_and_local_mediation_counts_keep_their_denominators(self):
        area = self.items["TW-15-012"]["body"]
        self.assertIn("2026年3至5月查核69個建案", area)
        self.assertIn("地方選案組50案中9案", area)
        self.assertIn("750個契約檢核項次中13項不符", area)
        self.assertIn("不是實際面積誤差、建材替換", area)
        current = self.records["TW-15-012"]["statistics_assessed"][0]
        self.assertEqual(current["denominator"], 750)
        self.assertEqual(current["value"]["local_noncompliant_projects"], 9)
        self.assertEqual(current["value"]["local_noncompliant_items"], 13)
        self.assertIn("非隨機", current["data_type"])

        condo = self.items["TW-15-017"]["body"]
        self.assertIn("315件，其中管理費類17件", condo)
        self.assertIn("不是新北市所有社區", condo)
        local = self.records["TW-15-017"]["statistics_assessed"][0]
        self.assertEqual(local["denominator"], 315)
        self.assertEqual(local["value"]["management_fee_cases"], 17)
        self.assertEqual(local["geographic_scope"], "新北市政府調處委員會")
        self.assertIsNone(local["published_at"])
        source = self.sources["ch15_ntpc_condo_disputes_2023"]
        self.assertIsNone(source["published_at"])
        self.assertEqual(local["source_ids"], [source["id"]])

    def test_legal_status_is_separate_from_frequency_and_source_absence(self):
        policy = (ROOT / "localization/TAIWAN_REUSE_POLICY.md").read_text(encoding="utf-8")
        self.assertIn("跨領域適配，不限自然環境或安全案例", policy)
        self.assertIn("合法或受規範必須獨立記錄", policy)
        self.assertIn("列舉不是完整清單", policy)

        # Cross-domain handling also covers explicit legal prohibitions, not
        # only the housing, finance, and environmental examples in this batch.
        organ_trade = self.items["TW-01-035"]
        self.assertIn("器官不可買賣", organ_trade["title"])
        self.assertIn("必須無償提供或取得", organ_trade["body"])
        self.assertIn("器官不可買賣", organ_trade["body"])
        self.assertIn("非法器官交易", organ_trade["body"])
        self.assertTrue(any("L0020024" in self.sources[source_id]["url"]
                            for source_id in organ_trade["source_ids"]))

        resale = self.items["TW-15-007"]["body"]
        self.assertIn("成屋標準買賣契約未納入履約保證機制", resale)
        self.assertIn("五種法定擔保方式", resale)
        self.assertIn("自2026-04-01適用新版", resale)
        self.assertIn("不得超過實際成交價金6%", resale)
        self.assertIn("未找到可配對全國中古屋交易量", resale)
        self.assertIn("presalestandard", self.items["TW-15-007"]["source_ids"])

        refinancing = self.items["TW-15-015"]["body"]
        self.assertIn("這是該個人購屋貸款定型化契約的範圍", refinancing)
        self.assertIn("未找到可連結全臺既有房貸戶", refinancing)

        arrears = self.items["TW-15-017"]["body"]
        self.assertIn("第21條", arrears)
        self.assertIn("逾二期或達相當金額", arrears)
        self.assertIn("不是逾期一次就能自行換鎖", arrears)


if __name__ == "__main__":
    unittest.main()

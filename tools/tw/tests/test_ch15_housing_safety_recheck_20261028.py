"""2026-10-28租屋爭議、防詐與住宅火場安全實質再審契約。"""
import hashlib
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ci_language_policy import audit_drafts
from retroactive_audit import validate_recheck_history
from review_contract import ROOT, publication_report, validate_runtime


IDS = ("TW-15-001", "TW-15-002", "TW-15-003", "TW-15-008")
NEW_SOURCE_IDS = {
    "ch15_tainan_rent_disputes_2025",
    "ch15_laf_rental_legal_aid_202601",
    "ch15_moi_rental_draft_status_20260722",
    "ch15_cib_fake_landlord_keys_20260906",
    "ch15_moi_rental_service_licensing_20260814",
    "ch15_moi_rental_service_directory_20261028",
    "ch15_nfa_residential_fire_stats_2021_2025",
    "ch15_nfa_fire_escape_guidance_20260103",
}


def read(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


class HousingSafetyRecheckTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.runtime = validate_runtime()
        cls.items = {item["id"]: item for item in cls.runtime["items"]}
        cls.sources = {source["id"]: source for source in cls.runtime["sources"]}
        cls.manifest = {item["id"]: item for item in read("localization/manifest.json")["entries"]}
        cls.register = read("localization/retroactive-review-register-20261019.json")
        cls.records = {item["id"]: item for item in cls.register["substantive_rechecks"]}
        cls.batch = read("localization/ch15-housing-safety-recheck-20261028.json")

    def test_articles_reviews_and_runtime_are_synchronized(self):
        for key in IDS:
            with self.subTest(id=key):
                item = self.items[key]
                review = read(f"localization/reviews/{key}.json")
                record = self.records[key]
                body = (ROOT / item["target_path"]).read_text(encoding="utf-8")
                digest = hashlib.sha256(body.encode("utf-8")).hexdigest()
                self.assertEqual(body, item["body"])
                self.assertEqual(review["target_sha256"], digest)
                self.assertNotEqual(record["before_sha256"], record["after_sha256"])
                self.assertEqual(record["after_sha256"], digest)
                self.assertEqual(record["source_checks"], review["source_checks"])
                self.assertEqual(review["review_due_at"], "2027-01-31")
                self.assertEqual({entry["url"] for entry in review["source_checks"]},
                                 {self.sources[source_id]["url"] for source_id in item["source_ids"]})
                self.assertTrue(all("非逐字引文" in entry["supporting_passage"]
                                    for entry in review["source_checks"]))
                self.assertTrue(all(self.sources[source_id]["url"] in body
                                    for source_id in item["source_ids"]))
                validate_recheck_history(ROOT, record, item)

    def test_local_evidence_keeps_scope_and_denominator_limits(self):
        tainan = self.items["TW-15-001"]["body"]
        self.assertIn("押金返還或抵充有39案", tainan)
        self.assertIn("沒有全國租屋戶、契約數", tainan)
        lockout = self.items["TW-15-002"]["body"]
        self.assertIn("不估算租客個人遭遇機率", lockout)
        fraud = self.items["TW-15-003"]["body"]
        self.assertIn("這是單一案件", fraud)
        self.assertIn("現場看屋", fraud)
        licensing = self.sources["ch15_moi_rental_service_licensing_20260814"]["supports"]
        self.assertIn("營業保證金", licensing)
        self.assertIn("所在地同業公會", licensing)
        fire = self.items["TW-15-008"]["body"]
        self.assertIn("25,895件", fire)
        self.assertIn("沒有租屋、分隔套房或住戶暴露分母", fire)
        self.assertIn("濃煙阻斷時不要硬闖", fire)
        self.assertIn("撥119", fire)
        stats = self.batch["statistics"]["TW-15-008"][0]
        self.assertEqual(stats["denominator"], 25895)
        self.assertEqual(stats["value"]["combined_residential_incidents"], 18521)
        self.assertIn("不是建築物數、住宅戶、租屋戶或人口", stats["denominator_definition"])

    def test_source_additions_and_no_new_core_progress(self):
        catalog = read("localization/tw-edition/sources/ch15-housing-safety-recheck-20261028.json")
        self.assertEqual({row[0] for row in catalog["sources"]}, NEW_SOURCE_IDS)
        self.assertTrue(NEW_SOURCE_IDS.issubset(self.sources))
        self.assertEqual(self.batch["new_core_ids"], [])
        self.assertEqual(self.batch["counts_after"]["core_reviewed"], self.batch["counts_before"]["core_reviewed"])
        self.assertEqual(self.batch["counts_after"]["runtime_sources"],
                         self.batch["counts_before"]["runtime_sources"] + len(NEW_SOURCE_IDS))
        self.assertEqual(self.batch["counts_after"]["registry_sources"],
                         self.batch["counts_before"]["registry_sources"] + len(NEW_SOURCE_IDS))
        self.assertEqual(self.batch["counts_after"]["substantive_rechecks"],
                         self.batch["counts_before"]["substantive_rechecks"] + len(IDS))
        self.assertEqual(audit_drafts()["json_files_checked"], self.batch["counts_after"]["coverage_json_files"])
        self.assertFalse(publication_report()["publication_ready"])

    def test_law_status_is_separate_from_frequency(self):
        policy = (ROOT / "localization/TAIWAN_REUSE_POLICY.md").read_text(encoding="utf-8")
        self.assertIn("跨領域適配，不限自然環境或安全案例", policy)
        self.assertIn("不得只用高低頻率描述", policy)
        self.assertIn("合法或受規範必須獨立記錄", policy)
        draft = self.items["TW-15-002"]["body"]
        self.assertIn("草案及政策說明不是已生效法律", draft)
        self.assertIn("須提出兩年內核發的租金補貼核定函影本才受理開案", draft)
        laf = self.sources["ch15_laf_rental_legal_aid_202601"]
        self.assertEqual(laf["published_at"], "2024-08-01")
        self.assertIn("更新日2026-01-02", laf["retrieval_method"])
        laf_check = next(check for check in read("localization/reviews/TW-15-002.json")["source_checks"]
                         if check["url"] == laf["url"])
        self.assertIn("國土管理署或地方政府於二年內核發的租金補貼核定函影本，始受理開案", laf_check["supporting_passage"])
        self.assertFalse(self.batch["publication_ready"])


if __name__ == "__main__":
    unittest.main()

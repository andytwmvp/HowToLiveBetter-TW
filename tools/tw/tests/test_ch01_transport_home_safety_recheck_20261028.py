"""第1章交通、住宅火災與燃氣安全高風險歷史實質再審契約。"""
import hashlib
import json
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ci_language_policy import audit_drafts
from review_contract import ROOT, validate_runtime

BASE = "37756e57425903c75dfa54dd24ee201bf613b6c5"
IDS = ["TW-01-003", "TW-01-004", "TW-01-002", "TW-01-001"]
SOURCE_IDS = {
    "ch01_road_traffic_act31_current",
    "ch01_motc_moto_rider_deaths_2026aug",
    "ch01_fire_services_act_current",
    "ch01_nfa_fire_amendment_effective_202506",
    "ch01_residential_alarm_installation_rule_current",
    "ch01_nfa_home_fire_escape_202601",
    "ch01_gasheater_installer_rule_current",
    "ch01_fair_trade_act25_current",
}


def read(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


class Chapter01TransportHomeSafetyRecheckTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.batch = read("localization/ch01-transport-home-safety-recheck-20261028.json")
        cls.register = read("localization/retroactive-review-register-20261019.json")
        cls.manifest = read("localization/manifest.json")
        cls.runtime = validate_runtime()
        cls.items = {item["id"]: item for item in cls.runtime["items"]}
        cls.sources = {source["id"]: source for source in cls.runtime["sources"]}
        cls.entries = {entry["id"]: entry for entry in cls.manifest["entries"]}
        cls.records = {
            record["id"]: record
            for record in cls.register["substantive_rechecks"]
            if record["id"] in IDS
        }

    def test_batch_counts_match_dynamic_source_inventory(self):
        before = self.batch["counts_before"]
        after = self.batch["counts_after"]
        self.assertEqual(self.batch["base_main_sha"], BASE)
        self.assertEqual((before["substantive_rechecks"], after["substantive_rechecks"]), (252, 256))
        self.assertEqual((before["runtime_sources"], after["runtime_sources"]), (902, 910))
        self.assertEqual((before["source_registry"], after["source_registry"]), (983, 991))
        self.assertEqual((before["json_files_checked"], after["json_files_checked"]), (498, 500))
        self.assertEqual(after["source_registry"], before["source_registry"] + len(SOURCE_IDS))
        self.assertEqual(set(self.batch["scope"]["historical_ids"]), set(IDS))
        self.assertEqual(set(self.batch["sources_added"][i]["id"] for i in range(len(SOURCE_IDS))), SOURCE_IDS)
        self.assertEqual(len(self.records), len(IDS))
        self.assertEqual(len(self.runtime["sources"]), after["runtime_sources"])
        self.assertEqual(audit_drafts(), read("localization/tw-edition/coverage.json"))
        coverage = read("localization/tw-edition/coverage.json")
        self.assertEqual(coverage["registry_sources"], after["source_registry"])
        self.assertEqual(coverage["json_files_checked"], after["json_files_checked"])
        self.assertEqual((coverage["publication_completed_entries"], coverage["publication_total_entries"]), (278, 765))
        self.assertFalse(coverage["publication_ready"])

    def test_all_four_historical_rechecks_sync_hashes_reviews_and_sources(self):
        for key in IDS:
            with self.subTest(key=key):
                item = self.items[key]
                record = self.records[key]
                entry = self.entries[key]
                review = read(f"localization/reviews/{key}.json")
                raw = (ROOT / entry["target_path"]).read_bytes()
                digest = hashlib.sha256(raw).hexdigest()
                self.assertEqual(record["status"], "ai_source_rechecked_professional_pending")
                self.assertEqual(record["reviewed_at"], "2026-10-28")
                self.assertEqual(record["review_due_at"], "2027-01-31")
                self.assertEqual(record["after_sha256"], digest)
                self.assertEqual(review["target_sha256"], digest)
                self.assertEqual(raw.decode("utf-8"), item["body"])
                self.assertEqual(entry["sources"], item["source_ids"])
                self.assertEqual(review["reviewed_at"], record["reviewed_at"])
                self.assertEqual(review["review_due_at"], record["review_due_at"])
                self.assertEqual(review["limits"], record["limits"])
                self.assertEqual(review["source_checks"], record["source_checks"])
                self.assertEqual(
                    {check["url"] for check in review["source_checks"]},
                    {self.sources[source_id]["url"] for source_id in item["source_ids"]},
                )

    def test_content_preserves_taiwan_risk_and_denominator_limits(self):
        body = {key: self.items[key]["body"] for key in IDS}
        self.assertIn("3,000至6,000元", body["TW-01-001"])
        self.assertIn("1,500至3,000元", body["TW-01-001"])
        self.assertIn("1,055人", body["TW-01-002"])
        self.assertNotIn("932人", body["TW-01-002"])
        self.assertIn("機車騎士", body["TW-01-002"])
        self.assertNotIn("安全帽相關死亡數", body["TW-01-002"].split("官方來源及改寫說明")[0])
        self.assertIn("3,171次", body["TW-01-003"])
        self.assertIn("不是全臺房屋戶數", body["TW-01-003"])
        self.assertIn("不要搭電梯", body["TW-01-003"])
        self.assertIn("不能僅因某人是房東或租客，就一概判定由誰負責", body["TW-01-003"])
        self.assertIn("22件事故", body["TW-01-004"])
        self.assertIn("沒有燃氣熱水器使用戶數", body["TW-01-004"])
        self.assertIn("技術士證", body["TW-01-004"])
        self.assertIn("不能因此把所有到府檢查都稱為詐騙", body["TW-01-004"])
        self.assertFalse(self.batch["publication_ready"])
        self.assertTrue(self.batch["professional_review_pending"])

    def test_removed_motorcycle_dashboard_source_is_preserved_with_hash(self):
        old = json.loads(
            subprocess.check_output(
                ["git", "show", BASE + ":localization/tw-edition/runtime.json"],
                cwd=ROOT,
                text=True,
            )
        )
        old_source = next(source for source in old["sources"] if source["id"] == "ch01_motc_moto_rider_deaths_2026july")
        current_source = self.sources[old_source["id"]]
        self.assertEqual(current_source, old_source)
        retirement = self.records["TW-01-002"]["retired_sources"]
        self.assertEqual([row["id"] for row in retirement], [old_source["id"]])
        self.assertEqual(
            retirement[0]["prior_source_sha256"],
            hashlib.sha256(json.dumps(old_source, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest(),
        )
        self.assertIn("ch01_motc_moto_rider_deaths_2026aug", retirement[0]["replacement_ids"])


if __name__ == "__main__":
    unittest.main()

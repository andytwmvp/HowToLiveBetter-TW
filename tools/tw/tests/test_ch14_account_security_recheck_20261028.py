"""Chapter 14 account security and SIM recovery substantive-recheck contract."""
import hashlib
import json
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from reader_copy_test_support import assert_body_version_matches_review_or_cleanup, assert_reader_limits_match_review_or_cleanup
from ci_language_policy import audit_drafts
from retroactive_audit import validate_recheck_history
from review_contract import ROOT, publication_report, validate_runtime

BASE = "2b79c8cf4248c18b8a20c33c7f2eb83ef79276a8"
IDS = ("TW-14-001", "TW-14-002", "TW-14-003", "TW-14-006")
NEW_SOURCE_IDS = {
    "ch14_nist_20261028",
    "ch14_acs_account_security_20260112",
    "ch14_acs_reset_report_202607",
    "ch14_ncc_sim_replacement_20250926",
    "ch14_cib_line_hijack_20260803",
}


def read(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def git_bytes(path):
    return subprocess.check_output(["git", "show", f"{BASE}:{path}"], cwd=ROOT)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


class Chapter14AccountSecurityRecheckTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.batch = read("localization/ch14-account-security-recheck-20261028.json")
        cls.register = read("localization/retroactive-review-register-20261019.json")
        cls.runtime = validate_runtime()
        cls.items = {item["id"]: item for item in cls.runtime["items"]}
        cls.sources = {source["id"]: source for source in cls.runtime["sources"]}
        cls.manifest = {entry["id"]: entry for entry in read("localization/manifest.json")["entries"]}
        cls.rechecks = {row["id"]: row for row in cls.register["substantive_rechecks"]}
        cls.batch_items = {row["id"]: row for row in cls.batch["items"]}
        cls.coverage = read("localization/tw-edition/coverage.json")

    def test_dynamic_progress_and_publication_state(self):
        before, after = self.batch["counts_before"], self.batch["counts_after"]
        self.assertEqual(self.batch["base_main_sha"], BASE)
        self.assertEqual(before["substantive_rechecks"], 260)
        self.assertEqual(after["substantive_rechecks"], before["substantive_rechecks"] + len(IDS))
        self.assertEqual(before["runtime_sources"], 916)
        self.assertEqual(after["runtime_sources"], before["runtime_sources"] + len(NEW_SOURCE_IDS))
        self.assertEqual(before["source_registry"], 997)
        self.assertEqual(after["source_registry"], before["source_registry"] + len(NEW_SOURCE_IDS))
        self.assertEqual(after["json_files_checked"], before["json_files_checked"] + 2)
        self.assertEqual((after["core_completed"], after["core_total"], after["shared_reader_items"]), (278, 765, 289))
        self.assertEqual((after["topics_with_any_content"], after["topics_without_content"]), (498, 267))
        self.assertEqual((after["unresolved_source_ids"], after["unresolved_reference_occurrences"]), (114, 304))
        self.assertFalse(after["publication_ready"])
        self.assertFalse(self.batch["publication_ready"])
        self.assertFalse(publication_report()["publication_ready"])
        self.assertEqual(self.batch["scope"]["new_core_ids"], [])

    def test_body_runtime_manifest_review_and_history_are_synchronized(self):
        self.assertEqual(set(self.batch_items), set(IDS))
        for item_id in IDS:
            with self.subTest(id=item_id):
                item = self.items[item_id]
                manifest = self.manifest[item_id]
                record = self.rechecks[item_id]
                evidence = self.batch_items[item_id]
                review = read(f"localization/reviews/{item_id}.json")
                raw = (ROOT / manifest["target_path"]).read_bytes()
                body_sha = digest(raw)
                self.assertEqual(raw.decode("utf-8"), item["body"])
                self.assertEqual(item["review_status"], "source_checked")
                self.assertEqual(item["reviewed_at"], "2026-10-28")
                self.assertEqual(item["review_due_at"], "2027-01-31")
                self.assertEqual(manifest["verified_at"], "2026-10-28")
                self.assertEqual(manifest["sources"], item["source_ids"])
                self.assertEqual(review["target_sha256"], body_sha)
                assert_body_version_matches_review_or_cleanup(self, item_id, record["after_sha256"], body_sha)
                self.assertEqual(evidence["after_sha256"], record["after_sha256"])
                self.assertNotEqual(record["before_sha256"], body_sha)
                self.assertEqual(record["prior_revision"], BASE)
                self.assertEqual(record["prior_review_kind"], "review_file")
                self.assertEqual(record["prior_review_sha256"], digest(git_bytes(f"localization/reviews/{item_id}.json")))
                self.assertEqual(record["before_sha256"], digest(git_bytes(manifest["target_path"])))
                self.assertEqual(record["source_checks"], review["source_checks"])
                self.assertEqual(record["limits"], review["limits"])
                assert_reader_limits_match_review_or_cleanup(self, item["id"], review["limits"][0])
                self.assertEqual(record["source_ids"], item["source_ids"])
                self.assertEqual(record["retired_sources"], [])
                self.assertEqual(record["previous_source_ids"], evidence["previous_source_ids"])
                self.assertEqual(record["status"], "ai_source_rechecked_professional_pending")
                self.assertTrue(all(check["retrieval_method"] and check["supporting_passage"] for check in review["source_checks"]))
                self.assertEqual(
                    {check["url"] for check in review["source_checks"]},
                    {self.sources[source_id]["url"] for source_id in item["source_ids"]},
                )
                validate_recheck_history(ROOT, record, item)

    def test_new_source_catalog_statistics_and_denominators(self):
        catalog = read("localization/tw-edition/sources/ch14-account-security-recheck-20261028.json")
        self.assertEqual({row[0] for row in catalog["sources"]}, NEW_SOURCE_IDS)
        self.assertTrue(NEW_SOURCE_IDS.issubset(self.sources))
        for row in self.batch["sources_added"]:
            source = self.sources[row["id"]]
            self.assertEqual(source["accessed_at"], "2026-10-28")
            self.assertTrue(source["supports"])
            self.assertTrue(source["retrieval_method"])
        expected_line_cases = {"2025_full_year_LINE_cases": 4033, "2026_january_to_july_LINE_cases": 138}
        line_stat = self.rechecks["TW-14-001"]["statistics_assessed"][0]
        self.assertEqual(line_stat["name"], "刑事警察局LINE盜（冒）用帳號案件數")
        self.assertIn("LINE盜（冒）用帳號案件", line_stat["population"])
        self.assertNotIn("網路銀行", line_stat["population"])
        self.assertEqual(line_stat["value"], expected_line_cases)
        self.assertIn("（件）", line_stat["unit"])
        self.assertIsNone(line_stat["denominator"])
        self.assertIn("活躍帳號", line_stat["denominator_definition"])
        self.assertTrue(line_stat["limitations"])
        self.assertTrue(line_stat["search_queries"])
        self.assertTrue(line_stat["screened_sources"])
        session_stat = self.rechecks["TW-14-006"]["statistics_assessed"][0]
        self.assertIsNone(session_stat["value"])
        self.assertIsNone(session_stat["denominator"])
        self.assertIn("不列入", session_stat["numerator_definition"])
        self.assertIn("LINE", session_stat["screened_sources"][0]["title"])
        for item_id in ("TW-14-002", "TW-14-003"):
            stat = self.rechecks[item_id]["statistics_assessed"][0]
            self.assertIsNone(stat["value"])
            self.assertIsNone(stat["denominator"])
            self.assertTrue(stat["limitations"])
            self.assertIn("資料不足", stat["data_type"])
        self.assertTrue(self.batch["professional_review_pending"])

    def test_taiwan_scenarios_frequency_legal_scope_and_no_overclaim(self):
        bodies = {item_id: self.items[item_id]["body"] for item_id in IDS}
        self.assertIn("LINE單一服務的案件件數", bodies["TW-14-001"])
        self.assertIn("不能換算成個人受害率", bodies["TW-14-001"])
        self.assertIn("驗證碼", bodies["TW-14-001"])
        self.assertIn("至少15個字元", bodies["TW-14-002"])
        self.assertIn("兩者的適用對象不同", bodies["TW-14-002"])
        self.assertIn("不是要求民眾啟用SIM PIN的法定義務", bodies["TW-14-003"])
        self.assertIn("不猜SIM PIN或PUK", bodies["TW-14-003"])
        self.assertIn("關閉「允許自其他裝置登入」", bodies["TW-14-006"])
        self.assertIn("可能仍須另向第三方提出刪除要求", bodies["TW-14-006"])
        self.assertTrue(all(self.rechecks[item_id]["taiwan_context_assessment"]["independent_of_frequency"] for item_id in IDS))
        self.assertTrue(all(self.rechecks[item_id]["reviewer_limit"] for item_id in IDS))
        self.assertFalse(self.coverage["publication_ready"])
        self.assertEqual(self.coverage, audit_drafts())
        self.assertFalse(self.batch["publication_ready"])


if __name__ == "__main__":
    unittest.main()

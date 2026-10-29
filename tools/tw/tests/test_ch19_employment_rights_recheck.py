"""第19章服務證明、契約認定、離職條款及派遣權益歷史再審。"""
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

BASE = "051db57bf41447898ff23286ebea255894814985"
IDS = ("TW-19-017", "TW-19-020", "TW-19-022", "TW-19-024")
NEW_SOURCE_IDS = {
    "ch19_service_false_info_2026",
    "ch19_service_separation_2026",
    "ch19_contract_faq_2026",
    "ch19_minimum_service_faq",
    "ch19_dispatch_guide_2024",
}


def read(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


class Ch19EmploymentRightsRecheckTests(unittest.TestCase):
    def test_rechecks_preserve_history_and_sync_reader_contracts(self):
        old_runtime = json.loads(subprocess.check_output(
            ["git", "show", f"{BASE}:localization/tw-edition/runtime.json"], cwd=ROOT))
        old_sources = {row["id"]: row for row in old_runtime["sources"]}
        runtime = validate_runtime()
        items = {row["id"]: row for row in runtime["items"]}
        sources = {row["id"]: row for row in runtime["sources"]}
        manifest = {row["id"]: row for row in read("localization/manifest.json")["entries"]}
        records = {row["id"]: row for row in read(
            "localization/retroactive-review-register-20261019.json")["substantive_rechecks"]}

        self.assertTrue(NEW_SOURCE_IDS <= (set(sources) - set(old_sources)))
        self.assertEqual(old_runtime["sources"], [row for row in runtime["sources"] if row["id"] in old_sources])
        for item_id in IDS:
            with self.subTest(item_id=item_id):
                item = items[item_id]
                row = records[item_id]
                review = read(f"localization/reviews/{item_id}.json")
                old_item = next(entry for entry in old_runtime["items"] if entry["id"] == item_id)
                old_review = subprocess.check_output(
                    ["git", "show", f"{BASE}:localization/reviews/{item_id}.json"], cwd=ROOT)
                markdown = (ROOT / item["target_path"]).read_bytes()
                body_sha = hashlib.sha256(markdown).hexdigest()

                self.assertEqual(row["prior_revision"], BASE)
                self.assertEqual(row["prior_review_sha256"], hashlib.sha256(old_review).hexdigest())
                self.assertEqual(row["before_sha256"], hashlib.sha256(old_item["body"].encode()).hexdigest())
                assert_body_version_matches_review_or_cleanup(self, item_id, row["after_sha256"], body_sha)
                self.assertNotEqual(row["before_sha256"], row["after_sha256"])
                self.assertEqual(item["body"], markdown.decode("utf-8"))
                self.assertEqual(review["target_sha256"], body_sha)
                self.assertEqual(review["source_checks"], row["source_checks"])
                self.assertEqual(review["limits"], row["limits"])
                self.assertEqual(manifest[item_id]["sources"], item["source_ids"])
                self.assertEqual(
                    {sources[sid]["url"] for sid in item["source_ids"]},
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

    def test_source_batch_and_completion_counts_are_scoped(self):
        batch = read("localization/tw-edition/sources/ch19-employment-rights-recheck-20261025.json")
        self.assertEqual({row[0] for row in batch["sources"]}, NEW_SOURCE_IDS)
        runtime_sources = {row["id"]: row for row in read("localization/tw-edition/runtime.json")["sources"]}
        for source_id, title, url, supports in batch["sources"]:
            self.assertEqual(runtime_sources[source_id]["title"], title)
            self.assertEqual(runtime_sources[source_id]["url"], url)
            self.assertEqual(runtime_sources[source_id]["supports"], supports)

        evidence = read("localization/ch19-employment-rights-recheck-20261025.json")
        self.assertEqual(evidence["base_main_sha"], BASE)
        self.assertEqual(evidence["new_core_ids"], [])
        self.assertEqual(evidence["counts_before"]["core_completed"], 278)
        self.assertEqual(evidence["counts_after"]["core_completed"], 278)
        self.assertEqual(evidence["counts_before"]["substantive_rechecks"], 116)
        self.assertEqual(evidence["counts_after"]["substantive_rechecks"], 120)
        self.assertFalse(evidence["coverage_snapshot"]["publication_ready"])
        self.assertIn("仍待取得", evidence["professional_review_status"])
        self.assertFalse(publication_report()["publication_ready"])

    def test_workplace_rights_keep_taiwan_legal_preconditions_and_deadlines(self):
        items = {row["id"]: row for row in validate_runtime()["items"]}
        certificate = items["TW-19-017"]["body"]
        for phrase in ("5年內", "2年內", "7日內補正", "15日內返還", "原因有爭議"):
            self.assertIn(phrase, certificate)

        contract = items["TW-19-020"]["body"]
        for phrase in ("平台接案", "繼續性的工作", "不要倒填日期", "沒有「未簽紙本契約，從第二個月起一律加發雙倍工資」的通用規則"):
            self.assertIn(phrase, contract)

        noncompete = items["TW-19-022"]["body"]
        for phrase in ("專業技術培訓", "合理補償", "期間最長2年", "每月補償不得低於勞工離職時一個月平均工資的50%", "即使達到50%", "預扣工資"):
            self.assertIn(phrase, noncompete)

        dispatch = items["TW-19-024"]["body"]
        for phrase in ("90日內", "10日內協商", "不得因勞工行使此權利", "依勞基法第27條限期給付", "30日內給付", "第63條之1"):
            self.assertIn(phrase, dispatch)


if __name__ == "__main__":
    unittest.main()

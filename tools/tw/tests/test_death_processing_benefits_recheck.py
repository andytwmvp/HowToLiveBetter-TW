"""第25章死亡程序、遺屬給付及數位帳號四篇歷史再審。"""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from reader_copy_test_support import assert_body_version_matches_review_or_cleanup
import retroactive_audit as audit
from review_contract import ROOT

BASE = "ff066b89ed649dccd8280d81f7134b960f9741d7"
IDS = ("TW-25-002", "TW-25-003", "TW-25-009", "TW-25-010")


def read(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


class DeathProcessingBenefitsRecheckTests(unittest.TestCase):
    def test_each_recheck_preserves_hashes_and_resolves_source_ids(self):
        old_runtime = json.loads(subprocess.check_output(
            ["git", "show", BASE + ":localization/tw-edition/runtime.json"], cwd=ROOT))
        current_runtime = read("localization/tw-edition/runtime.json")
        manifest = {entry["id"]: entry for entry in read("localization/manifest.json")["entries"]}
        register = {row["id"]: row for row in read(
            "localization/retroactive-review-register-20261019.json")["substantive_rechecks"]}
        old_items = {item["id"]: item for item in old_runtime["items"]}
        current_items = {item["id"]: item for item in current_runtime["items"]}
        sources = {source["id"]: source for source in current_runtime["sources"]}

        for item_id in IDS:
            with self.subTest(item_id=item_id):
                old = old_items[item_id]
                current = current_items[item_id]
                record = register[item_id]
                review = read(f"localization/reviews/{item_id}.json")
                body_sha = hashlib.sha256(current["body"].encode("utf-8")).hexdigest()
                markdown = (ROOT / current["target_path"]).read_bytes()
                self.assertEqual(record["prior_revision"], BASE)
                self.assertEqual(record["before_sha256"], hashlib.sha256(old["body"].encode()).hexdigest())
                self.assertNotEqual(record["before_sha256"], body_sha)
                assert_body_version_matches_review_or_cleanup(self, item_id, record["after_sha256"], body_sha)
                self.assertEqual(current["body"], markdown.decode("utf-8"))
                self.assertEqual(review["target_sha256"], hashlib.sha256(markdown).hexdigest())
                self.assertEqual(manifest[item_id]["sources"], current["source_ids"])
                self.assertEqual(
                    {sources[source_id]["url"] for source_id in current["source_ids"]},
                    {check["url"] for check in review["source_checks"]},
                )
                self.assertEqual(record["source_checks"], review["source_checks"])
                self.assertEqual(record["limits"], review["limits"])
                for check in review["source_checks"]:
                    self.assertGreaterEqual(len(check["supporting_passage"]), 50)
                    self.assertIn("非逐字", check["supporting_passage"])
                    self.assertNotIn(check["claim"], check["supporting_passage"])
                audit.validate_recheck_history(ROOT, record, current)

    def test_deadlines_permits_and_contract_rights_are_explicit(self):
        runtime = {item["id"]: item for item in read("localization/tw-edition/runtime.json")["items"]}
        body = {item_id: runtime[item_id]["body"] for item_id in IDS}
        for phrase in ("30日內辦理", "全國任一戶政事務所"):
            self.assertIn(phrase, body["TW-25-002"])
        for phrase in ("第25條", "第42條", "第48、49條", "書面契約", "未載明的費用不得請求"):
            self.assertIn(phrase, body["TW-25-003"])
        for phrase in ("得請領日起5年", "死亡次日起5年", "申請日前5年", "2026年3月27日", "2016年3月26日", "職業災害保險"):
            self.assertIn(phrase, body["TW-25-009"])
        self.assertIn("2025年部分修正標示為尚未生效", body["TW-25-010"])

    def test_retired_labor_faq_is_preserved_and_replaced_only_for_item(self):
        old_runtime = json.loads(subprocess.check_output(
            ["git", "show", BASE + ":localization/tw-edition/runtime.json"], cwd=ROOT))
        current_runtime = read("localization/tw-edition/runtime.json")
        old_source = next(source for source in old_runtime["sources"] if source["id"] == "ch25_bli")
        current_source = next(source for source in current_runtime["sources"] if source["id"] == "ch25_bli")
        self.assertEqual(old_source, current_source)
        retired = next(row for row in read(
            "localization/retroactive-review-register-20261019.json")["substantive_rechecks"]
            if row["id"] == "TW-25-009")["retired_sources"]
        self.assertEqual([row["id"] for row in retired], ["ch25_bli"])
        self.assertEqual(
            ["ch25_bli_death_current", "ch25_laborinsurance_deadline"],
            retired[0]["replacement_ids"],
        )
        item = next(item for item in current_runtime["items"] if item["id"] == "TW-25-009")
        self.assertNotIn("ch25_bli", item["source_ids"])


if __name__ == "__main__":
    unittest.main()

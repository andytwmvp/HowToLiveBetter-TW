"""第19章保險銜接、調職、離職取證與退職所得歷史實質再審。"""
import hashlib
import json
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from reader_copy_test_support import assert_body_version_matches_review_or_cleanup, assert_reader_limits_match_review_or_cleanup
import retroactive_audit as audit
from review_contract import ROOT, publication_report, validate_runtime

BASE = "779b870ba8b915fc561fcbb4cd21b207d99999fb"
IDS = ("TW-19-019", "TW-19-023", "TW-19-008", "TW-19-018")
NEW_SOURCE_IDS = {
    "mol_labor_disputes_table_3_5_2025",
    "nhi_person_enrollment_order_2024",
}


def read(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def prior_json(path):
    return json.loads(subprocess.check_output(["git", "show", f"{BASE}:{path}"], cwd=ROOT))


class Ch19FourRightsRecheckTests(unittest.TestCase):
    def test_review_history_sources_and_reader_outputs_are_synchronized(self):
        old_runtime = prior_json("localization/tw-edition/runtime.json")
        old_manifest = prior_json("localization/manifest.json")
        old_sources = {row["id"]: row for row in old_runtime["sources"]}
        runtime = validate_runtime()
        sources = {row["id"]: row for row in runtime["sources"]}
        self.assertEqual(
            old_runtime["sources"],
            [row for row in runtime["sources"] if row["id"] in old_sources],
        )
        # Keep this historical batch's sources present while allowing later batches to append theirs.
        self.assertTrue(NEW_SOURCE_IDS.issubset(set(sources) - set(old_sources)))

        source_file = read(
            "localization/tw-edition/sources/ch19-four-rights-recheck-20261026.json"
        )["sources"]
        registry = {row[0]: row for row in source_file}
        for source_id in NEW_SOURCE_IDS:
            self.assertEqual(registry[source_id][2], sources[source_id]["url"])
            self.assertIn("2026-10-26", sources[source_id]["accessed_at"])

        items = {row["id"]: row for row in runtime["items"]}
        manifest = {row["id"]: row for row in read("localization/manifest.json")["entries"]}
        old_manifest_rows = {row["id"]: row for row in old_manifest["entries"]}
        register = read("localization/retroactive-review-register-20261019.json")
        rechecks = {row["id"]: row for row in register["substantive_rechecks"]}
        self.assertTrue(set(IDS).issubset(rechecks))

        for item_id in IDS:
            with self.subTest(item_id=item_id):
                item = items[item_id]
                record = rechecks[item_id]
                review = read(f"localization/reviews/{item_id}.json")
                old_review = subprocess.check_output(
                    ["git", "show", f"{BASE}:localization/reviews/{item_id}.json"], cwd=ROOT
                )
                old_item = next(row for row in old_runtime["items"] if row["id"] == item_id)
                body = (ROOT / item["target_path"]).read_bytes()
                digest = hashlib.sha256(body).hexdigest()

                self.assertEqual(record["prior_revision"], BASE)
                self.assertEqual(
                    record["prior_review_sha256"], hashlib.sha256(old_review).hexdigest()
                )
                self.assertEqual(
                    record["before_sha256"],
                    hashlib.sha256(old_item["body"].encode("utf-8")).hexdigest(),
                )
                assert_body_version_matches_review_or_cleanup(self, item_id, record["after_sha256"], digest)
                self.assertNotEqual(old_item["body"], body.decode("utf-8"))
                self.assertEqual(item["body"], body.decode("utf-8"))
                self.assertEqual(review["target_sha256"], digest)
                self.assertEqual(review["source_checks"], record["source_checks"])
                self.assertEqual(review["limits"], record["limits"])
                assert_reader_limits_match_review_or_cleanup(self, item["id"], record["limits"][0])
                self.assertEqual(item["reviewed_at"], "2026-10-26")
                self.assertEqual(item["review_due_at"], record["review_due_at"])
                self.assertEqual(record["status"], "ai_source_rechecked_professional_pending")
                self.assertEqual(
                    {sources[source_id]["url"] for source_id in item["source_ids"]},
                    {check["url"] for check in review["source_checks"]},
                )
                self.assertEqual(manifest[item_id]["verified_at"], "2026-10-26")
                if item["source_ids"] != old_item["source_ids"]:
                    self.assertEqual(manifest[item_id]["sources"], item["source_ids"])
                else:
                    self.assertEqual(
                        manifest[item_id]["sources"], old_manifest_rows[item_id]["sources"]
                    )
                for check in review["source_checks"]:
                    self.assertGreaterEqual(len(check["supporting_passage"]), 50)
                    self.assertIn("非逐字引文", check["supporting_passage"])
                    self.assertNotIn(check["claim"], check["supporting_passage"])
                    self.assertTrue(check["retrieval_method"].strip())
                audit.validate_recheck_history(ROOT, record, item)

        retired = {
            row["id"]: row
            for item_id in IDS
            for row in rechecks[item_id]["retired_sources"]
        }
        self.assertEqual(set(retired), {"retiretax", "nhiact", "nhiunemployed", "labordispute"})
        for source_id, row in retired.items():
            self.assertEqual(sources[source_id], old_sources[source_id])
            self.assertEqual(
                row["prior_source_sha256"],
                hashlib.sha256(
                    json.dumps(old_sources[source_id], ensure_ascii=False, sort_keys=True).encode()
                ).hexdigest(),
            )

    def test_taiwan_frequency_evidence_and_article_corrections(self):
        items = {row["id"]: row for row in validate_runtime()["items"]}
        evidence = read("localization/ch19-four-rights-recheck-20261026.json")
        stats = {row["source_id"]: row for row in evidence["statistics"]}
        table = stats["mol_labor_disputes_table_3_5_2025"]
        self.assertEqual(table["period"], "2025-01-01至2025-12-31（民國114年）")
        self.assertEqual(table["values"]["all_dispute_cases"], 29_714)
        self.assertEqual(table["values"]["cases_handled_by_labor_admin_parentheses"], 10_543)
        self.assertEqual(table["unit"], "件，不是人數、事件全部發生數或個人發生率")
        self.assertIsNone(table["denominator"])

        body_008 = items["TW-19-008"]["body"]
        self.assertIn("保存勞工出勤紀錄五年", body_008)
        self.assertIn("逐日記載至分鐘", body_008)
        self.assertIn("不得拒絕", body_008)
        self.assertIn("未找到臺灣全國統計", body_008)

        body_018 = items["TW-19-018"]["body"]
        for phrase in ("115年度", "206,000", "414,000", "894,000", "2027年", "191,000元不是稅額，而是退職所得的計算額"):
            self.assertIn(phrase, body_018)
        self.assertNotIn("15萬／30萬", body_018)
        self.assertEqual(items["TW-19-018"]["review_due_at"], "2026-12-15")

        body_019 = items["TW-19-019"]["body"]
        self.assertIn("通知的翌日起算", body_019)
        self.assertIn("七日是申報期限，不是可以少算提繳天數", body_019)
        self.assertIn("工會、農會或漁會會員資格", body_019)
        self.assertIn("戶籍所在地鄉、鎮、市、區公所", body_019)
        self.assertIn("不估算轉職後漏保", body_019)

        body_023 = items["TW-19-023"]["body"]
        self.assertIn("29,714件", body_023)
        self.assertIn("不是調職專項", body_023)
        self.assertIn("無法推算調職發生率或個人遭遇機率", body_023)
        self.assertEqual(evidence["counts_before"]["substantive_rechecks"], 165)
        self.assertEqual(evidence["counts_after"]["substantive_rechecks"], 169)

    def test_progress_source_counts_and_publication_gate(self):
        evidence = read("localization/ch19-four-rights-recheck-20261026.json")
        coverage = read("localization/tw-edition/coverage.json")
        self.assertEqual(evidence["base_main_sha"], BASE)
        self.assertEqual(evidence["scope"]["new_core_ids"], [])
        self.assertEqual(evidence["counts_before"]["core_completed"], 278)
        self.assertEqual(evidence["counts_after"]["core_completed"], 278)
        self.assertEqual(evidence["counts_after"]["runtime_sources"], 763)
        self.assertEqual(evidence["counts_after"]["source_registry"], 844)
        self.assertEqual(evidence["counts_after"]["json_files_checked"], 464)
        self.assertEqual(evidence["counts_after"]["unresolved_source_ids"], 115)
        self.assertEqual(evidence["counts_after"]["unresolved_reference_occurrences"], 306)
        self.assertEqual(coverage["publication_completed_entries"], 278)
        self.assertFalse(coverage["publication_ready"])
        self.assertFalse(publication_report()["publication_ready"])


if __name__ == "__main__":
    unittest.main()

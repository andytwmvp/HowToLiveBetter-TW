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

BASE = "25f163aeb6214a31fcf91deea8c0faaf9d1ae384"
IDS = ("TW-07-017", "TW-07-022", "TW-07-023", "TW-07-016", "TW-07-011")
NEW_SOURCE_IDS = {
    "ris_lost_id_faq_2026",
    "ris_id_replacement_fee",
    "nlma_rent_2026_notice",
    "nlma_rent_2027_notice",
    "nlma_rent_app_stats_2026",
    "mohw_emergency_aid_overview_2026",
    "mol_contract_relation_2026",
    "consumer_debt_clearance_act",
    "judicial_consumer_debt_stats_2025",
}


def read(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def prior_json(path):
    return json.loads(
        subprocess.check_output(["git", "show", f"{BASE}:{path}"], cwd=ROOT)
    )


class Ch07BasicRightsRecheckTests(unittest.TestCase):
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
        self.assertTrue(NEW_SOURCE_IDS.issubset(set(sources) - set(old_sources)))

        source_file = read(
            "localization/tw-edition/sources/ch07-basic-rights-recheck-20261026.json"
        )["sources"]
        registry = {row[0]: row for row in source_file}
        self.assertEqual(NEW_SOURCE_IDS, set(registry))
        for source_id in NEW_SOURCE_IDS:
            self.assertEqual(registry[source_id][2], sources[source_id]["url"])
            self.assertIn("2026-10-26", sources[source_id]["accessed_at"])

        items = {row["id"]: row for row in runtime["items"]}
        manifest = {
            row["id"]: row for row in read("localization/manifest.json")["entries"]
        }
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
                    ["git", "show", f"{BASE}:localization/reviews/{item_id}.json"],
                    cwd=ROOT,
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
                self.assertEqual(item["review_due_at"], "2027-01-31")
                self.assertEqual(record["status"], "ai_source_rechecked_professional_pending")
                self.assertEqual(
                    {sources[source_id]["url"] for source_id in item["source_ids"]},
                    {check["url"] for check in review["source_checks"]},
                )
                self.assertEqual(manifest[item_id]["verified_at"], "2026-10-26")
                self.assertEqual(manifest[item_id]["sources"], item["source_ids"])
                self.assertEqual(
                    old_manifest_rows[item_id]["id"], item_id
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
        self.assertEqual(
            set(retired),
            {
                "idloss", "ch07_idfee", "rent2026", "rentbuilding", "supportlines",
                "urgentresidence", "debtcleanup", "ch07_debtlaw",
            },
        )
        for source_id, row in retired.items():
            self.assertEqual(sources[source_id], old_sources[source_id])
            self.assertEqual(
                row["prior_source_sha256"],
                hashlib.sha256(
                    json.dumps(old_sources[source_id], ensure_ascii=False, sort_keys=True).encode()
                ).hexdigest(),
            )

    def test_taiwan_context_frequency_evidence_and_article_corrections(self):
        items = {row["id"]: row for row in validate_runtime()["items"]}
        evidence = read("localization/ch07-basic-rights-recheck-20261026.json")
        stats = {row["source_id"]: row for row in evidence["statistics"]}

        rent = stats["nlma_rent_app_stats_2026"]
        self.assertEqual(rent["period"], "截至2026-05-31（115年度中央擴大租金補貼）")
        self.assertEqual(rent["values"]["applications_households_lower_bound"], 1_000_000)
        self.assertEqual(rent["values"]["approved_households_lower_bound"], 854_000)
        self.assertIsNone(rent["denominator"])

        labor = stats["labor_dispute_stats_2024"]
        self.assertEqual(labor["values"]["all_dispute_cases"], 27_419)
        self.assertEqual(labor["values"]["all_dispute_people_reported"], 38_766)
        self.assertEqual(labor["values"]["wage_arrears_main_category_cases"], 9_669)
        self.assertEqual(labor["values"]["wage_arrears_main_category_cases_2023"], 9_367)
        self.assertIsNone(labor["denominator"])

        debt = stats["judicial_consumer_debt_stats_2025"]
        self.assertEqual(debt["values"]["new_consumer_debt_cases"], 45_720)
        self.assertIsNone(debt["denominator"])
        self.assertIn("差16,671件", debt["numerator_definition"])

        self.assertIn("新證補發後才失效", items["TW-07-011"]["body"])
        self.assertIn("200元", items["TW-07-011"]["body"])
        self.assertIn("2027年1月1日09:00", items["TW-07-016"]["body"])
        self.assertIn("1957福利諮詢專線每天08:00至22:00", items["TW-07-017"]["body"])
        self.assertIn("9,669件", items["TW-07-022"]["body"])
        self.assertNotIn("9,367件", items["TW-07-022"]["body"])
        self.assertIn("45,720件", items["TW-07-023"]["body"])
        self.assertIn("沒有全體負債者或符合條例消費者的母數", items["TW-07-023"]["body"])

        self.assertEqual(evidence["base_main_sha"], BASE)
        self.assertEqual(evidence["scope"]["new_core_ids"], [])
        self.assertEqual(evidence["counts_before"]["core_completed"], 278)
        self.assertEqual(evidence["counts_after"]["core_completed"], 278)
        self.assertEqual(evidence["counts_before"]["substantive_rechecks"], 169)
        self.assertEqual(evidence["counts_after"]["substantive_rechecks"], 174)
        self.assertEqual(evidence["counts_after"]["runtime_sources"], 772)
        self.assertEqual(evidence["counts_after"]["source_registry"], 853)
        self.assertEqual(evidence["counts_after"]["json_files_checked"], 466)
        self.assertEqual(evidence["counts_after"]["unresolved_source_ids"], 115)
        self.assertEqual(evidence["counts_after"]["unresolved_reference_occurrences"], 306)
        self.assertTrue(evidence["professional_review_pending"])
        self.assertFalse(evidence["publication_ready"])

        coverage = read("localization/tw-edition/coverage.json")
        self.assertGreaterEqual(
            coverage["publication_completed_entries"], evidence["counts_after"]["core_completed"]
        )
        self.assertEqual(coverage["publication_ready"], publication_report()["publication_ready"])


if __name__ == "__main__":
    unittest.main()

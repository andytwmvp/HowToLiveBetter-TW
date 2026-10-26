# -*- coding: utf-8 -*-
"""第7、19章失業給付、欠薪與求職詐騙四篇歷史實質再審。"""
import hashlib
import json
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import retroactive_audit as audit
from review_contract import ROOT, publication_report, validate_runtime

BASE = "0149b4a25d9e2f79e92b8367323a36e1664de39d"
IDS = ("TW-07-001", "TW-07-002", "TW-07-015", "TW-19-006")
NEW_SOURCE_IDS = {
    "ch07_unemployment_stats_2025",
    "ch07_jobinsurance_deadlines_2026",
    "labor_dispute_stats_2024",
    "mol_mediation_support_20260903",
    "mol_labor_legal_aid_thresholds_20261002",
    "ch07_cib_fakejob_patterns_20261022",
    "ch07_cib_fakejob_case_20260907",
    "ch07_cib_fakejob_investment_case_20260809",
}


def read(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


class Ch07Ch19EmploymentRecheckTests(unittest.TestCase):
    def test_rechecks_preserve_history_and_sync_reader_contracts(self):
        old_runtime = json.loads(subprocess.check_output(
            ["git", "show", f"{BASE}:localization/tw-edition/runtime.json"], cwd=ROOT))
        old_sources = {row["id"]: row for row in old_runtime["sources"]}
        runtime = validate_runtime()
        current_sources = {row["id"]: row for row in runtime["sources"]}
        items = {row["id"]: row for row in runtime["items"]}
        manifest = {row["id"]: row for row in read("localization/manifest.json")["entries"]}
        records = {row["id"]: row for row in read(
            "localization/retroactive-review-register-20261019.json")["substantive_rechecks"]}
        self.assertEqual(old_runtime["sources"], [row for row in runtime["sources"] if row["id"] in old_sources])
        self.assertTrue(NEW_SOURCE_IDS <= set(current_sources) - set(old_sources))

        for item_id in IDS:
            with self.subTest(item_id=item_id):
                item = items[item_id]
                row = records[item_id]
                review = read(f"localization/reviews/{item_id}.json")
                old_item = next(value for value in old_runtime["items"] if value["id"] == item_id)
                prior_review = subprocess.check_output(
                    ["git", "show", f"{BASE}:localization/reviews/{item_id}.json"], cwd=ROOT)
                body_bytes = (ROOT / item["target_path"]).read_bytes()
                digest = hashlib.sha256(body_bytes).hexdigest()
                self.assertEqual(row["prior_revision"], BASE)
                self.assertEqual(row["prior_review_sha256"], hashlib.sha256(prior_review).hexdigest())
                self.assertEqual(row["before_sha256"], hashlib.sha256(old_item["body"].encode()).hexdigest())
                self.assertEqual(row["after_sha256"], digest)
                self.assertNotEqual(row["before_sha256"], row["after_sha256"])
                self.assertEqual(item["body"], body_bytes.decode("utf-8"))
                self.assertEqual(review["target_sha256"], digest)
                self.assertEqual(review["source_checks"], row["source_checks"])
                self.assertEqual(row["limits"], review["limits"])
                self.assertEqual(review["limits"][0], item["limits"])
                self.assertEqual(manifest[item_id]["sources"], item["source_ids"])
                self.assertEqual(
                    {current_sources[sid]["url"] for sid in item["source_ids"]},
                    {check["url"] for check in review["source_checks"]},
                )
                self.assertEqual(item["reviewed_at"], "2026-10-26")
                self.assertEqual(item["review_due_at"], "2027-01-31")
                self.assertEqual(row["status"], "ai_source_rechecked_professional_pending")
                for check in review["source_checks"]:
                    self.assertGreaterEqual(len(check["supporting_passage"]), 50)
                    self.assertIn("非逐字引文", check["supporting_passage"])
                    self.assertNotIn(check["claim"], check["supporting_passage"])
                    self.assertTrue(check["retrieval_method"].strip())
                audit.validate_recheck_history(ROOT, row, item)

    def test_statistics_and_case_examples_keep_correct_denominators(self):
        items = {row["id"]: row for row in validate_runtime()["items"]}
        unemployment = items["TW-07-001"]["body"]
        for phrase in ("447,304件", "首次認定申請94,892件", "再次認定申請352,412件", "並非不重複的失業者人數", "個人失業機率"):
            self.assertIn(phrase, unemployment)
        wages = items["TW-07-002"]["body"]
        for phrase in ("27,419件", "9,367件", "2023年為9,669件", "沒有全體勞工或欠薪暴露人次分母", "不是不重複勞工人數"):
            self.assertIn(phrase, wages)
        scam = items["TW-07-015"]["body"]
        for phrase in ("11名求職者", "這是一宗偵辦案件", "新臺幣50萬元", "不能據此估算發生率", "撥165諮詢或報案", "撥110"):
            self.assertIn(phrase, scam)
        dismissal = items["TW-19-006"]["body"]
        for phrase in ("仲裁須雙方同意", "第49條", "新臺幣65,000元", "300萬元", "可能依聲請裁定返還"):
            self.assertIn(phrase, dismissal)

    def test_batch_sources_retired_source_progress_and_nonpublication_status(self):
        batch = read("localization/tw-edition/sources/ch07-ch19-employment-recheck-20261026.json")
        self.assertEqual({row[0] for row in batch["sources"]}, NEW_SOURCE_IDS)
        sources = {row["id"]: row for row in validate_runtime()["sources"]}
        for source_id, title, url, supports in batch["sources"]:
            self.assertEqual(sources[source_id]["title"], title)
            self.assertEqual(sources[source_id]["url"], url)
            self.assertEqual(sources[source_id]["supports"], supports)
        evidence = read("localization/ch07-ch19-employment-recheck-20261026.json")
        self.assertEqual(evidence["base_main_sha"], BASE)
        self.assertEqual(evidence["scope"]["new_core_ids"], [])
        self.assertEqual(evidence["counts_before"]["substantive_rechecks"], 143)
        self.assertEqual(evidence["counts_after"]["substantive_rechecks"], 147)
        self.assertEqual(evidence["counts_before"]["core_completed"], 278)
        self.assertEqual(evidence["counts_after"]["core_completed"], 278)
        self.assertEqual(evidence["counts_after"]["runtime_sources"], 723)
        self.assertEqual(evidence["counts_after"]["source_registry"], 804)
        self.assertFalse(evidence["counts_after"]["publication_ready"])
        self.assertFalse(publication_report()["publication_ready"])
        self.assertEqual(evidence["statistics"][0]["denominator"], None)

        retired = read("localization/retroactive-review-register-20261019.json")["substantive_rechecks"]
        retired = next(row for row in retired if row["id"] == "TW-07-015")["retired_sources"][0]
        old_runtime = json.loads(subprocess.check_output(
            ["git", "show", f"{BASE}:localization/tw-edition/runtime.json"], cwd=ROOT))
        old_source = next(row for row in old_runtime["sources"] if row["id"] == "fraud165")
        old_digest = hashlib.sha256(json.dumps(old_source, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
        self.assertEqual(retired["id"], "fraud165")
        self.assertEqual(retired["prior_source_sha256"], old_digest)
        self.assertEqual(sources["fraud165"], old_source)
        self.assertIn("502", retired["reason"])
        self.assertEqual(read("localization/tw-edition/coverage.json")["publication_ready"], False)


if __name__ == "__main__":
    unittest.main()

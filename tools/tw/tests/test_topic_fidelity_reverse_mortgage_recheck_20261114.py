"""臺灣以房養老主題忠實度、證據範圍與歷史契約。"""
import hashlib
import json
import re
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools/tw"))

from ci_language_policy import audit_drafts
from retroactive_audit import validate_recheck_history
from review_contract import publication_report, validate_runtime

BASE = "72a6139a3426f75a8b40f8a5073520bb1a4477aa"
ITEM_ID = "TW-17-006"
BODY_PATH = "locales/zh-TW/book/ch17/TW-17-006.md"
REVIEW_PATH = f"localization/reviews/{ITEM_ID}.json"
REGISTER_PATH = "localization/retroactive-review-register-20261019.json"
BATCH_PATH = "localization/topic-fidelity-reverse-mortgage-recheck-20261114.json"
SOURCE_PATH = "localization/tw-edition/sources/ch17-elder-20261017.json"


def read(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def git_bytes(revision, path):
    return subprocess.check_output(["git", "show", f"{revision}:{path}"], cwd=ROOT)


def sha(data):
    return hashlib.sha256(data).hexdigest()


class ReverseMortgageTopicFidelityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.runtime = validate_runtime()
        cls.item = next(row for row in cls.runtime["items"] if row["id"] == ITEM_ID)
        cls.sources = {row["id"]: row for row in cls.runtime["sources"]}
        cls.manifest = next(row for row in read("localization/manifest.json")["entries"] if row["id"] == ITEM_ID)
        cls.review = read(REVIEW_PATH)
        cls.register = read(REGISTER_PATH)
        cls.record = next(
            row for row in reversed(cls.register["substantive_rechecks"])
            if row["id"] == ITEM_ID and row["reviewed_at"] == "2026-11-15"
        )
        cls.batch = read(BATCH_PATH)

    def test_recheck_is_append_only_and_hash_bound_to_prior_main(self):
        old_body = git_bytes(BASE, BODY_PATH)
        old_review = git_bytes(BASE, REVIEW_PATH)
        body = (ROOT / BODY_PATH).read_bytes()
        old_register = json.loads(git_bytes(BASE, REGISTER_PATH))
        old_runtime = json.loads(git_bytes(BASE, "localization/tw-edition/runtime.json"))

        self.assertEqual(self.batch["baseline_main_sha"], BASE)
        self.assertEqual(self.record["prior_revision"], BASE)
        self.assertEqual(self.record["before_sha256"], sha(old_body))
        self.assertEqual(self.record["previous_body"].encode("utf-8"), old_body)
        self.assertEqual(self.record["prior_review_sha256"], sha(old_review))
        self.assertEqual(self.record["after_sha256"], sha(body))
        self.assertEqual(self.review["target_sha256"], sha(body))
        self.assertEqual(self.review["source_reviewed_sha256"], sha(body))
        self.assertEqual(self.review["review_due_at"], "2027-02-15")
        self.assertEqual(self.manifest["verified_at"], self.review["reviewed_at"])
        self.assertEqual(self.manifest["sources"], self.item["source_ids"])
        self.assertEqual(self.review["source_ids"], self.item["source_ids"])
        self.assertEqual(self.review["source_checks"], self.record["source_checks"])
        self.assertEqual(self.review["limits"], self.record["limits"])
        self.assertEqual(
            self.register["substantive_rechecks"][:len(old_register["substantive_rechecks"])],
            old_register["substantive_rechecks"],
        )
        self.assertEqual(self.batch["items"][0]["before_sha256"], sha(old_body))
        self.assertEqual(self.batch["items"][0]["after_sha256"], sha(body))
        self.assertEqual(self.batch["items"][0]["prior_review_sha256"], sha(old_review))
        validate_recheck_history(ROOT, self.record, self.item)

        current_sources = self.sources
        for source in old_runtime["sources"]:
            self.assertEqual(current_sources[source["id"]], source)
        self.assertFalse(self.review["professional_review"]["obtained"])
        self.assertTrue(self.review["professional_review"]["required"])

    def test_topic_decision_keeps_taiwan_relevance_without_importing_china_product_rules(self):
        body = self.item["body"]
        topic = self.review["topic_fidelity_review"]

        self.assertIn("住房反向抵押養老保險", topic["original_topic"])
        self.assertEqual(topic["decision"], "retain_localized_core_with_scoped_taiwan_case")
        self.assertIn("商業型以房養老", body)
        self.assertIn("一般貸款方案", body)
        self.assertIn("結合信託、保險", body)
        self.assertIn("一般房屋抵押借款，不是銀行商業型以房養老貸款", body)
        self.assertIn("單一案例沒有案件總數或相關暴露母群", body)
        self.assertIn("《金融消費者保護法》第13條", body)
        self.assertIn("30日內適當處理並回覆", body)
        self.assertIn("60日內", body)
        self.assertIn("不代表一定獲賠", body)
        self.assertIn("保留臺灣銀行", topic["reader_content_decision"])
        self.assertIn("不恢復中國", topic["reader_content_decision"])
        self.assertNotIn("銀保監會", body)
        self.assertNotIn("6%、8%、10%", body)
        self.assertNotIn("保險公司才可辦理", body)
        for internal_text in ("本批", "AI輔助", "待專業審閱", "fork", "批次摘要"):
            self.assertNotIn(internal_text, body)

    def test_statistics_keep_units_populations_and_denominators_separate(self):
        stats = self.review["statistics_assessed"]
        land_bank = next(row for row in stats if "土地銀行" in row["topic"])
        police_case = next(row for row in stats if "新北" in row["topic"])
        national_rate = next(row for row in stats if "全國" in row["geographic_scope"])

        self.assertEqual(land_bank["value"]["cumulative_cases"], 2723)
        self.assertEqual(land_bank["period"], "2016年推出至2025-12-31")
        self.assertIn("單一銀行行政業務量", land_bank["data_type"])
        self.assertIsNone(land_bank["denominator"])
        self.assertEqual(police_case["value"]["reported_cases"], 1)
        self.assertIn("年齡未載", police_case["limitations"])
        self.assertIn("不是商業型以房養老貸款", police_case["event_definition"])
        self.assertIsNone(police_case["denominator"])
        self.assertIsNone(national_rate["value"])
        self.assertIsNone(national_rate["numerator"])
        self.assertIsNone(national_rate["denominator"])
        self.assertIn("不以銀行承作件數", national_rate["limitations"])

    def test_body_review_runtime_manifest_and_source_ledger_align(self):
        body_urls = set(re.findall(r"\]\((https://[^)]+)\)", self.item["body"]))
        runtime_urls = {self.sources[source_id]["url"] for source_id in self.item["source_ids"]}
        review_urls = {row["url"] for row in self.review["source_checks"]}
        ledger_rows = read(SOURCE_PATH)["sources"]
        ledger_ids = {row[0] for row in ledger_rows}
        old_runtime = json.loads(git_bytes(BASE, "localization/tw-edition/runtime.json"))
        old_civil = next(row for row in old_runtime["sources"] if row["id"] == "ch17_civil")

        self.assertEqual(body_urls, runtime_urls)
        self.assertEqual(runtime_urls, review_urls)
        self.assertEqual(self.manifest["sources"], self.item["source_ids"])
        self.assertEqual(set(self.item["source_ids"]), set(self.batch["items"][0]["source_ids"]))
        self.assertEqual(set(self.batch["new_source_ids"]), {
            "ch17_mohw_reverse", "ch17_reverse_mortgage_scam_case_20260127"
        })
        self.assertTrue(set(self.batch["new_source_ids"]).issubset(ledger_ids))
        shared_source_ids = set(self.batch["shared_source_ids"])
        self.assertEqual(shared_source_ids, {
            "property_bot", "property_landcount", "ch14_financial_law", "foi_dispute_process_current"
        })
        self.assertTrue(shared_source_ids.issubset(self.sources))
        self.assertTrue(shared_source_ids.isdisjoint(ledger_ids))
        self.assertNotIn("ch17_civil", self.item["source_ids"])
        self.assertEqual(self.sources["ch17_civil"], old_civil)
        self.assertTrue(any(row["id"] == "ch17_reverse_mortgage_scam_case_20260127"
                            and row["published_at"] == "2026-01-27" for row in [self.sources[x] for x in self.item["source_ids"]]))
        for check in self.review["source_checks"]:
            self.assertGreaterEqual(len(check["supporting_passage"]), 50)
            self.assertLessEqual(check["accessed_at"], self.review["reviewed_at"])

    def test_counts_match_baseline_snapshot_and_current_data(self):
        before = self.batch["counts_before"]
        after = self.batch["counts_after"]
        baseline_coverage = json.loads(git_bytes(BASE, "localization/tw-edition/coverage.json"))
        baseline_runtime = json.loads(git_bytes(BASE, "localization/tw-edition/runtime.json"))
        baseline_manifest = json.loads(git_bytes(BASE, "localization/manifest.json"))
        baseline_register = json.loads(git_bytes(BASE, REGISTER_PATH))

        self.assertEqual(before["manifest_entries"], len(baseline_manifest["entries"]))
        self.assertEqual(before["verified_core_entries"], baseline_coverage["core_reviewed_entries"])
        self.assertEqual(before["runtime_items"], len(baseline_runtime["items"]))
        self.assertEqual(before["runtime_sources"], len(baseline_runtime["sources"]))
        self.assertEqual(before["source_registry"], baseline_coverage["registry_sources"])
        self.assertEqual(before["review_rechecks"], len(baseline_register["substantive_rechecks"]))
        self.assertEqual(before["coverage_json_files"], baseline_coverage["json_files_checked"])
        self.assertEqual(before["unresolved_source_ids"], len(baseline_coverage["unresolved_source_ids"]))
        self.assertEqual(before["unresolved_reference_occurrences"], baseline_coverage["unresolved_reference_occurrences"])
        self.assertEqual(before["publication_completed_entries"], baseline_coverage["publication_completed_entries"])
        self.assertEqual(before["publication_ready"], baseline_coverage["publication_ready"])

        audit = audit_drafts()
        publication = publication_report()
        live_coverage = read("localization/tw-edition/coverage.json")
        actual = {
            "manifest_entries": len(read("localization/manifest.json")["entries"]),
            "verified_core_entries": live_coverage["core_reviewed_entries"],
            "runtime_items": len(self.runtime["items"]),
            "runtime_sources": len(self.runtime["sources"]),
            "source_registry": audit["registry_sources"],
            "review_rechecks": len(self.register["substantive_rechecks"]),
            "coverage_json_files": audit["json_files_checked"],
            "unresolved_source_ids": len(audit["unresolved_source_ids"]),
            "unresolved_reference_occurrences": sum(audit["unresolved_source_ids"].values()),
            "publication_completed_entries": publication["publication_completed_entries"],
            "publication_ready": publication["publication_ready"],
        }
        self.assertEqual(after, actual)
        self.assertFalse(after["publication_ready"])


if __name__ == "__main__":
    unittest.main()

"""逐題保留臺灣相關的長者照護預付款與投資風險內容。"""
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

BASE = "c46443b55942139d0067e2011d2f004fad1e44eb"
ITEM_ID = "TW-17-005"
BODY_PATH = "locales/zh-TW/book/ch17/TW-17-005.md"
REVIEW_PATH = f"localization/reviews/{ITEM_ID}.json"
REGISTER_PATH = "localization/retroactive-review-register-20261019.json"
BATCH_PATH = "localization/topic-fidelity-eldercare-prepayment-20261114.json"
SOURCE_PATH = "localization/tw-edition/sources/topic-fidelity-eldercare-prepayment-20261114.json"
SOURCE_ID = "ch17_fake_eldercare_project_investment_20260315"
SOURCE_URL = "https://www.pbs.npa.gov.tw/ch/app/data/view?id=18740&module=wg183&serno=4b8d83e5-53dd-4382-b927-a01d5793eb05"


def read(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def git_bytes(revision, path):
    return subprocess.check_output(["git", "show", f"{revision}:{path}"], cwd=ROOT)


def sha(data):
    return hashlib.sha256(data).hexdigest()


class EldercareTopicFidelityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.runtime = validate_runtime()
        cls.item = next(x for x in cls.runtime["items"] if x["id"] == ITEM_ID)
        cls.sources = {x["id"]: x for x in cls.runtime["sources"]}
        cls.manifest = next(x for x in read("localization/manifest.json")["entries"] if x["id"] == ITEM_ID)
        cls.review = read(REVIEW_PATH)
        cls.register = read(REGISTER_PATH)
        cls.record = next(
            x for x in reversed(cls.register["substantive_rechecks"])
            if x["id"] == ITEM_ID and x["reviewed_at"] == "2026-11-14"
        )
        cls.batch = read(BATCH_PATH)

    def test_recheck_is_append_only_and_hash_bound(self):
        old_body = git_bytes(BASE, BODY_PATH)
        old_review = git_bytes(BASE, REVIEW_PATH)
        body = (ROOT / BODY_PATH).read_bytes()

        self.assertEqual(self.batch["baseline_main_sha"], BASE)
        self.assertEqual(self.record["prior_revision"], BASE)
        self.assertEqual(self.record["before_sha256"], sha(old_body))
        self.assertEqual(self.record["previous_body"].encode("utf-8"), old_body)
        self.assertEqual(self.record["prior_review_sha256"], sha(old_review))
        self.assertNotEqual(self.record["before_sha256"], self.record["after_sha256"])
        self.assertEqual(self.record["after_sha256"], sha(body))
        self.assertEqual(self.review["target_sha256"], sha(body))
        self.assertEqual(self.review["source_reviewed_sha256"], sha(body))
        self.assertEqual(self.manifest["verified_at"], self.review["reviewed_at"])
        self.assertEqual(self.manifest["sources"], self.item["source_ids"])
        self.assertEqual(self.review["source_ids"], self.item["source_ids"])
        self.assertEqual(self.review["source_checks"], self.record["source_checks"])
        self.assertEqual(self.review["limits"], self.record["limits"])
        self.assertEqual(self.batch["items"][0]["review_sha256"], sha((ROOT / REVIEW_PATH).read_bytes()))
        self.assertFalse(self.review["professional_review"]["obtained"])
        validate_recheck_history(ROOT, self.record, self.item)

    def test_taiwan_case_is_bounded_and_not_used_as_a_rate(self):
        body = self.item["body"]
        topic = self.review["topic_fidelity_review"]
        case = self.review["statistics_assessed"][0]

        self.assertEqual(topic["decision"], "retain_localized_core_with_scoped_taiwan_case")
        self.assertIn("和付費購買住宿服務是不同交易", body)
        self.assertIn("單一假投資案例", body)
        self.assertIn("不能推算個人受騙機率", body)
        self.assertIn("報導沒有說明當事人年齡", case["limitations"])
        self.assertEqual(case["value"]["reported_cases"], 1)
        self.assertIsNone(case["denominator"])
        self.assertIsNone(self.review["statistics_assessed"][1]["value"])
        self.assertIsNone(self.review["statistics_assessed"][1]["denominator"])

    def test_china_only_legal_claims_are_not_restored(self):
        body = self.item["body"]
        topic = self.review["topic_fidelity_review"]

        self.assertIn("《銀行法》第5-1條", body)
        self.assertIn("不是每項預付款、服務契約或投資約定都違法", body)
        self.assertIn("不恢復中國法條", topic["reader_content_decision"])
        self.assertNotIn("防範和處置非法集資條例", body)
        self.assertIn("不能用其案件數推估臺灣發生率", topic["reason"])

    def test_sources_and_runtime_exports_match(self):
        body = self.item["body"]
        body_urls = set(re.findall(r"\]\((https://[^)]+)\)", body))
        runtime_urls = {self.sources[key]["url"] for key in self.item["source_ids"]}
        review_urls = {x["url"] for x in self.review["source_checks"]}
        new_source = self.sources[SOURCE_ID]
        ledger = read(SOURCE_PATH)["sources"]

        self.assertLessEqual(body_urls, runtime_urls)
        self.assertEqual(runtime_urls, review_urls)
        self.assertEqual(new_source["url"], SOURCE_URL)
        self.assertEqual(new_source["published_at"], "2026-03-15")
        self.assertIn(SOURCE_ID, self.batch["new_source_ids"])
        self.assertEqual(ledger[0][0], SOURCE_ID)
        self.assertIn("未說明該女子年齡", new_source["supports"])

    def test_counts_reflect_live_data_without_claiming_publication_ready(self):
        counts = self.batch["counts_after"]
        audit = audit_drafts()
        publication = publication_report()
        unresolved = audit["unresolved_source_ids"]

        self.assertEqual(counts["manifest_entries"], len(read("localization/manifest.json")["entries"]))
        self.assertEqual(counts["runtime_items"], len(self.runtime["items"]))
        self.assertEqual(counts["runtime_sources"], len(self.runtime["sources"]))
        self.assertEqual(counts["source_registry"], audit["registry_sources"])
        self.assertEqual(counts["review_rechecks"], len(self.register["substantive_rechecks"]))
        self.assertEqual(counts["coverage_json_files"], audit["json_files_checked"])
        self.assertEqual(counts["unresolved_source_ids"], len(unresolved))
        self.assertEqual(counts["unresolved_reference_occurrences"], sum(unresolved.values()))
        self.assertEqual(counts["publication_completed_entries"], publication["publication_completed_entries"])
        self.assertFalse(counts["publication_ready"])


if __name__ == "__main__":
    unittest.main()

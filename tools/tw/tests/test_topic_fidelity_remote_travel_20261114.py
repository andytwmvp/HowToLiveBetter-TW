"""第13章偏遠地區迷途條目的逐題主題保真度與旅外範圍驗證。"""
import hashlib
import json
import re
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools/tw"))

from retroactive_audit import validate_recheck_history
from review_contract import validate_runtime
from body_renderer import body_blocks


BASE = "f8793d7013577bc6c3a507681fbb3a0bf82ef3e4"
ITEM_ID = "TW-13-027"
BODY_PATH = "locales/zh-TW/book/ch13/TW-13-027.md"
REVIEW_PATH = f"localization/reviews/{ITEM_ID}.json"
REGISTER_PATH = "localization/retroactive-review-register-20261019.json"
BATCH_PATH = "localization/topic-fidelity-remote-travel-20261114.json"
SOURCE_PATH = "localization/tw-edition/sources/topic-fidelity-remote-travel-20261114.json"
SOURCE_ID = "ch13_deathvalley_nps_incident_20260821"


def read(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def git_bytes(revision, path):
    return subprocess.check_output(["git", "show", f"{revision}:{path}"], cwd=ROOT)


def sha(data):
    return hashlib.sha256(data).hexdigest()


class RemoteTravelTopicFidelityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.runtime = validate_runtime()
        cls.items = {item["id"]: item for item in cls.runtime["items"]}
        cls.sources = {source["id"]: source for source in cls.runtime["sources"]}
        cls.manifest = {
            item["id"]: item for item in read("localization/manifest.json")["entries"]
        }
        cls.review = read(REVIEW_PATH)
        cls.register = read(REGISTER_PATH)
        cls.batch = read(BATCH_PATH)
        cls.item = cls.items[ITEM_ID]
        cls.entry = cls.manifest[ITEM_ID]
        cls.record = next(
            row for row in reversed(cls.register["substantive_rechecks"])
            if row["id"] == ITEM_ID and row["reviewed_at"] == "2026-11-14"
        )

    def test_recheck_is_append_only_hash_bound_and_source_complete(self):
        prior_body = git_bytes(BASE, BODY_PATH)
        prior_review = git_bytes(BASE, REVIEW_PATH)
        current_body = (ROOT / BODY_PATH).read_bytes()
        body_sha = sha(current_body)

        self.assertEqual(self.batch["baseline_main_sha"], BASE)
        self.assertEqual(self.record["prior_revision"], BASE)
        self.assertEqual(self.record["before_sha256"], sha(prior_body))
        self.assertEqual(self.record["previous_body"], prior_body.decode("utf-8"))
        self.assertEqual(self.record["prior_review_sha256"], sha(prior_review))
        self.assertEqual(self.record["after_sha256"], body_sha)
        self.assertEqual(self.review["target_sha256"], body_sha)
        self.assertEqual(self.review["source_reviewed_sha256"], body_sha)
        self.assertEqual(self.batch["items"][0]["review_sha256"], sha((ROOT / REVIEW_PATH).read_bytes()))
        self.assertEqual(self.entry["verified_at"], self.review["reviewed_at"])
        self.assertEqual(self.entry["sources"], self.item["source_ids"])
        self.assertEqual(self.review["source_ids"], self.item["source_ids"])
        self.assertEqual(self.record["source_checks"], self.review["source_checks"])
        self.assertEqual(self.record["statistics_assessed"], self.review["statistics_assessed"])
        self.assertFalse(self.review["professional_review"]["obtained"])
        self.assertEqual(self.review["review_due_at"], "2027-02-14")
        validate_recheck_history(ROOT, self.record, self.item)

        body = current_body.decode("utf-8")
        body_urls = set(re.findall(r"\]\((https://[^)]+)\)", body))
        runtime_urls = {self.sources[source_id]["url"] for source_id in self.item["source_ids"]}
        checked_urls = {check["url"] for check in self.review["source_checks"]}
        self.assertEqual(body_urls, runtime_urls)
        self.assertEqual(checked_urls, runtime_urls)
        self.assertIn(SOURCE_ID, self.batch["new_source_ids"])
        self.assertEqual(read(SOURCE_PATH)["sources"][0][0], SOURCE_ID)

    def test_taiwan_first_guidance_and_bounded_travel_context(self):
        body = self.item["body"]
        self.assertLess(body.index("撥119"), body.index("旅外沙漠或偏遠道路的提醒"))
        for phrase in (
            "只適用於行程確實會到沙漠或偏遠道路的人",
            "美國死亡谷國家公園管理局2026年8月通報",
            "這是死亡谷的個案及當地建議",
            "目前沒有可估算臺灣旅客在沙漠或偏遠道路受困機率的可比統計",
            "依現場狀況與指示行動",
            "不是CSFB型號",
        ):
            self.assertIn(phrase, body)
        overseas_section = body.split("## 旅外沙漠或偏遠道路的提醒", 1)[1]
        self.assertNotIn("撥119", overseas_section)
        self.assertNotIn("每人每天4公升", body)
        self.assertNotIn("三聲短", body)
        self.assertIn("旅外聯絡方式另見第21章", body)

    def test_topic_decision_distinguishes_relevance_from_bulk_restoration(self):
        topic = self.review["topic_fidelity_review"]
        self.assertEqual(sum(block["tag"] == "h3" for block in body_blocks(self.item)), 6)
        self.assertEqual(topic["decision"], "retain_bounded_overseas_travel_safety_content")
        self.assertIn("不整篇恢復外地沙漠程序", topic["reader_content_decision"])
        self.assertIn("臺灣日常山域需求", topic["reason"])
        self.assertIsNone(self.review["statistics_assessed"][-1]["value"])
        self.assertIsNone(self.review["statistics_assessed"][-1]["denominator"])
        policy = (ROOT / "localization/TAIWAN_REUSE_POLICY.md").read_text(encoding="utf-8")
        self.assertIn("不得把所有外地題目一律抓回", policy)
        self.assertIn("不設單一分數或「海外研究一律收錄」規則", policy)

    def test_progress_snapshot_is_bound_to_base_and_current_artifacts(self):
        coverage = read("localization/tw-edition/coverage.json")
        later_batch = read("localization/topic-fidelity-eldercare-prepayment-20261114.json")
        self.assertEqual(self.batch["counts_before"]["runtime_sources"], 1276)
        self.assertEqual(self.batch["counts_before"]["review_rechecks"], 387)
        self.assertEqual(self.batch["counts_after"]["runtime_sources"], later_batch["counts_before"]["runtime_sources"])
        self.assertEqual(self.batch["counts_after"]["review_rechecks"], later_batch["counts_before"]["review_rechecks"])
        self.assertEqual(self.batch["counts_after"]["coverage_json_files"], later_batch["counts_before"]["coverage_json_files"])
        self.assertEqual(self.batch["counts_after"]["registry_sources"], later_batch["counts_before"]["source_registry"])
        self.assertEqual(later_batch["counts_after"]["runtime_sources"], len(self.runtime["sources"]))
        self.assertEqual(later_batch["counts_after"]["review_rechecks"], len(self.register["substantive_rechecks"]))
        self.assertEqual(later_batch["counts_after"]["coverage_json_files"], coverage["json_files_checked"])
        self.assertEqual(later_batch["counts_after"]["source_registry"], coverage["registry_sources"])
        self.assertEqual(
            later_batch["counts_after"]["runtime_sources"],
            later_batch["counts_before"]["runtime_sources"] + len(later_batch["new_source_ids"]),
        )
        self.assertFalse(coverage["publication_ready"])


if __name__ == "__main__":
    unittest.main()

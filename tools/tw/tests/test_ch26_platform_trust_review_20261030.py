"""第26章平台信任、性影像與著作權四篇歷史再審契約。"""
import hashlib
import json
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from reader_copy_test_support import (
    assert_body_version_matches_review_or_cleanup,
    assert_reader_limits_match_review_or_cleanup,
)
from retroactive_audit import validate_recheck_history
from review_contract import ROOT, validate_runtime


BASELINE = "d7554a66c62caaae07e7dfd7c02beee24aac5e41"
EVIDENCE_PATH = "localization/ch26-platform-trust-review-20261030.json"
REGISTRY_PATH = "localization/tw-edition/sources/ch26-platform-trust-review-20261030.json"
ITEM_IDS = {"TW-26-003", "TW-26-006", "TW-26-007", "TW-26-009"}


def read(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def read_at(revision, path):
    raw = subprocess.check_output(["git", "show", f"{revision}:{path}"], cwd=ROOT)
    return json.loads(raw)


class PlatformTrustReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.evidence = read(EVIDENCE_PATH)
        cls.runtime = validate_runtime()
        cls.items = {item["id"]: item for item in cls.runtime["items"]}
        cls.sources = {source["id"]: source for source in cls.runtime["sources"]}
        cls.manifest = {
            item["id"]: item for item in read("localization/manifest.json")["entries"]
        }
        cls.reviews = {
            item_id: read(f"localization/reviews/{item_id}.json") for item_id in ITEM_IDS
        }
        register = read("localization/retroactive-review-register-20261019.json")
        cls.records = {item["id"]: item for item in register["substantive_rechecks"]}
        cls.evidence_items = {item["id"]: item for item in cls.evidence["items"]}

    def test_counts_reconcile_to_the_main_baseline_and_current_audit(self):
        self.assertEqual(self.evidence["baseline_main_sha"], BASELINE)
        self.assertEqual(set(self.evidence_items), ITEM_IDS)
        self.assertIn("未新增核心條目", self.evidence["scope"])
        before_coverage = read_at(BASELINE, "localization/tw-edition/coverage.json")
        before_runtime = read_at(BASELINE, "localization/tw-edition/runtime.json")
        before_register = read_at(
            BASELINE, "localization/retroactive-review-register-20261019.json"
        )
        coverage = read("localization/tw-edition/coverage.json")
        current_register = read("localization/retroactive-review-register-20261019.json")
        before = self.evidence["counts_before"]
        after = self.evidence["counts_after"]

        self.assertEqual(before["core_completed"], before_coverage["publication_completed_entries"])
        self.assertEqual(before["core_total"], before_coverage["publication_total_entries"])
        self.assertEqual(before["runtime_items"], len(before_runtime["items"]))
        self.assertEqual(before["runtime_sources_before"], len(before_runtime["sources"]))
        self.assertEqual(before["registry_sources_before"], before_coverage["registry_sources"])
        self.assertEqual(before["json_files_before"], before_coverage["json_files_checked"])
        self.assertEqual(before["substantive_rechecks_before"], len(before_register["substantive_rechecks"]))
        # `counts_after` is the immutable snapshot from this October 30 batch.
        # Later reviews append sources and history, so validate the batch's
        # own arithmetic separately from today's live, cumulative coverage.
        self.assertEqual(
            after["runtime_sources"],
            before["runtime_sources_before"] + len(self.evidence["new_source_ids"]),
        )
        self.assertEqual(
            after["registry_sources"],
            before["registry_sources_before"] + len(self.evidence["new_source_ids"]),
        )
        self.assertEqual(
            after["substantive_rechecks"],
            before["substantive_rechecks_before"] + len(ITEM_IDS),
        )
        self.assertEqual(after["json_files"], before["json_files_before"] + 2)
        self.assertGreaterEqual(
            coverage["publication_completed_entries"], after["core_completed"]
        )
        self.assertEqual(after["core_total"], coverage["publication_total_entries"])
        self.assertGreaterEqual(len(self.runtime["items"]), after["runtime_items"])
        self.assertGreaterEqual(len(self.runtime["sources"]), after["runtime_sources"])
        self.assertGreaterEqual(
            len(current_register["substantive_rechecks"]), after["substantive_rechecks"]
        )
        self.assertGreaterEqual(coverage["json_files_checked"], after["json_files"])
        self.assertGreaterEqual(coverage["registry_sources"], after["registry_sources"])
        self.assertEqual(
            len(coverage["unresolved_source_ids"]),
            len(set(coverage["unresolved_source_ids"])),
        )
        self.assertFalse(after["publication_ready"])
        self.assertFalse(coverage["publication_ready"])

    def test_reader_articles_review_sources_and_historical_hashes_align(self):
        for item_id in ITEM_IDS:
            with self.subTest(item=item_id):
                item = self.items[item_id]
                evidence = self.evidence_items[item_id]
                review = self.reviews[item_id]
                record = self.records[item_id]
                manifest_item = self.manifest[item_id]
                markdown_path = manifest_item["target_path"]
                body_bytes = (ROOT / markdown_path).read_bytes()
                body = body_bytes.decode("utf-8")
                body_sha = hashlib.sha256(body_bytes).hexdigest()

                self.assertEqual(body, item["body"])
                self.assertEqual(body_sha, evidence["after_sha256"])
                self.assertEqual(body_sha, review["target_sha256"])
                self.assertEqual(body_sha, review["source_reviewed_sha256"])
                self.assertEqual(body_sha, record["after_sha256"])
                self.assertEqual(review["reviewed_at"], evidence["reviewed_at"])
                self.assertEqual(review["review_due_at"], evidence["review_due_at"])
                self.assertEqual(record["review_due_at"], evidence["review_due_at"])
                self.assertEqual(record["status"], "ai_source_rechecked_professional_pending")
                self.assertEqual(manifest_item["verified_at"], self.evidence["reviewed_at"])
                self.assertEqual(item["source_ids"], evidence["source_ids"])
                self.assertEqual(record["source_ids"], evidence["source_ids"])
                self.assertEqual(review["source_checks"], evidence["source_checks"])
                self.assertEqual(record["source_checks"], evidence["source_checks"])
                self.assertEqual(record["limits"], review["limits"])
                expected_urls = {self.sources[source_id]["url"] for source_id in item["source_ids"]}
                self.assertEqual({check["url"] for check in review["source_checks"]}, expected_urls)
                self.assertEqual(manifest_item["sources"], [self.sources[sid]["url"] for sid in item["source_ids"]])
                assert_body_version_matches_review_or_cleanup(
                    self, item_id, evidence["after_sha256"], body_sha
                )
                assert_reader_limits_match_review_or_cleanup(self, item_id, review["limits"][0])

                old_runtime = read_at(BASELINE, "localization/tw-edition/runtime.json")
                old_item = next(row for row in old_runtime["items"] if row["id"] == item_id)
                old_review_bytes = subprocess.check_output(
                    ["git", "show", f"{BASELINE}:localization/reviews/{item_id}.json"], cwd=ROOT
                )
                self.assertEqual(hashlib.sha256(old_item["body"].encode()).hexdigest(), evidence["before_sha256"])
                self.assertEqual(hashlib.sha256(old_review_bytes).hexdigest(), evidence["prior_review_sha256"])
                validate_recheck_history(ROOT, record, item)

    def test_new_sources_are_additive_and_every_cited_url_is_registered(self):
        previous = {
            source["id"]: source
            for source in read_at(BASELINE, "localization/tw-edition/runtime.json")["sources"]
        }
        registry = read(REGISTRY_PATH)
        registry_ids = {row[0] for row in registry["sources"]}
        new_ids = set(self.sources) - set(previous)
        self.assertTrue(set(self.evidence["new_source_ids"]).issubset(new_ids))
        self.assertEqual(set(self.evidence["new_source_ids"]), registry_ids)
        for source_id, source in previous.items():
            with self.subTest(source=source_id):
                self.assertEqual(self.sources[source_id], source)
        for item_id in ITEM_IDS:
            with self.subTest(item=item_id):
                article = self.items[item_id]
                article_urls = set(
                    __import__("re").findall(r"\]\((https?://[^)]+)\)", article["body"])
                )
                cited_urls = {self.sources[sid]["url"] for sid in article["source_ids"]}
                self.assertEqual(article_urls, cited_urls)
        self.assertEqual(len(self.evidence["new_source_ids"]), 17)

    def test_legal_scope_and_statistics_are_not_overgeneralized(self):
        child = self.items["TW-26-006"]["body"]
        self.assertIn("2023年2月15日施行版本", child)
        self.assertIn("現行適用文字沒有一律24小時的期限", child)
        self.assertIn("2024年8月修正的相關條文仍待行政院定施行日", child)
        self.assertIn("書面命令後", child)
        self.assertIn("刑法第319條之1至第319條之4", child)
        self.assertIn("不能擴大成所有留言的一律時限", child)
        self.assertIn("6,687個性影像網址", child)
        self.assertIn("6,688件申訴網址", child)
        self.assertIn("不能當成盛行率或個人遭遇機率", child)

        identity = self.items["TW-26-007"]["body"]
        self.assertIn("廣告委託刊播者及出資者", identity)
        self.assertIn("不等於所有瀏覽、發文、留言或私訊", identity)
        self.assertIn("每月獨立訪客數是否超過人口5%", identity)
        self.assertIn("仍由行政院另定施行日期", identity)

        copyright = self.items["TW-26-009"]["body"]
        self.assertIn("資訊儲存服務提供者", copyright)
        self.assertIn("次日起10個工作日", copyright)
        self.assertIn("次日起14個工作日", copyright)
        self.assertIn("造成他人損害", copyright)

        for item_id in ITEM_IDS:
            body = self.items[item_id]["body"]
            for internal_phrase in ("本批", "累計", "實質再審", "AI來源實質再審", "下方為原作"):
                self.assertNotIn(internal_phrase, body)

        all_statistics = [
            stat
            for item in self.evidence["items"]
            for stat in item["statistics_assessed"]
        ]
        self.assertEqual(len(all_statistics), 2)
        for stat in all_statistics:
            self.assertIsNone(stat["denominator"])
            self.assertTrue(stat["denominator_definition"])
            self.assertTrue(stat["data_type"])
            self.assertTrue(stat["limitations"])


if __name__ == "__main__":
    unittest.main()

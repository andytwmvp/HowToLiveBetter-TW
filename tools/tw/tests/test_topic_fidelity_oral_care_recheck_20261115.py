"""逐題保留有台灣讀者價值的口腔健康老化證據。"""
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

BASE = "52aad87ab9034492f71807a12bbc0683df45ca9f"
ITEM_ID = "TW-02-010"
BODY_PATH = "locales/zh-TW/book/ch02/TW-02-010.md"
REVIEW_PATH = f"localization/reviews/{ITEM_ID}.json"
REGISTER_PATH = "localization/retroactive-review-register-20261019.json"
BATCH_PATH = "localization/topic-fidelity-oral-care-recheck-20261115.json"
SOURCE_PATH = "localization/tw-edition/sources/ch02-oral-care-topic-fidelity-20261115.json"
NEW_SOURCE_IDS = {
    "tw02_jages_oral_mortality_2026",
    "tw02_cochrane_powered_brushing_2014",
}


def read(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def git_bytes(revision, path):
    return subprocess.check_output(["git", "show", f"{revision}:{path}"], cwd=ROOT)


def sha(data):
    return hashlib.sha256(data).hexdigest()


class OralCareTopicFidelityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.runtime = validate_runtime()
        cls.item = next(row for row in cls.runtime["items"] if row["id"] == ITEM_ID)
        cls.sources = {row["id"]: row for row in cls.runtime["sources"]}
        cls.manifest = next(
            row for row in read("localization/manifest.json")["entries"]
            if row["id"] == ITEM_ID
        )
        cls.review = read(REVIEW_PATH)
        cls.register = read(REGISTER_PATH)
        cls.record = next(
            row for row in reversed(cls.register["substantive_rechecks"])
            if row["id"] == ITEM_ID and row["reviewed_at"] == "2026-11-15"
        )
        cls.batch = read(BATCH_PATH)

    def test_recheck_is_append_only_and_hash_bound_to_latest_main(self):
        prior_body = git_bytes(BASE, BODY_PATH)
        prior_review = git_bytes(BASE, REVIEW_PATH)
        prior_register = json.loads(git_bytes(BASE, REGISTER_PATH))
        body = (ROOT / BODY_PATH).read_bytes()

        self.assertEqual(self.batch["baseline_main_sha"], BASE)
        self.assertEqual(self.record["prior_revision"], BASE)
        self.assertEqual(self.record["before_sha256"], sha(prior_body))
        self.assertEqual(self.record["previous_body"].encode("utf-8"), prior_body)
        self.assertEqual(self.record["prior_review_sha256"], sha(prior_review))
        self.assertEqual(self.record["after_sha256"], sha(body))
        self.assertEqual(self.review["target_sha256"], sha(body))
        self.assertEqual(self.review["source_reviewed_sha256"], sha(body))
        self.assertEqual(self.manifest["verified_at"], self.review["reviewed_at"])
        self.assertEqual(self.manifest["sources"], self.item["source_ids"])
        self.assertEqual(self.review["source_ids"], self.item["source_ids"])
        self.assertEqual(self.review["source_checks"], self.record["source_checks"])
        self.assertEqual(self.review["limits"], self.record["limits"])
        self.assertEqual(
            self.register["substantive_rechecks"][:len(prior_register["substantive_rechecks"])],
            prior_register["substantive_rechecks"],
        )
        self.assertEqual(self.batch["items"][0]["review_sha256"], sha((ROOT / REVIEW_PATH).read_bytes()))
        self.assertTrue(self.review["professional_review"]["required"])
        self.assertFalse(self.review["professional_review"]["obtained"])
        validate_recheck_history(ROOT, self.record, self.item)

    def test_only_relevant_research_is_restored_with_clear_limits(self):
        body = self.item["body"]
        topic = self.review["topic_fidelity_review"]

        self.assertIn("9,676名", body)
        self.assertIn("65歲以上長者", body)
        self.assertIn("HR為0.89（95%信賴區間0.80–0.99）", body)
        self.assertIn("舌苔清潔工具為0.77（0.68–0.87）", body)
        self.assertIn("不能證明工具本身延長壽命", body)
        self.assertIn("56項隨機試驗、5,068人", body)
        self.assertIn("長期牙齒健康的實際影響仍不清楚", body)
        self.assertNotIn("HR 1.87", body)
        self.assertNotIn("補牙可延長壽命", body)
        self.assertEqual(len(topic["historical_claim_decisions"]), 3)
        self.assertEqual(topic["historical_claim_decisions"][0]["decision"], "bounded_reader_restoration")
        self.assertEqual(topic["historical_claim_decisions"][1]["decision"], "bounded_reader_restoration")
        self.assertEqual(topic["historical_claim_decisions"][2]["decision"], "not_restored_to_reader_body")
        self.assertIn("高異質性的觀察關聯", topic["reader_content_decision"])
        for internal_text in ("批次摘要", "AI審查狀態", "fork管理", "專業審閱仍待"):
            self.assertNotIn(internal_text, body)

    def test_source_links_checks_manifest_and_runtime_align(self):
        body = self.item["body"]
        body_urls = set(re.findall(r"\]\((https://[^)]+)\)", body))
        runtime_urls = {self.sources[source_id]["url"] for source_id in self.item["source_ids"]}
        review_urls = {row["url"] for row in self.review["source_checks"]}
        source_rows = read(SOURCE_PATH)["sources"]

        self.assertEqual(body_urls, runtime_urls)
        self.assertEqual(runtime_urls, review_urls)
        self.assertEqual(set(self.batch["new_source_ids"]), NEW_SOURCE_IDS)
        self.assertEqual({row[0] for row in source_rows}, NEW_SOURCE_IDS)
        source_records = {row[0]: row for row in source_rows}
        for source_id, row in source_records.items():
            self.assertEqual(
                row,
                [self.sources[source_id][key] for key in ("id", "title", "url", "supports")],
            )
        self.assertEqual(set(self.item["source_ids"][-2:]), NEW_SOURCE_IDS)
        self.assertIn("https://doi.org/10.1016/j.jdent.2026.106789", runtime_urls)
        self.assertIn("https://pmc.ncbi.nlm.nih.gov/articles/PMC7133541/", runtime_urls)
        for source_id in NEW_SOURCE_IDS:
            self.assertTrue(self.sources[source_id]["supports"])
            self.assertEqual(self.sources[source_id]["accessed_at"], "2026-11-15")
        checks = {row["source_id"]: row for row in self.review["source_checks"]}
        self.assertTrue(all(row["accessed_at"] == self.review["reviewed_at"] for row in checks.values()))
        self.assertIn("最後更新115-11-04", checks["tw02_mohw_oral_care_20261109"]["retrieval_method"])
        self.assertIn("更新112-11-29", checks["tw02_nhi_periodontal_services_20261109"]["retrieval_method"])
        self.assertIn("回應403", checks["tw02_tph_dental_emergency_20261109"]["retrieval_method"])
        self.assertIn("2026-11-09直接查閱紀錄", checks["tw02_tph_dental_emergency_20261109"]["retrieval_method"])
        jages = next(row for row in self.review["statistics_assessed"] if row["topic"].startswith("日本社區居住"))
        self.assertEqual(jages["value"]["mortality_incidence_rate"], 17.3)
        self.assertIn("每1,000人年17.3件", jages["unit"])
        self.assertIn("未提供計算17.3", jages["denominator"])
        self.assertIn("並非隨機分派", jages["data_type"])
        self.assertIn("不能外推為台灣發生率", jages["limitations"])

    def test_counts_reconcile_without_claiming_publication_ready(self):
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

        self.assertEqual(after["manifest_entries"], before["manifest_entries"])
        self.assertEqual(after["verified_core_entries"], before["verified_core_entries"])
        self.assertEqual(after["runtime_items"], before["runtime_items"])
        self.assertEqual(after["runtime_sources"], before["runtime_sources"] + len(NEW_SOURCE_IDS))
        self.assertEqual(after["source_registry"], before["source_registry"] + len(NEW_SOURCE_IDS))
        self.assertEqual(after["review_rechecks"], before["review_rechecks"] + 1)
        self.assertEqual(after["coverage_json_files"], before["coverage_json_files"] + 2)
        self.assertEqual(after["unresolved_source_ids"], before["unresolved_source_ids"])
        self.assertEqual(after["unresolved_reference_occurrences"], before["unresolved_reference_occurrences"])
        self.assertEqual(after["publication_completed_entries"], before["publication_completed_entries"])
        self.assertFalse(after["publication_ready"])

        next_batch = read("localization/topic-fidelity-stream-licensing-recheck-20261115.json")
        audit = audit_drafts()
        coverage = read("localization/tw-edition/coverage.json")
        publication = publication_report()
        self.assertEqual(after, next_batch["counts_before"])
        self.assertEqual(coverage, audit)
        self.assertFalse(publication["publication_ready"])


if __name__ == "__main__":
    unittest.main()

"""第1章流感接種時程及監測資料的緊急更新契約。"""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ci_language_policy import audit_drafts
from content_validation import load_json
from retroactive_audit import ROOT, validate_recheck_history
from review_contract import validate_runtime
from reader_copy_test_support import assert_professional_review_pending

BASE = "41fe7b26fc9643e4ed077d17f70909cc78a72f21"
EVIDENCE = "localization/ch01-flu-refresh-20261103.json"
ITEM_ID = "TW-01-020"
SOURCE_IDS = [
    "ch01_flu_plan_20260929",
    "ch01_cdc_flu_vaccine_2026",
    "ch01_cdc_flu_effect_safety",
    "hpa_emergency",
    "ch01_cdc_flu_phase2_open_20261102",
    "ch01_cdc_flu_surveillance_20261027",
]
NEW_SOURCE_IDS = SOURCE_IDS[-2:]


def read(path):
    return load_json(ROOT / path)


def old(path):
    return json.loads(subprocess.check_output(["git", "show", f"{BASE}:{path}"], cwd=ROOT, text=True))


class ChapterOneFluRefreshTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.evidence = read(EVIDENCE)
        cls.correction = read("localization/medical-eldercare-correction-20261103.json")
        cls.runtime = validate_runtime()
        cls.items = {item["id"]: item for item in cls.runtime["items"]}
        cls.sources = {source["id"]: source for source in cls.runtime["sources"]}
        cls.manifest = {item["id"]: item for item in read("localization/manifest.json")["entries"]}
        cls.review = read(f"localization/reviews/{ITEM_ID}.json")
        cls.register = read("localization/retroactive-review-register-20261019.json")
        cls.current_rows = [
            row for row in cls.register["substantive_rechecks"]
            if row["id"] == ITEM_ID and row.get("reviewed_at") == "2026-11-03"
        ]
        cls.item_evidence = {item["id"]: item for item in cls.evidence["items"]}[ITEM_ID]

    def test_article_sources_runtime_manifest_and_hash_are_synchronized(self):
        item = self.items[ITEM_ID]
        manifest = self.manifest[ITEM_ID]
        raw = (ROOT / manifest["target_path"]).read_bytes()
        body = raw.decode("utf-8")
        digest = hashlib.sha256(raw).hexdigest()
        self.assertEqual(self.evidence["base_main_sha"], BASE)
        self.assertEqual(self.evidence["new_core_ids"], [])
        self.assertEqual(self.evidence["rechecked_ids"], [ITEM_ID])
        self.assertEqual(self.evidence["reviewed_at"], "2026-11-03")
        self.assertEqual(self.evidence["review_due_at"], "2027-02-03")
        self.assertEqual(manifest["status"], "verified")
        self.assertEqual(manifest["verified_at"], "2026-11-03")
        self.assertEqual(manifest["sources"], SOURCE_IDS)
        self.assertEqual(item["source_ids"], SOURCE_IDS)
        self.assertEqual(item["target_path"], manifest["target_path"])
        self.assertEqual(item["body"], body)
        self.assertEqual(item["title"], self.item_evidence["title"])
        self.assertEqual(self.review["target_sha256"], digest)
        self.assertEqual(self.review["source_reviewed_sha256"], digest)
        self.assertEqual(item["reviewed_at"], "2026-11-03")
        self.assertEqual(item["review_due_at"], "2027-02-03")
        self.assertEqual(self.review["review_due_at"], item["review_due_at"])
        self.assertEqual(self.item_evidence["after_sha256"], digest)
        self.assertEqual(self.review["source_checks"], self.item_evidence["source_checks"])
        self.assertEqual(
            {check["url"] for check in self.review["source_checks"]},
            {self.sources[source_id]["url"] for source_id in SOURCE_IDS},
        )
        self.assertEqual(self.item_evidence["source_ids"], SOURCE_IDS)
        self.assertEqual(self.evidence["source_counts"]["runtime_before"], 1038)
        self.assertEqual(self.evidence["source_counts"]["runtime_after"], self.correction["source_counts"]["runtime_sources_before"])
        self.assertGreaterEqual(len(self.runtime["sources"]), self.correction["source_counts"]["runtime_sources_after"])

    def test_current_taiwan_policy_statistics_and_reader_wording(self):
        body = self.items[ITEM_ID]["body"]
        self.assertIn("第二階段已於11月2日開放", body)
        self.assertIn("第一階段符合資格者仍可接種", body)
        self.assertIn("https://www.cdc.gov.tw/Bulletin/Detail/HGWcz7qahX4V2DxoqL-vXA?typeid=9", body)
        self.assertIn("50至64歲且沒有高風險慢性病的成人", body)
        self.assertNotIn("預定11月2日才開放", body)
        self.assertNotIn("成人通常每季一劑", body)
        self.assertIn("每個流感季接種一劑", body)
        self.assertIn("101,746人次", body)
        self.assertIn("391例流感併發重症及57例死亡", body)
        self.assertIn("可能重複", body)
        self.assertIn("不能換算成個人感染機率", body)
        self.assertIn("颱風放假、門診休診", body)
        self.assertIn("立即打119", body)
        self.assertIn("不要自行開車", body)

        stats = {row["id"]: row for row in self.evidence["statistics"]}
        self.assertEqual(stats["influenza_ili_visits_week42_2026"]["value"], 101746)
        self.assertEqual(stats["influenza_ili_visits_week42_2026"]["numerator"], 101746)
        self.assertIsNone(stats["influenza_ili_visits_week42_2026"]["denominator"])
        self.assertEqual(stats["influenza_severe_cases_2026_season_to_20261026"]["value"], 391)
        self.assertEqual(stats["influenza_deaths_2026_season_to_20261026"]["value"], 57)
        for stat in stats.values():
            for field in ("unit", "period", "geography", "population", "event_definition", "data_type", "method", "source_accessed_at", "limitations"):
                self.assertIn(field, stat)
            self.assertTrue(stat["limitations"])
        self.assertEqual(self.evidence["excluded_sources"][0]["accessed_at"], "2026-11-03")
        self.assertIn("不同流感季", self.evidence["excluded_sources"][0]["exclusion_reason"])

    def test_append_only_review_history_and_professional_boundary(self):
        self.assertEqual(len(self.current_rows), 1)
        record = self.current_rows[0]
        self.assertEqual(record["before_sha256"], self.evidence["review_history"]["before_sha256"])
        self.assertEqual(record["after_sha256"], self.item_evidence["after_sha256"])
        self.assertEqual(record["prior_review_sha256"], self.evidence["review_history"]["prior_review_sha256"])
        self.assertEqual(record["prior_revision"], BASE)
        self.assertEqual(record["review_due_at"], self.review["review_due_at"])
        self.assertEqual(record["source_checks"], self.review["source_checks"])
        self.assertEqual(record["limits"], self.review["limits"])
        self.assertEqual(record["status"], "ai_source_rechecked_professional_pending")
        # The correction counts are a historical snapshot; later append-only reviews must remain valid.
        self.assertGreaterEqual(len(self.register["substantive_rechecks"]), self.correction["source_counts"]["substantive_rechecks_after"])
        self.assertIn(record, self.register["substantive_rechecks"])
        prior_body = subprocess.check_output(["git", "show", self.evidence["review_history"]["prior_body_git_ref"]], cwd=ROOT)
        prior_review = subprocess.check_output(["git", "show", self.evidence["review_history"]["prior_review_git_ref"]], cwd=ROOT)
        self.assertEqual(hashlib.sha256(prior_body).hexdigest(), record["before_sha256"])
        self.assertEqual(hashlib.sha256(prior_review).hexdigest(), record["prior_review_sha256"])
        assert_professional_review_pending(self, self.review["reviewer"])
        self.assertFalse(self.evidence["professional_review"]["obtained"])
        validate_recheck_history(ROOT, record, self.items[ITEM_ID])

    def test_sources_are_additive_and_coverage_remains_unpublished(self):
        previous = old("localization/tw-edition/runtime.json")["sources"]
        current_ids = [source["id"] for source in self.runtime["sources"]]
        previous_ids = [source["id"] for source in previous]
        self.assertEqual(current_ids[:len(previous_ids)], previous_ids)
        for source in previous:
            self.assertEqual(self.sources[source["id"]], source)
        flu_positions = [current_ids.index(source_id) for source_id in NEW_SOURCE_IDS]
        self.assertEqual(flu_positions, list(range(flu_positions[0], flu_positions[0] + len(NEW_SOURCE_IDS))))
        correction_positions = [current_ids.index(source_id) for source_id in self.correction["new_source_ids"]]
        self.assertEqual(correction_positions, list(range(correction_positions[0], correction_positions[0] + len(correction_positions))))
        self.assertLess(flu_positions[-1], correction_positions[0])
        self.assertLess(correction_positions[-1], len(current_ids))
        self.assertEqual(self.evidence["new_source_ids"], NEW_SOURCE_IDS)
        self.assertEqual(self.evidence["source_objects_preserved"], True)
        for source_id in NEW_SOURCE_IDS:
            source = self.sources[source_id]
            self.assertEqual(source["accessed_at"], "2026-11-03")
            self.assertGreater(len(source["retrieval_method"]), 20)
        source_catalog = read("localization/tw-edition/sources/ch01-flu-refresh-20261103.json")
        self.assertEqual([row[0] for row in source_catalog["sources"]], NEW_SOURCE_IDS)
        coverage = read("localization/tw-edition/coverage.json")
        self.assertEqual(coverage, audit_drafts())
        self.assertGreaterEqual(coverage["publication_completed_entries"], self.evidence["core_progress"]["after"])
        self.assertGreaterEqual(coverage["publication_total_entries"], self.evidence["core_progress"]["total"])
        self.assertFalse(coverage["publication_ready"])
        self.assertEqual(self.evidence["source_counts"]["registry_after"], self.correction["source_counts"]["registry_sources_before"])
        self.assertEqual(self.evidence["source_counts"]["json_files_after"], self.correction["source_counts"]["json_files_before"])
        self.assertGreaterEqual(coverage["registry_sources"], self.correction["source_counts"]["registry_sources_after"])
        self.assertGreaterEqual(coverage["json_files_checked"], self.correction["source_counts"]["json_files_after"])
        self.assertGreaterEqual(len(self.runtime["sources"]), self.correction["source_counts"]["runtime_sources_after"])


if __name__ == "__main__":
    unittest.main()

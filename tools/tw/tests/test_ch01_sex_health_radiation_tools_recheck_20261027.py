"""第1章五篇醫療、輻射與工具安全歷史實質再審契約。"""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from reader_copy_test_support import assert_body_version_matches_review_or_cleanup, assert_reader_limits_match_review_or_cleanup
from ci_language_policy import audit_drafts
from content_validation import load_json
from retroactive_audit import validate_recheck_history
from review_contract import ROOT, validate_runtime

BASE = "0ff546d81a1d3d42ec87ba4cd852761dc2e545ae"
EVIDENCE = "localization/ch01-sex-health-radiation-tools-recheck-20261027.json"
ITEM_IDS = {"TW-01-021", "TW-01-028", "TW-01-029", "TW-01-036", "TW-01-042"}
NEW_SOURCE_IDS = {
    "ch01_zoster_cdc_20261027",
    "ch01_zoster_adult_schedule_20261027",
    "ch01_zoster_vghtpe_20261027",
    "ch01_zoster_claims_2011_2020",
    "ch01_ed_ntuh_20261027",
    "ch01_ed_fda_20261027",
    "ch01_ed_survey_2010",
    "ch01_ed_lifestyle_ntuh_20261027",
    "ch01_nusc_reporting_20261027",
    "ch01_nusc_scrap_guide_20261027",
    "ch01_nusc_steel_anomaly_2023",
    "ch01_nusc_firstline_faq_20261027",
    "ch01_grinder_bosch_manual_20261027",
    "ch01_grinder_facilities_20261027",
    "ch01_grinder_law_history_20261027",
    "ch01_grinder_silica_mol_20261027",
}
RETIRED_SOURCE_IDS = {
    "ch01_zoster_cdc", "ch01_zoster_vghtpe", "ch01_zoster_claims_2017",
    "ch01_ed_ntuh202610", "ch01_ed_fda2026", "ch01_ed_lifestyle_ntuh",
    "ch01_nusc_reporting", "ch01_nusc_scrap_guide", "ch01_iaea_uncontrolled_source",
    "ch01_nusc_scrap_effective", "ch01_grinder_bosch_manual",
    "ch01_grinder_facilities", "ch01_grinder_law_history", "ch01_grinder_silica_mol",
}


def read(path):
    return load_json(ROOT / path)


def old(path):
    return json.loads(subprocess.check_output(
        ["git", "show", f"{BASE}:{path}"], cwd=ROOT, text=True
    ))


class Ch01SexHealthRadiationToolsRecheckTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.evidence = read(EVIDENCE)
        cls.runtime = validate_runtime()
        cls.items = {item["id"]: item for item in cls.runtime["items"]}
        cls.sources = {source["id"]: source for source in cls.runtime["sources"]}
        cls.manifest = {entry["id"]: entry for entry in read("localization/manifest.json")["entries"]}
        cls.coverage = read("localization/tw-edition/coverage.json")
        cls.register = read("localization/retroactive-review-register-20261019.json")
        cls.rows = cls.register["substantive_rechecks"]
        cls.base_rows = old("localization/retroactive-review-register-20261019.json")["substantive_rechecks"]
        cls.records = {
            row["id"]: row for row in cls.rows
            if row.get("reviewed_at") == "2026-10-27" and row.get("id") in ITEM_IDS
        }
        cls.evidence_items = {item["id"]: item for item in cls.evidence["items"]}

    def test_batch_counts_and_publication_boundary(self):
        before, after = self.evidence["counts_before"], self.evidence["counts_after"]
        live = audit_drafts()
        self.assertEqual(self.evidence["base_main_sha"], BASE)
        self.assertEqual(set(self.evidence_items), ITEM_IDS)
        self.assertEqual(self.evidence["new_core_entries"], [])
        self.assertEqual(after["substantive_rechecks"], before["substantive_rechecks"] + len(ITEM_IDS))
        self.assertEqual((before["substantive_rechecks"], after["substantive_rechecks"]), (218, 223))
        self.assertEqual((before["runtime_sources"], after["runtime_sources"]), (839, 855))
        self.assertEqual((before["source_registry"], after["source_registry"]), (920, 936))
        self.assertEqual((before["json_files_checked"], after["json_files_checked"]), (483, 485))
        self.assertEqual(after["core_completed"], before["core_completed"])
        self.assertEqual(after["core_total"], 765)
        self.assertEqual(after["shared_reader_items"], 289)
        self.assertEqual(after["topics_with_any_content"], 498)
        self.assertEqual(after["topics_without_content"], 267)
        self.assertEqual((after["unresolved_source_ids"], after["unresolved_reference_occurrences"]), (115, 306))
        for key in ("json_files_checked", "registry_sources", "publication_completed_entries",
                    "unique_draft_entries", "entries_without_any_draft", "publication_ready"):
            self.assertEqual(self.coverage[key], live[key], key)
        self.assertFalse(self.evidence["publication_ready"])
        self.assertFalse(self.coverage["publication_ready"])
        self.assertEqual(self.rows[:len(self.base_rows)], self.base_rows)
        self.assertGreaterEqual(len(self.rows), len(self.base_rows) + len(ITEM_IDS))
        self.assertEqual(set(self.records), ITEM_IDS)

    def test_body_runtime_manifest_review_and_history_are_synchronized(self):
        for item_id in ITEM_IDS:
            with self.subTest(item=item_id):
                ev = self.evidence_items[item_id]
                item = self.items[item_id]
                review_path = f"localization/reviews/{item_id}.json"
                review = read(review_path)
                path = self.manifest[item_id]["target_path"]
                raw = (ROOT / path).read_bytes()
                body = raw.decode("utf-8")
                sha = hashlib.sha256(raw).hexdigest()
                record = self.records[item_id]
                assert_body_version_matches_review_or_cleanup(self, item_id, ev["after_sha256"], sha)
                self.assertEqual(sha, review["target_sha256"])
                self.assertEqual(item["body"], body)
                self.assertEqual(item["title"], next(line[2:] for line in body.splitlines() if line.startswith("# ")))
                self.assertEqual(item["source_ids"], ev["source_ids"])
                self.assertEqual(item["source_ids"], self.manifest[item_id]["sources"])
                self.assertEqual(review["reviewed_at"], self.evidence["reviewed_at"])
                self.assertEqual(self.manifest[item_id]["verified_at"], self.evidence["reviewed_at"])
                self.assertEqual(review["review_due_at"], ev["review_due_at"])
                assert_reader_limits_match_review_or_cleanup(self, item["id"], review["limits"][0])
                self.assertEqual(record["source_checks"], review["source_checks"])
                self.assertEqual(record["limits"], review["limits"])
                self.assertEqual(record["before_sha256"], ev["before_sha256"])
                self.assertEqual(record["after_sha256"], ev["after_sha256"])
                self.assertEqual(record["prior_review_sha256"], ev["prior_review_sha256"])
                self.assertEqual(record["prior_revision"], BASE)
                self.assertEqual(record["review_path"], review_path)
                self.assertEqual(record["status"], "ai_source_rechecked_professional_pending")
                self.assertEqual(
                    {self.sources[sid]["url"] for sid in ev["source_ids"]},
                    {check["url"] for check in review["source_checks"]},
                )
                prior_body = subprocess.check_output(["git", "show", ev["prior_body_git_ref"]], cwd=ROOT)
                prior_review = subprocess.check_output(["git", "show", ev["prior_review_git_ref"]], cwd=ROOT)
                self.assertEqual(hashlib.sha256(prior_body).hexdigest(), ev["before_sha256"])
                self.assertEqual(hashlib.sha256(prior_review).hexdigest(), ev["prior_review_sha256"])
                validate_recheck_history(ROOT, record, item)

    def test_sources_append_without_rewriting_prior_objects(self):
        prior = old("localization/tw-edition/runtime.json")["sources"]
        current_ids = [source["id"] for source in self.runtime["sources"]]
        prior_ids = [source["id"] for source in prior]
        self.assertEqual(current_ids[:len(prior_ids)], prior_ids)
        for source in prior:
            self.assertEqual(self.sources[source["id"]], source)
        added = self.evidence["sources_added"]
        self.assertEqual({source["id"] for source in added}, NEW_SOURCE_IDS)
        added_ids = [source["id"] for source in added]
        start = len(prior_ids)
        self.assertEqual(current_ids[start:start + len(added_ids)], added_ids)
        catalog = read("localization/tw-edition/sources/ch01-sex-health-radiation-tools-recheck-20261027.json")
        catalog_rows = {row[0]: row for row in catalog["sources"]}
        self.assertEqual([row[0] for row in catalog["sources"]], [source["id"] for source in added])
        for source in added:
            self.assertEqual(self.sources[source["id"]], source)
            self.assertEqual(catalog_rows[source["id"]][2], source["url"])
            self.assertGreater(len(source["retrieval_method"]), 20)
        retired = self.evidence["sources_retired"]
        self.assertEqual({source["id"] for source in retired}, RETIRED_SOURCE_IDS)
        for source in retired:
            original = next(row for row in prior if row["id"] == source["id"])
            self.assertTrue(source["current_source_object_unchanged"])
            self.assertEqual(self.sources[source["id"]], original)
            self.assertEqual(
                hashlib.sha256(json.dumps(original, ensure_ascii=False, sort_keys=True).encode()).hexdigest(),
                source["prior_source_sha256"],
            )

    def test_statistics_preserve_measure_population_and_denominator_limits(self):
        stats = {stat["id"]: stat for stat in self.evidence["statistics"]}
        self.assertEqual(len(stats), 9)
        self.assertEqual(stats["taiwan_hz_age_standardized_rate_2011"]["value"], 7.15)
        self.assertEqual(stats["taiwan_hz_age_standardized_rate_2020"]["value"], 7.82)
        self.assertEqual(stats["taiwan_hz_crude_rate_age18_49_2020"]["value"], 5.92)
        self.assertEqual(stats["taiwan_hz_crude_rate_age50plus_2020"]["value"], 14.00)
        self.assertEqual(stats["taiwan_ed_survey_prevalence_all_2010"]["denominator"], 1060)
        self.assertIsNone(stats["taiwan_ed_survey_prevalence_all_2010"]["numerator"])
        self.assertEqual(stats["taiwan_steel_recycle_reports_2023"]["value"], 38)
        self.assertEqual(stats["taiwan_steel_recycle_artificial_nuclide_2023"]["denominator"], 38)
        self.assertEqual(stats["taiwan_engineered_stone_silicosis_2021_2024"]["value"], 17)
        for stat in stats.values():
            for field in ("unit", "period", "geography", "population", "numerator", "denominator",
                          "denominator_description", "event_definition", "data_type", "method",
                          "source_accessed_at", "limitations"):
                self.assertIn(field, stat)
            self.assertEqual(stat["source_accessed_at"], "2026-10-27")
            self.assertTrue(stat["limitations"])
            self.assertTrue(stat["denominator_description"])

    def test_body_safety_boundaries_and_professional_limits(self):
        bodies = {key: self.items[key]["body"] for key in ITEM_IDS}
        self.assertIn("每千人年7.15例", bodies["TW-01-021"])
        self.assertIn("研究沒有疫苗史", bodies["TW-01-021"])
        self.assertIn("2010年發表", bodies["TW-01-028"])
        self.assertIn("不可與PDE5抑制劑併用", bodies["TW-01-028"])
        self.assertIn("不自行推算運動、戒菸或減重效果", bodies["TW-01-029"])
        self.assertIn("0800-088-928", bodies["TW-01-036"])
        self.assertIn("不是民眾撿到失控射源的全國發生率", bodies["TW-01-036"])
        self.assertIn("不把特定手冊擴大成全機型規則", bodies["TW-01-042"])
        self.assertNotIn("勿改裝鋸齒片", bodies["TW-01-042"])
        self.assertIn("每日作業前試轉至少1分鐘", bodies["TW-01-042"])
        for item_id in ITEM_IDS:
            self.assertIn("非醫師", read(f"localization/reviews/{item_id}.json")["reviewer"])
            self.assertEqual(self.records[item_id]["status"], "ai_source_rechecked_professional_pending")
            self.assertTrue(self.evidence_items[item_id]["unresolved"])


if __name__ == "__main__":
    unittest.main()

"""第1章血尿急症、HP篩檢、C肝及胃鏡四篇高風險歷史再審契約。"""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from reader_copy_test_support import assert_body_version_matches_review_or_cleanup
from ci_language_policy import audit_drafts
from content_validation import load_json
from retroactive_audit import validate_recheck_history
from review_contract import ROOT, validate_runtime

BASE = "9d34ccae0ad8c478b9ea2d514ade441c2d33ceae"
EVIDENCE_PATH = "localization/ch01-gi-hepatitis-hematuria-recheck-20261027.json"
ITEM_IDS = {"TW-01-023", "TW-01-027", "TW-01-045", "TW-01-047"}
NEW_SOURCE_IDS = {
    "ch01_hp_klchb_20261006",
    "ch01_stomach_cancer_registry_2023",
    "ch01_hematuria_tsgh_20261023",
    "ch01_hcv_hpa_qa6_ntpc_202602",
    "ch01_hcv_nhi_daa_coverage_20251201",
}
RETIRED_SOURCE_IDS = {
    "ch01_hematuria_ntuh",
    "ch01_uti_vgh2026",
    "ch01_hcv_hpa_qa6",
    "ch01_hcv_ntuh_diagnosis",
    "ch01_hcv_ntuh_svr",
}


def read(path):
    return load_json(ROOT / path)


def old(path):
    return json.loads(
        subprocess.check_output(["git", "show", f"{BASE}:{path}"], cwd=ROOT, text=True)
    )


class Ch01GIHepatitisHematuriaRecheckTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.evidence = read(EVIDENCE_PATH)
        cls.runtime = validate_runtime()
        cls.items = {item["id"]: item for item in cls.runtime["items"]}
        cls.sources = {source["id"]: source for source in cls.runtime["sources"]}
        cls.manifest = {item["id"]: item for item in read("localization/manifest.json")["entries"]}
        cls.register = read("localization/retroactive-review-register-20261019.json")
        cls.rows = cls.register["substantive_rechecks"]
        cls.base_rows = old("localization/retroactive-review-register-20261019.json")["substantive_rechecks"]
        cls.records = {
            item_id: [
                row for row in cls.rows
                if row["id"] == item_id and row.get("reviewed_at") == "2026-10-27"
            ]
            for item_id in ITEM_IDS
        }
        cls.evidence_items = {item["id"]: item for item in cls.evidence["items"]}

    def test_batch_progress_and_publication_boundary(self):
        coverage = read("localization/tw-edition/coverage.json")
        self.assertEqual(self.evidence["base_main_sha"], BASE)
        self.assertEqual(self.evidence["new_core_entries"], [])
        self.assertEqual({item["id"] for item in self.evidence["items"]}, ITEM_IDS)
        self.assertEqual(self.evidence["counts_before"]["core_completed"], 278)
        self.assertEqual(self.evidence["counts_after"]["core_completed"], 278)
        self.assertEqual(self.evidence["counts_after"]["core_total"], 765)
        self.assertEqual(self.evidence["counts_before"]["substantive_rechecks"], 210)
        self.assertEqual(self.evidence["counts_after"]["substantive_rechecks"], 214)
        self.assertEqual(self.evidence["counts_after"]["runtime_sources"], 836)
        self.assertEqual(self.evidence["counts_after"]["source_registry"], 917)
        self.assertEqual(self.evidence["counts_after"]["json_files_checked"], 481)
        live_coverage = audit_drafts()
        self.assertEqual(coverage["json_files_checked"], live_coverage["json_files_checked"])
        self.assertEqual(coverage["registry_sources"], live_coverage["registry_sources"])
        self.assertEqual(coverage["unique_draft_entries"], 498)
        self.assertEqual(coverage["entries_without_any_draft"], 267)
        self.assertGreaterEqual(len(self.rows), len(self.base_rows) + len(ITEM_IDS))
        self.assertEqual(self.rows[:len(self.base_rows)], self.base_rows)
        self.assertFalse(self.evidence["publication_ready"])
        self.assertFalse(self.evidence["counts_after"]["publication_ready"])

    def test_body_review_manifest_runtime_and_append_only_register_are_synchronized(self):
        for item_id in ITEM_IDS:
            with self.subTest(item=item_id):
                evidence_item = self.evidence_items[item_id]
                runtime_item = self.items[item_id]
                manifest_item = self.manifest[item_id]
                review_path = f"localization/reviews/{item_id}.json"
                review = read(review_path)
                body = (ROOT / manifest_item["target_path"]).read_bytes()
                body_text = body.decode("utf-8")
                body_hash = hashlib.sha256(body).hexdigest()
                title = next(line[2:] for line in body_text.splitlines() if line.startswith("# "))
                assert_body_version_matches_review_or_cleanup(self, item_id, evidence_item["after_sha256"], body_hash)
                self.assertEqual(body_hash, review["target_sha256"])
                self.assertEqual(body_text, runtime_item["body"])
                self.assertEqual(title, runtime_item["title"])
                self.assertEqual(manifest_item["target_path"], review["target_path"])
                self.assertEqual(manifest_item["sources"], evidence_item["source_ids"])
                self.assertEqual(runtime_item["source_ids"], evidence_item["source_ids"])
                self.assertEqual(manifest_item["verified_at"], "2026-10-27")
                self.assertEqual(review["reviewed_at"], "2026-10-27")
                self.assertEqual(review["review_due_at"], evidence_item["review_due_at"])
                self.assertEqual(runtime_item["review_due_at"], evidence_item["review_due_at"])
                self.assertEqual(runtime_item["review_status"], "source_checked")
                self.assertEqual(len(self.records[item_id]), 1)
                record = self.records[item_id][0]
                self.assertEqual(record["before_sha256"], evidence_item["before_sha256"])
                self.assertEqual(record["after_sha256"], evidence_item["after_sha256"])
                self.assertEqual(record["prior_review_sha256"], evidence_item["prior_review_sha256"])
                self.assertEqual(record["prior_revision"], BASE)
                self.assertEqual(record["source_ids"], evidence_item["source_ids"])
                self.assertEqual(record["reviewed_at"], "2026-10-27")
                self.assertEqual(record["status"], "ai_source_rechecked_professional_pending")
                self.assertEqual(record["source_checks"], review["source_checks"])
                self.assertEqual(record["limits"], review["limits"])
                old_body = subprocess.check_output(["git", "show", evidence_item["prior_body_git_ref"]], cwd=ROOT)
                old_review = subprocess.check_output(["git", "show", evidence_item["prior_review_git_ref"]], cwd=ROOT)
                self.assertEqual(hashlib.sha256(old_body).hexdigest(), evidence_item["before_sha256"])
                self.assertEqual(hashlib.sha256(old_review).hexdigest(), evidence_item["prior_review_sha256"])
                prior_rows = [row for row in self.rows if row["id"] == item_id and row.get("reviewed_at") != "2026-10-27"]
                expected_prior_rows = [row for row in self.base_rows if row["id"] == item_id]
                self.assertEqual(prior_rows, expected_prior_rows)
                validate_recheck_history(ROOT, record, runtime_item)

    def test_sources_are_additive_and_retired_citations_keep_their_history(self):
        previous = old("localization/tw-edition/runtime.json")["sources"]
        previous_ids = [source["id"] for source in previous]
        current_ids = [source["id"] for source in self.runtime["sources"]]
        self.assertEqual(current_ids[:len(previous_ids)], previous_ids)
        self.assertEqual(
            current_ids[len(previous_ids):len(previous_ids) + len(NEW_SOURCE_IDS)],
            [source["id"] for source in self.evidence["sources_added"]],
        )
        for source in previous:
            self.assertEqual(self.sources[source["id"]], source)
        evidence_added = {source["id"]: source for source in self.evidence["sources_added"]}
        self.assertEqual(set(evidence_added), NEW_SOURCE_IDS)
        catalog = read("localization/tw-edition/sources/ch01-gi-hepatitis-hematuria-recheck-20261027.json")
        catalog_rows = {row[0]: row for row in catalog["sources"]}
        self.assertEqual(set(catalog_rows), NEW_SOURCE_IDS)
        self.assertEqual([row[0] for row in catalog["sources"]], [source["id"] for source in self.evidence["sources_added"]])
        for source_id in NEW_SOURCE_IDS:
            source = self.sources[source_id]
            self.assertEqual(source, evidence_added[source_id])
            self.assertEqual(catalog_rows[source_id][2], source["url"])
            self.assertGreater(len(source["retrieval_method"]), 20)
        self.assertEqual({item["id"] for item in self.evidence["sources_retired"]}, RETIRED_SOURCE_IDS)
        for retired in self.evidence["sources_retired"]:
            old_source = next(source for source in previous if source["id"] == retired["id"])
            self.assertEqual(self.sources[retired["id"]], old_source)
            digest = hashlib.sha256(json.dumps(old_source, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
            self.assertEqual(digest, retired["prior_source_sha256"])
            self.assertTrue(retired["preserved_in_runtime"])
        for item_id in ITEM_IDS:
            cited = set(self.items[item_id]["source_ids"])
            self.assertTrue(cited.isdisjoint(RETIRED_SOURCE_IDS))

    def test_statistics_keep_period_population_event_and_denominator_limits(self):
        stats = {stat["id"]: stat for stat in self.evidence["statistics"]}
        self.assertEqual(len(stats), 6)
        for stat in stats.values():
            for field in ["value", "unit", "period", "geography", "population", "numerator", "denominator", "denominator_description", "event_definition", "data_type", "method", "source_accessed_at", "limitations"]:
                self.assertIn(field, stat)
            self.assertTrue(stat["period"])
            self.assertTrue(stat["event_definition"])
            self.assertTrue(stat["limitations"])
        hp = stats["hpylori_reported_prevalence_2026_mohw"]
        self.assertEqual(hp["value"], 30)
        self.assertIsNone(hp["numerator"])
        self.assertIsNone(hp["denominator"])
        self.assertIn("原始年份", hp["limitations"][1])
        gastric = stats["gastric_cancer_cases_2023_taiwan"]
        self.assertEqual((gastric["value"], gastric["numerator"]), (4518, 4518))
        self.assertIn("不含原位癌", " ".join(gastric["limitations"]))
        gastric_asr = stats["gastric_cancer_asr_2023_taiwan"]
        self.assertEqual(gastric_asr["value"], 9.8)
        self.assertIsNone(gastric_asr["denominator"])
        self.assertIn("不是以病例數直接除以100,000", gastric_asr["denominator_description"])
        hcv = stats["hcv_bc_cumulative_screening_service_users_2025_12"]
        self.assertEqual(hcv["reported_value"], ">7,860,000")
        self.assertIn("不是HCV新感染事件", hcv["event_definition"])
        self.assertIsNone(hcv["denominator"])

    def test_article_wording_preserves_emergency_first_and_taiwan_policy_boundaries(self):
        bodies = {item_id: self.items[item_id]["body"] for item_id in ITEM_IDS}
        self.assertIn("基隆市公告另列", bodies["TW-01-023"])
        self.assertIn("4,518例", bodies["TW-01-023"])
        self.assertIn("民眾可領450元", bodies["TW-01-023"])
        self.assertIn("缺原始", bodies["TW-01-023"])
        self.assertIn("先急診", bodies["TW-01-027"])
        self.assertIn("血塊阻塞", bodies["TW-01-027"])
        self.assertIn("撥119", bodies["TW-01-027"])
        self.assertIn("1986", bodies["TW-01-045"])
        self.assertIn("HCV RNA", bodies["TW-01-045"])
        self.assertIn("逾786萬人", bodies["TW-01-045"])
        self.assertIn("重新感染", bodies["TW-01-045"])
        self.assertIn("不是胃鏡", bodies["TW-01-047"])
        self.assertIn("年齡標準化發生率", bodies["TW-01-047"])
        self.assertIn("騎車", bodies["TW-01-047"])
        date = next(x for x in self.evidence["policy_dates"] if x["id"] == "adult_hcv_screening_expansion")
        self.assertIn("差異", date["status"])
        self.assertFalse(self.evidence["publication_ready"])


if __name__ == "__main__":
    unittest.main()

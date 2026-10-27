"""第1章HIV、PrEP與賭博危害四篇歷史實質再審契約。"""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ci_language_policy import audit_drafts
from content_validation import load_json
from retroactive_audit import validate_recheck_history
from review_contract import ROOT, validate_entry, validate_runtime

BASE = "69f1bd947a32997f99837f7ed9fcdfdc84983079"
EVIDENCE = "localization/ch01-gambling-hiv-prep-recheck-20261027.json"
IDS = {"TW-01-030", "TW-01-031", "TW-01-037", "TW-01-038"}
NEW_SOURCE_IDS = {
    "ch01_gambling_mohw_1925_20250828",
    "ch01_prep_selfpay_20261008",
    "ch01_hiv_nidss_20261027",
}


def read(path):
    return load_json(ROOT / path)


def old(path):
    return json.loads(
        subprocess.check_output(["git", "show", f"{BASE}:{path}"], cwd=ROOT, text=True)
    )


class Ch01GamblingHivPrepRecheckTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.evidence = read(EVIDENCE)
        cls.runtime = validate_runtime()
        cls.items = {item["id"]: item for item in cls.runtime["items"]}
        cls.sources = {source["id"]: source for source in cls.runtime["sources"]}
        cls.manifest = {entry["id"]: entry for entry in read("localization/manifest.json")["entries"]}
        cls.register = read("localization/retroactive-review-register-20261019.json")
        cls.rows = cls.register["substantive_rechecks"]
        cls.base_rows = old("localization/retroactive-review-register-20261019.json")["substantive_rechecks"]
        cls.evidence_items = {item["id"]: item for item in cls.evidence["items"]}

    def test_counts_are_current_and_content_remains_unapproved(self):
        before, after = self.evidence["counts_before"], self.evidence["counts_after"]
        coverage = read("localization/tw-edition/coverage.json")
        live = audit_drafts()
        self.assertEqual(self.evidence["base_main_sha"], BASE)
        self.assertEqual(set(self.evidence_items), IDS)
        self.assertEqual(self.evidence["new_core_entries"], [])
        self.assertEqual(after["core_completed"], before["core_completed"])
        self.assertEqual(after["core_total"], 765)
        self.assertEqual(after["shared_reader_items"], before["shared_reader_items"])
        self.assertEqual(after["substantive_rechecks"], before["substantive_rechecks"] + 4)
        self.assertEqual(after["runtime_sources"], before["runtime_sources"] + 3)
        self.assertEqual(after["source_registry"], before["source_registry"] + 3)
        self.assertEqual(after["json_files_checked"], before["json_files_checked"] + 2)
        for field in (
            "json_files_checked", "registry_sources", "unique_draft_entries",
            "entries_without_any_draft", "unresolved_source_ids",
            "unresolved_reference_occurrences",
        ):
            self.assertEqual(coverage[field], live[field])
        self.assertEqual(after["topics_with_any_content"], 498)
        self.assertEqual(after["topics_without_content"], 267)
        self.assertFalse(self.evidence["publication_ready"])
        self.assertFalse(after["publication_ready"])
        self.assertFalse(coverage["publication_ready"])

    def test_review_hashes_source_ids_and_append_only_history_are_synchronized(self):
        base_manifest = {entry["id"]: entry for entry in old("localization/manifest.json")["entries"]}
        records = {
            item["id"]: item for item in self.rows
            if item.get("reviewed_at") == "2026-10-27" and item["id"] in IDS
        }
        self.assertEqual(self.rows[:len(self.base_rows)], self.base_rows)
        self.assertGreaterEqual(len(self.rows), len(self.base_rows) + 4)
        self.assertEqual(set(records), IDS)
        for item_id in IDS:
            with self.subTest(item=item_id):
                ev = self.evidence_items[item_id]
                body = (ROOT / ev["target_path"]).read_bytes()
                body_hash = hashlib.sha256(body).hexdigest()
                review = read(f"localization/reviews/{item_id}.json")
                entry = self.manifest[item_id]
                item = self.items[item_id]
                record = records[item_id]
                self.assertEqual(body_hash, ev["after_sha256"])
                self.assertEqual(body_hash, review["target_sha256"])
                self.assertEqual(body.decode("utf-8"), item["body"])
                self.assertEqual(entry["sources"], ev["source_ids"])
                self.assertEqual(item["source_ids"], ev["source_ids"])
                self.assertEqual(review["source_ids"], ev["source_ids"])
                self.assertEqual(ev["previous_source_ids"], base_manifest[item_id]["sources"])
                self.assertEqual(entry["verified_at"], "2026-10-27")
                self.assertEqual(review["reviewed_at"], "2026-10-27")
                self.assertEqual(item["reviewed_at"], "2026-10-27")
                self.assertEqual(item["review_status"], "source_checked")
                self.assertEqual(record["status"], "ai_source_rechecked_professional_pending")
                self.assertEqual(record["prior_revision"], BASE)
                self.assertEqual(record["before_sha256"], ev["before_sha256"])
                self.assertEqual(record["after_sha256"], body_hash)
                self.assertEqual(record["prior_review_sha256"], ev["prior_review_sha256"])
                self.assertEqual(record["source_ids"], ev["source_ids"])
                self.assertEqual(record["source_checks"], review["source_checks"])
                self.assertEqual(record["limits"], review["limits"])
                self.assertEqual(
                    {check["url"] for check in review["source_checks"]},
                    {self.sources[source_id]["url"] for source_id in item["source_ids"]},
                )
                old_body = subprocess.check_output(["git", "show", ev["prior_body_git_ref"]], cwd=ROOT)
                old_review = subprocess.check_output(["git", "show", ev["prior_review_git_ref"]], cwd=ROOT)
                self.assertEqual(hashlib.sha256(old_body).hexdigest(), ev["before_sha256"])
                self.assertEqual(hashlib.sha256(old_review).hexdigest(), ev["prior_review_sha256"])
                validate_recheck_history(ROOT, record, item)

    def test_sources_are_additive_and_old_source_history_is_preserved(self):
        base_runtime = old("localization/tw-edition/runtime.json")
        base_ids = [source["id"] for source in base_runtime["sources"]]
        current_ids = [source["id"] for source in self.runtime["sources"]]
        self.assertEqual(current_ids[:len(base_ids)], base_ids)
        added = self.runtime["sources"][len(base_ids):]
        batch_added = self.evidence["sources_added"]
        batch_ids = [source["id"] for source in batch_added]
        self.assertEqual(len(batch_ids), len(NEW_SOURCE_IDS))
        self.assertEqual(set(batch_ids), NEW_SOURCE_IDS)
        self.assertEqual([source["id"] for source in added[:len(batch_ids)]], batch_ids)
        self.assertTrue(set(batch_ids).issubset({source["id"] for source in added}))
        for prior in base_runtime["sources"]:
            self.assertEqual(self.sources[prior["id"]], prior)
        catalog = read("localization/tw-edition/sources/ch01-gambling-hiv-prep-recheck-20261027.json")
        self.assertEqual([row[0] for row in catalog["sources"]], batch_ids)
        for row, source in zip(catalog["sources"], batch_added):
            self.assertEqual(row[2], source["url"])
            self.assertEqual(row[3], source["supports"])
        old_monthly = next(source for source in base_runtime["sources"] if source["id"] == "ch01_hiv_monthly_202609")
        self.assertEqual(self.sources[old_monthly["id"]], old_monthly)
        retired = next(source for source in self.evidence["sources_retired"] if source["id"] == "ch01_gambling_mental")
        former = next(source for source in base_runtime["sources"] if source["id"] == retired["id"])
        self.assertEqual(self.sources[former["id"]], former)
        self.assertEqual(
            hashlib.sha256(json.dumps(former, ensure_ascii=False, sort_keys=True).encode()).hexdigest(),
            retired["prior_source_sha256"],
        )
        self.assertTrue(retired["preserved_in_runtime"])

    def test_statistics_and_reader_guidance_keep_their_scope(self):
        stats = {item["id"]: item for item in self.evidence["statistics"]}
        current = stats["hiv_diagnosis_cases_2026_asof_20261027"]
        prior_year = stats["hiv_diagnosis_cases_2025_full_year_asof_20261027"]
        self.assertEqual((current["value"], current["numerator"], current["denominator"]), (837, 837, None))
        self.assertEqual((prior_year["value"], prior_year["numerator"], prior_year["denominator"]), (1027, 1027, None))
        for stat in (current, prior_year):
            self.assertIn("診斷日", stat["event_definition"])
            self.assertIn("本國籍及非本國籍", stat["geography"])
            self.assertIn("資料更新時間2026-10-27 07:16", stat["method"])
            self.assertTrue(stat["limitations"])
        bodies = {key: self.items[key]["body"] for key in IDS}
        self.assertIn("72小時內", bodies["TW-01-030"])
        self.assertIn("24小時內最佳", bodies["TW-01-030"])
        self.assertIn("2019-08-13", bodies["TW-01-030"])
        self.assertIn("資料更新2026-10-27", bodies["TW-01-030"])
        self.assertIn("3至12週", bodies["TW-01-031"])
        self.assertIn("當次（3日內）", bodies["TW-01-031"])
        self.assertIn("只補助該次就醫", bodies["TW-01-031"])
        self.assertIn("不能取代119、急診或賭博成癮治療", bodies["TW-01-037"])
        self.assertIn("未找到具全國代表性", bodies["TW-01-037"])
        self.assertIn("412-8518轉2", bodies["TW-01-037"])
        self.assertIn("自費院所名冊2026-10-08", bodies["TW-01-038"])
        self.assertIn("35歲（含）以下", bodies["TW-01-038"])
        self.assertNotIn("約七成", bodies["TW-01-038"])
        self.assertTrue(all("專業獨立審閱" in read(f"localization/reviews/{key}.json")["limits"][-1] for key in IDS))


if __name__ == "__main__":
    unittest.main()

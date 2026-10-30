"""2026-10-29 旅外急難、境外醫療、失聯求援及預售屋歷史再審。"""
import hashlib
import json
import subprocess
import sys
import re
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ci_language_policy import audit_drafts
from retroactive_audit import normalize_reader_item, validate_recheck_history
from review_contract import ROOT, publication_report, validate_runtime


BASE = "2090d5865c46c037afb82d09bbd9acfd09529725"
REVIEW_REGISTER_BASE = "a853321583f76ef502ec88738af8d221b8d696d4"
IDS = ("TW-21-003", "TW-21-004", "TW-21-011", "TW-15-018")


def read(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


class HighRiskRecheckTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.batch = read("localization/ch15-ch21-high-risk-recheck-20261029.json")
        cls.runtime = validate_runtime()
        cls.items = {item["id"]: item for item in cls.runtime["items"]}
        cls.sources = {source["id"]: source for source in cls.runtime["sources"]}
        cls.manifest = {item["id"]: item for item in read("localization/manifest.json")["entries"]}
        cls.register = read("localization/retroactive-review-register-20261019.json")
        cls.base_register = json.loads(subprocess.check_output(
            ["git", "show", f"{REVIEW_REGISTER_BASE}:localization/retroactive-review-register-20261019.json"],
            cwd=ROOT,
            text=True,
        ))

    def test_four_reader_articles_match_manifest_runtime_and_new_review_edges(self):
        self.assertEqual(self.batch["base_main_sha"], BASE)
        self.assertEqual(tuple(self.batch["scope"]["historical_ids"]), IDS)
        self.assertEqual(self.batch["scope"]["new_core_ids"], [])
        rows = {item["id"]: item for item in self.batch["items"]}
        self.assertEqual(set(rows), set(IDS))
        for key in IDS:
            with self.subTest(id=key):
                item = self.items[key]
                review = read(f"localization/reviews/{key}.json")
                body = (ROOT / item["target_path"]).read_bytes()
                digest = hashlib.sha256(body).hexdigest()
                evidence = rows[key]
                matches = [record for record in self.register["substantive_rechecks"]
                           if record["id"] == key
                           and record["prior_revision"] == BASE
                           and record["after_sha256"] == digest]
                self.assertEqual(len(matches), 1)
                record = matches[0]
                old = subprocess.check_output(
                    ["git", "show", f"{BASE}:{item['target_path']}"], cwd=ROOT
                )
                self.assertEqual(hashlib.sha256(old).hexdigest(), record["before_sha256"])
                self.assertEqual(body.decode("utf-8"), item["body"])
                self.assertEqual(digest, evidence["body_sha256_after"])
                self.assertEqual(record["before_sha256"], evidence["body_sha256_before"])
                self.assertEqual(review["target_sha256"], digest)
                self.assertEqual(self.manifest[key]["verified_at"], "2026-10-29")
                self.assertEqual(review["reviewed_at"], item["reviewed_at"])
                self.assertEqual(review["review_due_at"], item["review_due_at"])
                self.assertEqual(review["source_checks"], record["source_checks"])
                self.assertEqual(item["source_ids"], evidence["source_ids"])
                self.assertEqual(
                    self.manifest[key]["sources"],
                    [self.sources[source_id]["url"] for source_id in item["source_ids"]],
                )
                for source_id in item["source_ids"]:
                    self.assertIn(self.sources[source_id]["url"], item["body"])
                validate_recheck_history(ROOT, record, item)

    def test_statistics_preserve_units_periods_and_missing_denominators(self):
        records = {row["id"]: row for row in self.register["substantive_rechecks"]
                   if row["prior_revision"] == BASE and row["reviewed_at"] == "2026-10-29"}
        self.assertEqual(set(records), set(IDS))

        emergency = records["TW-21-003"]["statistics_assessed"][0]
        self.assertEqual(emergency["period"], "2025年（民國114年）")
        self.assertEqual(emergency["value"], {"events": 7374, "service_person_times": 9336})
        self.assertIsNone(emergency["denominator"])
        self.assertIn("行政", emergency["data_type"])

        lost_contact = records["TW-21-011"]["statistics_assessed"][0]
        self.assertEqual(lost_contact["value"], {"listed_count": 240})
        self.assertIsNone(lost_contact["denominator"])
        self.assertIn("口徑未明", lost_contact["data_type"])

        presale = records["TW-15-018"]["statistics_assessed"]
        local_sample = next(stat for stat in presale if stat["name"] == "115年度地方選案預售屋契約不符比例")
        self.assertEqual((local_sample["value"]["projects_with_some_noncompliance"],
                          local_sample["denominator"]), (9, 50))
        clauses = next(stat for stat in presale if stat["name"] == "地方選案契約檢核項次不符數")
        self.assertEqual((clauses["value"]["noncompliant_items"], clauses["denominator"]), (13, 750))

        overseas_claim = records["TW-21-004"]["statistics_assessed"][0]
        self.assertEqual(overseas_claim["period"], "截至2026-10-29")
        self.assertIsNone(overseas_claim["value"])
        self.assertIsNone(overseas_claim["denominator"])
        self.assertIn("核退金額上限", overseas_claim["data_type"])

    def test_reader_copy_has_no_editorial_progress_notes_and_coverage_is_current(self):
        reader_paths = ["README.md", "REPOSITORY_GUIDE.md", "locales/zh-TW/README.md"]
        reader_paths.extend(str(path.relative_to(ROOT)) for path in
                            (ROOT / "locales/zh-TW/book").rglob("TW-*.md"))
        progress_patterns = (
            r"(?m)^\s*(?:>\s*)?\*{0,2}20\d{2}-\d{2}-\d{2}[^\n]*(?:再審|稽核)",
            r"(?m)^\s*(?:本次|本批)[^\n]*(?:再審|來源核對|稽核)[^\n]*",
            r"(?im)^\s*僅在此.*(?:fork|repo)",
            r"(?m)^\s*(?:下方為原作|臺灣版尚在)",
        )
        for path in reader_paths:
            text = (ROOT / path).read_text(encoding="utf-8")
            for pattern in progress_patterns:
                with self.subTest(path=path, pattern=pattern):
                    self.assertIsNone(re.search(pattern, text))

        coverage = read("localization/tw-edition/coverage.json")
        report = publication_report()
        self.assertEqual(coverage["publication_completed_entries"], report["publication_completed_entries"])
        self.assertEqual(coverage["core_reviewed_entries"], report["publication_completed_entries"])
        self.assertFalse(coverage["publication_ready"])
        self.assertEqual(audit_drafts(), coverage)
        self.assertEqual(self.batch["counts_after"]["core_reviewed"], 278)
        prior_rechecks = self.base_register["substantive_rechecks"]
        current_rechecks = self.register["substantive_rechecks"]
        self.assertEqual(len(prior_rechecks), self.batch["counts_after"]["substantive_rechecks"])
        self.assertEqual(current_rechecks[:len(prior_rechecks)], prior_rechecks)
        self.assertGreater(len(current_rechecks), len(prior_rechecks))

    def test_reader_documents_and_taiwan_routing_survive_runtime_normalization(self):
        documents = {row["path"]: row for row in self.batch["reader_documents"]}
        cleanups = {
            row["path"]: row
            for row in read("localization/reader-language-cleanup-20261029.json")["reader_documents"]
        }
        current_cleanup = read("localization/reader-language-cleanup-20261031.json")
        current_surfaces = {row["path"]: row for row in current_cleanup["reader_surfaces"]}
        self.assertEqual(set(documents), {"README.md", "REPOSITORY_GUIDE.md", "locales/zh-TW/README.md"})
        self.assertEqual(set(cleanups), set(documents))
        self.assertTrue(set(documents).issubset(current_surfaces))
        self.assertEqual(current_cleanup["prior_revision"], "b0367db7a5f817462020670bfafdfef3dd020fab")
        cleanup_record = read("localization/reader-language-cleanup-20261029.json")
        self.assertEqual(cleanup_record["prior_revision"], "454c0b6a193b2503749a5f579c882311631edc41")
        for path, evidence in documents.items():
            prior = subprocess.check_output(["git", "show", f"{BASE}:{path}"], cwd=ROOT)
            cleanup_prior = subprocess.check_output(
                ["git", "show", f"{cleanup_record['prior_revision']}:{path}"], cwd=ROOT
            )
            current = (ROOT / path).read_bytes()
            self.assertEqual(hashlib.sha256(prior).hexdigest(), evidence["before_sha256"])
            cleanup = cleanups[path]
            self.assertRegex(cleanup["before_sha256"], r"^[0-9a-f]{64}$")
            self.assertRegex(cleanup["after_sha256"], r"^[0-9a-f]{64}$")
            self.assertEqual(hashlib.sha256(cleanup_prior).hexdigest(), cleanup["before_sha256"])
            self.assertEqual(evidence["after_sha256"], cleanup["before_sha256"])
            main_prior = subprocess.check_output(
                ["git", "show", f"{current_cleanup['prior_revision']}:{path}"], cwd=ROOT
            )
            self.assertEqual(hashlib.sha256(main_prior).hexdigest(), cleanup["after_sha256"])
            self.assertEqual(current_surfaces[path]["before_sha256"], cleanup["after_sha256"])
            self.assertEqual(hashlib.sha256(current).hexdigest(), current_surfaces[path]["after_sha256"])

        item = self.items["TW-21-011"]
        normalized, _ = normalize_reader_item(item)
        self.assertEqual(normalized, item)
        self.assertIn("赴陸港澳動態登錄及急難聯絡方式", normalized["body"])
        self.assertIn("聯絡對象不必一定是家人", normalized["body"])


if __name__ == "__main__":
    unittest.main()

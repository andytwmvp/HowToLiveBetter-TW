"""第二章尚未發布健康草稿的來源再審追蹤契約。"""
import copy
import json
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import retroactive_audit as audit

ROOT = audit.ROOT
BASE = "171783959adfc988ad6cd2cff04cfcdf21a745f6"
IDS = {"TW-02-006", "TW-02-008", "TW-02-021", "TW-02-045"}


def read(relative):
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


class ChapterTwoHealthDraftRecheckTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = read("localization/manifest.json")
        cls.runtime = read("localization/tw-edition/runtime.json")
        cls.register = read("localization/retroactive-review-register-20261019.json")
        cls.chapter = read("localization/tw-edition/chapters/02.json")

    def test_selected_topics_remain_pending_and_unpublished(self):
        entries = {entry["id"]: entry for entry in self.manifest["entries"]}
        runtime_ids = {item["id"] for item in self.runtime["items"]}
        for key in IDS:
            with self.subTest(id=key):
                self.assertEqual(entries[key]["status"], "pending")
                self.assertIsNone(entries[key]["target_path"])
                self.assertEqual(entries[key]["sources"], [])
                self.assertNotIn(key, runtime_ids)

    def test_draft_rechecks_are_append_only_and_separate_from_published_rechecks(self):
        rows = self.register.get("draft_substantive_rechecks")
        self.assertIsInstance(rows, list)
        self.assertTrue(IDS.issubset({row["id"] for row in rows}))
        self.assertTrue(all(row["status"] == "ai_source_rechecked_draft_unpublished" for row in rows))
        self.assertTrue(all(row["prior_revision"] == BASE for row in rows))

    def test_drafts_use_taiwan_current_law_and_frequency_limits(self):
        rows = {f"TW-02-{row[0]:03}": row for row in self.chapter["entries"]}
        self.assertIn("在學國中生為2.1%", rows["TW-02-006"][2])
        self.assertIn("不得單獨處罰持有", rows["TW-02-006"][4])
        self.assertIn("8,522", rows["TW-02-008"][2])
        self.assertIn("不等於嚼檳榔造成的個人機率", rows["TW-02-008"][4])
        self.assertIn("0800-255959", rows["TW-02-021"][3])
        self.assertIn("停止飲酒前先找醫療人員", rows["TW-02-021"][4])
        self.assertIn("約25%", rows["TW-02-045"][2])
        self.assertIn("2017-2020", rows["TW-02-045"][2])
        self.assertIn("不是每年新發病例或個人發病機率", rows["TW-02-045"][4])

    def test_oral_bleeding_warning_has_a_specific_official_source(self):
        row = next(row for row in self.chapter["entries"] if row[0] == 8)
        self.assertIn("出血", row[3])
        self.assertIn("oral_bleeding_warning", row[5].split())
        record = next(row for row in self.register["draft_substantive_rechecks"] if row["id"] == "TW-02-008")
        review = read(record["review_path"])
        check = next(source for source in review["source_checks"] if source["source_id"] == "oral_bleeding_warning")
        self.assertIn("出血", check["supporting_passage"])
        self.assertIn("hpa.gov.tw", check["url"])

    def test_each_draft_review_preserves_before_after_row_and_source_evidence(self):
        records = {row["id"]: row for row in self.register["draft_substantive_rechecks"]}
        rows = {f"TW-02-{row[0]:03}": row for row in self.chapter["entries"]}
        for key in IDS:
            with self.subTest(id=key):
                record = records[key]
                review = read(record["review_path"])
                self.assertEqual(review["id"], key)
                self.assertEqual(review["original_draft"], self._row_at(BASE, key))
                self.assertEqual(review["current_draft"], rows[key])
                self.assertEqual(record["before_sha256"], review["before_sha256"])
                self.assertEqual(record["after_sha256"], review["after_sha256"])
                self.assertTrue(record["taiwan_context"].strip())
                self.assertTrue(record["frequency_assessment"].strip())
                self.assertTrue(record["changes"].strip())
                self.assertTrue(record["unresolved_questions"])
                self.assertTrue(review["source_checks"])
                for source in review["source_checks"]:
                    self.assertTrue(source["claim"])
                    self.assertTrue(source["supporting_passage"])
                    self.assertEqual(source["accessed_at"], "2026-10-31")
                    self.assertTrue(source["retrieval_method"])

    def test_draft_rechecks_stay_separate_from_published_records(self):
        records = audit.validate_draft_recheck_records(ROOT, self.register, self.manifest, self.runtime)
        self.assertEqual(len(records), len(self.register["draft_substantive_rechecks"]))
        self.assertTrue(IDS.issubset({item["id"] for item in records}))
        self.assertTrue(IDS.isdisjoint({item["id"] for item in self.register["substantive_rechecks"]}))
        self.assertFalse(audit.load(ROOT, "localization/tw-edition/coverage.json")["publication_ready"])

    def test_audit_rejects_a_draft_recheck_if_manifest_or_runtime_promotes_it(self):
        validator = getattr(audit, "validate_draft_recheck_records", None)
        self.assertTrue(callable(validator))
        published = copy.deepcopy(self.manifest)
        next(entry for entry in published["entries"] if entry["id"] == "TW-02-006")["status"] = "verified"
        with self.assertRaises(ValueError):
            validator(ROOT, self.register, published, self.runtime)

        published = copy.deepcopy(self.runtime)
        published["items"].append({"id": "TW-02-006"})
        with self.assertRaises(ValueError):
            validator(ROOT, self.register, self.manifest, published)

    def test_audit_rejects_a_review_with_a_different_prior_revision(self):
        record = next(row for row in self.register["draft_substantive_rechecks"] if row["id"] == "TW-02-008")
        original_load = audit.load

        def load_with_wrong_revision(root, relative):
            value = original_load(root, relative)
            if relative == record["review_path"]:
                value["prior_revision"] = "0" * 40
            return value

        with patch.object(audit, "load", side_effect=load_with_wrong_revision):
            with self.assertRaisesRegex(ValueError, "證據檔與登錄"):
                audit.validate_draft_recheck_records(ROOT, self.register, self.manifest, self.runtime)

    @staticmethod
    def _row_at(revision, key):
        raw = subprocess.check_output(
            ["git", "show", f"{revision}:localization/tw-edition/chapters/02.json"],
            cwd=ROOT,
            text=True,
        )
        chapter = json.loads(raw)
        row = next(row for row in chapter["entries"] if f"TW-02-{row[0]:03}" == key)
        return row


if __name__ == "__main__":
    unittest.main()

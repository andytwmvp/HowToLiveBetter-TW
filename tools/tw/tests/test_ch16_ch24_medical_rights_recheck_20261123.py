"""第16、24章慢箋、健保費用及身心障礙申請權益歷史再審契約。"""

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
from review_contract import validate_runtime


BASELINE = "1ca0a13d2988210d930afab9444e8589d36d4709"
DATE = "2026-11-23"
DUE = "2027-02-23"
IDS = ("TW-16-005", "TW-24-002", "TW-24-010", "TW-24-015")
REGISTER_PATH = "localization/retroactive-review-register-20261019.json"
BUNDLE_PATH = "localization/tw-edition/sources/ch16-24-medical-rights-recheck-20261123.json"
BATCH_PATH = "localization/ch16-24-medical-rights-recheck-20261123.json"
NEW_SOURCE_IDS = (
    "access_disability_process_20261123",
    "access_disability_online_20261123",
    "ch24_selfpay_compare_tool_20261123",
    "ch24_selfpay_compare_guide_20261123",
)


def read_json(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def git_bytes(revision, path):
    return subprocess.check_output(
        ["git", "show", f"{revision}:{path}"], cwd=ROOT
    )


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


class MedicalRightsRecheckTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.runtime = validate_runtime()
        cls.runtime_items = {row["id"]: row for row in cls.runtime["items"]}
        cls.runtime_sources = {row["id"]: row for row in cls.runtime["sources"]}
        cls.manifest = {
            row["id"]: row for row in read_json("localization/manifest.json")["entries"]
        }
        cls.reviews = {
            item_id: read_json(f"localization/reviews/{item_id}.json")
            for item_id in IDS
        }
        cls.register = read_json(REGISTER_PATH)
        cls.rows = cls.register["substantive_rechecks"]
        cls.batch_rows = {
            item_id: next(
                row for row in reversed(cls.rows)
                if row["id"] == item_id and row["reviewed_at"] == DATE
            )
            for item_id in IDS
        }
        cls.bundle = read_json(BUNDLE_PATH)
        cls.batch = read_json(BATCH_PATH)
        cls.coverage = read_json("localization/tw-edition/coverage.json")
        cls.live_coverage = audit_drafts()

    def test_each_review_preserves_prior_version_and_hash_chain(self):
        self.assertEqual(self.batch["baseline_main_sha"], BASELINE)
        self.assertEqual(self.batch["reviewed_at"], DATE)
        old_manifest = {
            row["id"]: row
            for row in json.loads(git_bytes(BASELINE, "localization/manifest.json"))["entries"]
        }
        old_runtime = json.loads(git_bytes(BASELINE, "localization/tw-edition/runtime.json"))
        old_items = {row["id"]: row for row in old_runtime["items"]}

        for item_id in IDS:
            with self.subTest(id=item_id):
                entry = self.manifest[item_id]
                review = self.reviews[item_id]
                record = self.batch_rows[item_id]
                batch_item = next(row for row in self.batch["items"] if row["id"] == item_id)
                article_path = entry["target_path"]
                body_bytes = (ROOT / article_path).read_bytes()
                body_sha = digest(body_bytes)
                old_body = git_bytes(BASELINE, article_path)
                old_review = git_bytes(BASELINE, f"localization/reviews/{item_id}.json")
                old_review_data = json.loads(old_review)

                self.assertEqual(entry["status"], "verified")
                self.assertEqual(review["reviewed_at"], DATE)
                self.assertEqual(review["review_due_at"], DUE)
                self.assertEqual(review["target_path"], article_path)
                self.assertEqual(review["target_sha256"], body_sha)
                self.assertEqual(review["source_reviewed_sha256"], body_sha)
                self.assertEqual(review["after_sha256"], body_sha)
                self.assertEqual(record["after_sha256"], body_sha)
                self.assertEqual(record["before_sha256"], digest(old_body))
                self.assertEqual(record["previous_body"], old_body.decode("utf-8"))
                self.assertEqual(record["prior_review_sha256"], digest(old_review))
                self.assertEqual(record["prior_reviewed_at"], old_review_data["reviewed_at"])
                self.assertEqual(record["prior_revision"], BASELINE)
                self.assertEqual(record["review_sha256"], digest((ROOT / f"localization/reviews/{item_id}.json").read_bytes()))
                self.assertEqual(review["prior_review_sha256"], digest(old_review))
                self.assertEqual(review["before_sha256"], digest(old_body))
                self.assertEqual(review["previous_body"], old_body.decode("utf-8"))
                self.assertEqual(batch_item["before_sha256"], digest(old_body))
                self.assertEqual(batch_item["after_sha256"], body_sha)
                self.assertEqual(batch_item["review_sha256"], digest((ROOT / f"localization/reviews/{item_id}.json").read_bytes()))
                self.assertEqual(review["source_bundle_path"], BUNDLE_PATH)
                self.assertEqual(record["source_bundle_sha256"], digest((ROOT / BUNDLE_PATH).read_bytes()))
                self.assertEqual(review["source_bundle_sha256"], digest((ROOT / BUNDLE_PATH).read_bytes()))
                self.assertEqual(review["source_checks"], record["source_checks"])
                self.assertEqual(review["statistics_assessed"], [])
                self.assertTrue(review["frequency_assessment"])
                self.assertEqual(review["professional_review"]["status"], "pending")
                self.assertFalse(review["professional_review"]["obtained"])
                self.assertEqual(record["status"], "ai_source_rechecked_professional_pending")

                item = self.runtime_items[item_id]
                self.assertEqual(item["body"], body_bytes.decode("utf-8"))
                self.assertEqual(item["source_ids"], entry["sources"])
                self.assertEqual(review["source_ids"], entry["sources"])
                self.assertEqual(record["source_ids"], entry["sources"])
                self.assertEqual(record["review_due_at"], DUE)
                self.assertEqual(old_manifest[item_id]["id"], item_id)
                self.assertEqual(old_items[item_id]["id"], item_id)

    def test_append_only_review_history_and_source_registration(self):
        old_register = json.loads(git_bytes(BASELINE, REGISTER_PATH))
        old_rows = old_register["substantive_rechecks"]
        self.assertEqual(self.rows[:len(old_rows)], old_rows)
        appended = self.rows[len(old_rows):]
        this_batch = [row for row in appended if row["reviewed_at"] == DATE]
        self.assertEqual([row["id"] for row in this_batch], list(IDS))
        self.assertEqual(len(this_batch), len(IDS))

        old_runtime = json.loads(git_bytes(BASELINE, "localization/tw-edition/runtime.json"))
        old_sources = {row["id"]: row for row in old_runtime["sources"]}
        current_sources = self.runtime_sources
        changed_existing = {
            key for key, value in old_sources.items()
            if current_sources.get(key) != value
        }
        self.assertEqual(changed_existing, set())
        self.assertEqual(
            {key for key in current_sources if key not in old_sources},
            set(NEW_SOURCE_IDS),
        )
        self.assertEqual(self.batch["new_source_ids"], list(NEW_SOURCE_IDS))
        self.assertEqual(self.batch["updated_source_ids"], [])
        self.assertEqual([row[0] for row in self.bundle["sources"]], list(NEW_SOURCE_IDS))
        self.assertEqual(self.bundle["checked_at"], DATE)
        self.assertEqual(self.batch["source_bundle_sha256"], digest((ROOT / BUNDLE_PATH).read_bytes()))

        gov_review = self.reviews["TW-24-010"]
        gov_source = current_sources["access_disability_process_20261123"]
        self.assertEqual(gov_source["accessed_at"], DATE)
        self.assertIn("3家（含）以上", gov_source["supports"])
        exact_check = next(row for row in gov_review["source_checks"] if row["source_id"] == "access_disability_process_20261123")
        self.assertIn("3家（含）以上", exact_check["supporting_passage"])
        self.assertIn("直接開頁回403", exact_check["retrieval_method"])
        retired = gov_review["retired_sources"]
        self.assertEqual(len(retired), 1)
        self.assertEqual(retired[0]["id"], "ch24_disability")
        self.assertEqual(retired[0]["replacement_ids"], ["access_disability_process_20261123"])
        self.assertEqual(retired[0]["disposition"], "replaced")
        self.assertEqual(
            self.batch["retired_source_records"],
            [self.reviews["TW-16-005"]["retired_sources"][0], retired[0]],
        )

    def test_runtime_manifest_review_and_sources_stay_synchronized(self):
        markdown_url = re.compile(r"https://[^)\s]+")
        for item_id in IDS:
            with self.subTest(id=item_id):
                entry = self.manifest[item_id]
                item = self.runtime_items[item_id]
                review = self.reviews[item_id]
                body = item["body"]
                source_ids = entry["sources"]
                self.assertEqual(item["source_ids"], source_ids)
                self.assertEqual(review["source_ids"], source_ids)
                self.assertTrue(set(source_ids).issubset(self.runtime_sources))
                checks = {row["source_id"]: row for row in review["source_checks"]}
                self.assertEqual(set(checks), set(source_ids))
                self.assertEqual(
                    {self.runtime_sources[key]["url"] for key in source_ids},
                    set(markdown_url.findall(body)),
                )
                for source_id in source_ids:
                    source = self.runtime_sources[source_id]
                    check = checks[source_id]
                    self.assertEqual(check["url"], source["url"])
                    self.assertNotEqual(check["claim"], check["supporting_passage"])
                    self.assertGreaterEqual(len(check["supporting_passage"].strip()), 30)
                    self.assertEqual(check["accessed_at"], DATE)

    def test_reader_copy_contains_specific_taiwan_actions_and_no_process_log(self):
        bodies = {item_id: self.runtime_items[item_id]["body"] for item_id in IDS}
        self.assertIn("全民健康保險醫療辦法第22至25條", bodies["TW-16-005"])
        self.assertNotIn("第22、26、28條", bodies["TW-16-005"])
        self.assertNotIn("2026-10-21實讀", bodies["TW-24-002"])
        self.assertIn("掛號費不是這張表列的基本部分負擔", bodies["TW-24-002"])
        self.assertIn("一吋半身照片三張", bodies["TW-24-010"])
        self.assertIn("須至三家以上鑑定醫院", bodies["TW-24-010"])
        self.assertIn("同一障礙類別因不同鑑定向度", bodies["TW-24-010"])
        self.assertIn("健保署的「自付差額醫材比價查詢」", bodies["TW-24-015"])
        self.assertIn("院所上傳的價格", bodies["TW-24-015"])
        for item_id, body in bodies.items():
            with self.subTest(id=item_id):
                self.assertNotRegex(body, r"(批次摘要|AI輔助審查|本次再審|PR\s*#\d+|內部審閱)")

    def test_coverage_snapshot_counts_real_changes_without_claiming_publication_readiness(self):
        old_coverage = json.loads(git_bytes(BASELINE, "localization/tw-edition/coverage.json"))
        old_runtime = json.loads(git_bytes(BASELINE, "localization/tw-edition/runtime.json"))
        old_register = json.loads(git_bytes(BASELINE, REGISTER_PATH))
        before = self.batch["counts_before"]
        after = self.batch["counts_after"]
        self.assertEqual(self.coverage, self.live_coverage)
        self.assertEqual(before["verified_core_entries"], old_coverage["core_reviewed_entries"])
        self.assertEqual(before["publication_completed_entries"], old_coverage["publication_completed_entries"])
        self.assertEqual(before["runtime_items"], len(old_runtime["items"]))
        self.assertEqual(before["runtime_sources"], len(old_runtime["sources"]))
        self.assertEqual(before["source_registry"], old_coverage["registry_sources"])
        self.assertEqual(before["coverage_json_files"], old_coverage["json_files_checked"])
        self.assertEqual(before["substantive_rechecks"], len(old_register["substantive_rechecks"]))

        self.assertEqual(after["verified_core_entries"], self.coverage["core_reviewed_entries"])
        self.assertEqual(after["publication_completed_entries"], self.coverage["publication_completed_entries"])
        self.assertEqual(after["runtime_items"], len(self.runtime["items"]))
        self.assertEqual(after["runtime_sources"], len(self.runtime["sources"]))
        self.assertEqual(after["source_registry"], self.coverage["registry_sources"])
        self.assertEqual(after["coverage_json_files"], self.coverage["json_files_checked"])
        self.assertEqual(after["unresolved_source_id_categories"], len(self.coverage["unresolved_source_ids"]))
        self.assertEqual(after["unresolved_reference_occurrences"], self.coverage["unresolved_reference_occurrences"])
        self.assertEqual(after["substantive_rechecks"], len(self.rows))
        self.assertEqual(after["publication_ready"], self.coverage["publication_ready"])
        self.assertFalse(after["publication_ready"])
        self.assertEqual(after["verified_core_entries"], before["verified_core_entries"])
        self.assertEqual(after["runtime_items"], before["runtime_items"])
        self.assertEqual(after["substantive_rechecks"], before["substantive_rechecks"] + len(IDS))
        self.assertEqual(after["runtime_sources"], before["runtime_sources"] + len(NEW_SOURCE_IDS))
        self.assertEqual(after["source_registry"], before["source_registry"] + len(NEW_SOURCE_IDS))
        self.assertEqual(after["coverage_json_files"], before["coverage_json_files"] + 2)


if __name__ == "__main__":
    unittest.main()

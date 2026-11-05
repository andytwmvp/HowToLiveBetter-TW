"""第13章四篇安全主題的台灣實質再審與讀者內容契約。"""
import hashlib
import json
import re
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from review_contract import ROOT, validate_runtime
from retroactive_audit import validate_recheck_history

BASE = "9a5a971e2ee62d872bc15465837614b6059775fe"
BATCH = "localization/ch13-conflict-wildlife-dental-recheck-20261106.json"
SOURCE_INDEX = "localization/tw-edition/sources/ch13-conflict-wildlife-dental-recheck-20261106.json"
IDS = ("TW-13-031", "TW-13-036", "TW-13-037", "TW-13-048")
NEW_SOURCE_IDS = (
    "animal_wildlife_wish_reports", "animal_dog_chpb_2026", "animal_dog_moa_1959",
    "conflict_victim_avs_counseling", "conflict_victim_enforcement_rules",
    "conflict_victim_legal_history", "urgent_dental_iadt_index_20261106",
    "urgent_dental_mohw_directory_20261106", "urgent_dental_mohw_regular_20250303",
)


def read_json(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def git_bytes(revision, path):
    return subprocess.check_output(["git", "show", f"{revision}:{path}"], cwd=ROOT)


def sha(data):
    return hashlib.sha256(data).hexdigest()


class Chapter13ConflictWildlifeDentalRecheckTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.runtime = validate_runtime()
        cls.items = {item["id"]: item for item in cls.runtime["items"]}
        cls.sources = {source["id"]: source for source in cls.runtime["sources"]}
        cls.manifest = {entry["id"]: entry for entry in read_json("localization/manifest.json")["entries"]}
        cls.reviews = {item_id: read_json(f"localization/reviews/{item_id}.json") for item_id in IDS}
        cls.register = read_json("localization/retroactive-review-register-20261019.json")
        cls.batch = read_json(BATCH)
        cls.batch_items = {item["id"]: item for item in cls.batch["items"]}
        cls.baseline_runtime = json.loads(git_bytes(BASE, "localization/tw-edition/runtime.json"))
        cls.baseline_reviews = {
            item_id: git_bytes(BASE, f"localization/reviews/{item_id}.json") for item_id in IDS
        }

    def test_four_rechecks_match_formal_content_and_append_only_history(self):
        self.assertEqual(self.batch["baseline_main_sha"], BASE)
        self.assertEqual(self.batch["reviewed_at"], "2026-11-06")
        self.assertEqual(self.batch["review_due_at"], "2027-02-06")
        self.assertEqual(set(self.batch_items), set(IDS))
        self.assertTrue(self.batch["professional_review"]["required"])
        self.assertFalse(self.batch["professional_review"]["obtained"])

        baseline_items = {item["id"]: item for item in self.baseline_runtime["items"]}
        for item_id in IDS:
            with self.subTest(item_id=item_id):
                item = self.items[item_id]
                record = self.batch_items[item_id]
                review = self.reviews[item_id]
                entry = self.manifest[item_id]
                body_path = ROOT / item["target_path"]
                body_bytes = body_path.read_bytes()
                body = body_bytes.decode("utf-8")
                body_sha = sha(body_bytes)
                history = [row for row in self.register["substantive_rechecks"]
                           if row["id"] == item_id and row["reviewed_at"] == "2026-11-06"]
                old_item = baseline_items[item_id]

                self.assertEqual(len(history), 1)
                self.assertEqual(history[0], record)
                self.assertEqual(record["status"], "ai_source_rechecked_professional_pending")
                self.assertEqual(record["prior_revision"], BASE)
                self.assertEqual(record["previous_body"], old_item["body"])
                self.assertEqual(record["before_sha256"], sha(old_item["body"].encode("utf-8")))
                self.assertEqual(record["after_sha256"], body_sha)
                self.assertEqual(review["target_sha256"], body_sha)
                self.assertEqual(review["source_reviewed_sha256"], body_sha)
                self.assertEqual(review["source_checks"], record["source_checks"])
                self.assertEqual(review["limits"], record["limits"])
                self.assertEqual(item["limits"], review["limits"][0])
                self.assertEqual(item["body"], body)
                self.assertEqual(entry["sources"], item["source_ids"])
                self.assertEqual(entry["status"], "verified")
                self.assertEqual(item["reviewed_at"], "2026-11-06")
                self.assertEqual(item["review_due_at"], "2027-02-06")
                self.assertEqual(sha(self.baseline_reviews[item_id]), record["prior_review_sha256"])
                self.assertEqual(old_item["target_path"], item["target_path"])
                self.assertEqual(old_item["eligibility"], item["eligibility"])
                self.assertEqual(old_item["review_status"], item["review_status"])

                urls = set(re.findall(r"\]\((https?://[^)]+)\)", body))
                source_urls = {self.sources[source_id]["url"] for source_id in item["source_ids"]}
                checked_urls = {check["url"] for check in review["source_checks"]}
                self.assertEqual(urls, source_urls)
                self.assertEqual(urls, checked_urls)
                self.assertEqual([line for line in body.splitlines() if line.startswith("# ")], ["# " + item["title"]])
                self.assertNotRegex(body, r"(?:本次(?:逐主張|來源|實質)|本批|AI輔助|專業審閱仍待|review|SHA-256)")
                self.assertTrue(record["statistics_assessed"])
                for statistic in record["statistics_assessed"]:
                    for field in ("period", "geographic_scope", "population", "numerator", "denominator",
                                  "event_definition", "data_type", "accessed_at", "limitations"):
                        self.assertTrue(statistic.get(field), f"{item_id} missing {field}")
                validate_recheck_history(ROOT, record, item)

    def test_retired_sources_are_unchanged_and_prior_order_is_preserved(self):
        old_sources = {source["id"]: source for source in self.baseline_runtime["sources"]}
        for item_id, record in self.batch_items.items():
            old_ids = record["previous_source_ids"]
            retired = {row["id"]: row for row in record["retired_sources"]}
            retained = [source_id for source_id in old_ids if source_id not in retired]
            current_ids = self.items[item_id]["source_ids"]
            self.assertEqual(current_ids[:len(retained)], retained)
            self.assertEqual(set(old_ids) - set(current_ids), set(retired))
            for source_id, row in retired.items():
                self.assertEqual(self.sources[source_id], old_sources[source_id])
                self.assertEqual(row["prior_source_sha256"], sha(json.dumps(
                    old_sources[source_id], ensure_ascii=False, sort_keys=True).encode("utf-8")))
                self.assertTrue(set(row["replacement_ids"]).issubset(current_ids))

    def test_new_sources_and_live_counts_are_recorded(self):
        source_rows = read_json(SOURCE_INDEX)["sources"]
        self.assertEqual({row[0] for row in source_rows}, set(NEW_SOURCE_IDS))
        for row in source_rows:
            source = self.sources[row[0]]
            self.assertEqual(row, [source["id"], source["title"], source["url"], source["supports"]])
        counts = self.batch["counts_after"]
        coverage = read_json("localization/tw-edition/coverage.json")
        self.assertGreaterEqual(len(self.runtime["items"]), counts["runtime_items"])
        self.assertGreaterEqual(len(self.runtime["sources"]), counts["runtime_sources"])
        self.assertGreaterEqual(coverage["registry_sources"], counts["registry_sources"])
        self.assertGreaterEqual(coverage["json_files_checked"], counts["json_files"])
        self.assertGreaterEqual(len(self.register["substantive_rechecks"]), counts["substantive_rechecks"])
        self.assertFalse(coverage["publication_ready"])
        self.assertEqual(self.batch["new_source_ids"], list(NEW_SOURCE_IDS))

    def test_taiwan_risk_and_frequency_boundaries_are_reader_visible(self):
        bear = self.items["TW-13-031"]["body"]
        robbery = self.items["TW-13-036"]["body"]
        fight = self.items["TW-13-037"]["body"]
        tooth = self.items["TW-13-048"]["body"]
        self.assertIn("所在地1999", bear)
        self.assertIn("1959", bear)
        self.assertIn("所有暴力事件數", robbery)
        self.assertIn("503件", robbery)
        self.assertIn("130件", robbery)
        self.assertIn("118件", robbery)
        self.assertIn("2024年9月", robbery)
        self.assertIn("第24條", fight)
        self.assertIn("2023年7月1日", fight)
        self.assertIn("每次以1小時為原則，最多3次", fight)
        self.assertIn("19.9%", tooth)
        self.assertIn("6,312名", tooth)
        self.assertIn("不是整顆恆牙脫落的發生率", tooth)
        self.assertNotIn("AI輔助", bear + robbery + fight + tooth)
        self.assertNotIn("批次", bear + robbery + fight + tooth)


if __name__ == "__main__":
    unittest.main()

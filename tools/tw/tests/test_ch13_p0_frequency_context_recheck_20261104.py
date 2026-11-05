"""驗證第13章四篇高風險急症再審的台灣證據與追溯鏈。"""
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


BASE = "ce03f62026efddfe4d59aeb87fb75a66c430ffd2"
BATCH_PATH = "localization/ch13-p0-frequency-context-20261104.json"
SOURCE_PATH = "localization/tw-edition/sources/ch13-p0-frequency-context-20261104.json"
ITEM_IDS = ("TW-13-002", "TW-13-006", "TW-13-009", "TW-13-011")
NEW_SOURCE_IDS = (
    "ch13_falls_hpa_nhis_2021",
    "ch13_headinjury_nhia_2023",
    "ch13_headinjury_nice_ng232",
    "ch13_acute_glaucoma_tsem_2025",
    "ch13_pacg_tmu_nhi_2008",
    "ch13_thunderclap_ntuh_2023_epaper",
    "ch13_vte_taiwan_nhi_2010",
)


def read_json(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


class Chapter13P0FrequencyContextRecheckTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.runtime = validate_runtime()
        cls.runtime_items = {item["id"]: item for item in cls.runtime["items"]}
        cls.runtime_sources = {source["id"]: source for source in cls.runtime["sources"]}
        cls.manifest = read_json("localization/manifest.json")
        cls.manifest_items = {item["id"]: item for item in cls.manifest["entries"]}
        cls.reviews = {
            item_id: read_json(f"localization/reviews/{item_id}.json")
            for item_id in ITEM_IDS
        }
        cls.register = read_json("localization/retroactive-review-register-20261019.json")
        cls.batch = read_json(BATCH_PATH)
        cls.batch_items = {item["id"]: item for item in cls.batch["items"]}
        cls.source_rows = read_json(SOURCE_PATH)["sources"]
        cls.baseline_runtime = json.loads(subprocess.check_output(
            ["git", "show", f"{BASE}:localization/tw-edition/runtime.json"],
            cwd=ROOT,
            text=True,
        ))
        cls.baseline_reviews = {
            item_id: json.loads(subprocess.check_output(
                ["git", "show", f"{BASE}:localization/reviews/{item_id}.json"],
                cwd=ROOT,
                text=True,
            ))
            for item_id in ITEM_IDS
        }
        cls.baseline_sources = {
            source["id"]: source for source in cls.baseline_runtime["sources"]
        }

    def test_batch_records_match_reader_content_sources_and_hashes(self):
        self.assertEqual(self.batch["baseline_main_sha"], BASE)
        self.assertEqual(self.batch["reviewed_at"], "2026-11-04")
        self.assertEqual(self.batch["review_due_at"], "2027-02-04")
        self.assertEqual(set(self.batch_items), set(ITEM_IDS))
        self.assertEqual(self.batch["new_source_ids"], list(NEW_SOURCE_IDS))
        self.assertEqual(self.batch["professional_review"]["obtained"], False)
        self.assertTrue(self.batch["professional_review"]["required"])

        source_rows = {row[0]: row for row in self.source_rows}
        self.assertEqual(set(source_rows), set(NEW_SOURCE_IDS))
        for source_id, row in source_rows.items():
            source = self.runtime_sources[source_id]
            self.assertEqual(row, [source["id"], source["title"], source["url"], source["supports"]])

        for item_id in ITEM_IDS:
            with self.subTest(item_id=item_id):
                item = self.runtime_items[item_id]
                record = self.batch_items[item_id]
                review = self.reviews[item_id]
                manifest_item = self.manifest_items[item_id]
                history = [
                    row for row in self.register["substantive_rechecks"]
                    if row["id"] == item_id and row["reviewed_at"] == self.batch["reviewed_at"]
                ]
                self.assertEqual(len(history), 1)
                self.assertEqual(history[0], record)
                self.assertEqual(record["status"], "ai_source_rechecked_professional_pending")
                self.assertEqual(record["review_due_at"], self.batch["review_due_at"])

                body_path = ROOT / item["target_path"]
                body = body_path.read_text(encoding="utf-8")
                body_sha = hashlib.sha256(body_path.read_bytes()).hexdigest()
                self.assertEqual(body, item["body"])
                self.assertEqual(body_sha, record["after_sha256"])
                self.assertEqual(body_sha, review["target_sha256"])
                self.assertEqual(body_sha, review["source_reviewed_sha256"])
                self.assertEqual(review["source_checks"], record["source_checks"])
                self.assertEqual(review["reviewed_at"], record["reviewed_at"])
                self.assertEqual(review["review_due_at"], record["review_due_at"])
                self.assertEqual(review["reader_copy_cleanup"], self.baseline_reviews[item_id]["reader_copy_cleanup"])
                self.assertEqual(manifest_item["target_path"], item["target_path"])
                self.assertEqual(manifest_item["sources"], item["source_ids"])
                self.assertEqual(manifest_item["status"], "verified")

                source_ids = set(record["source_ids"])
                body_urls = set(re.findall(r"\]\((https?://[^)]+)\)", body))
                review_urls = {check["url"] for check in review["source_checks"]}
                runtime_urls = {self.runtime_sources[source_id]["url"] for source_id in source_ids}
                self.assertEqual(body_urls, runtime_urls)
                self.assertEqual(review_urls, runtime_urls)
                self.assertEqual(set(item["source_ids"]), source_ids)
                self.assertNotRegex(
                    body,
                    r"(?:批次摘要|PR\s*#\d+|CI\s*(?:成功|通過)|(?:本次|本輪).{0,16}(?:AI|審查|再審|核對))",
                )
                validate_recheck_history(ROOT, record, item)

    def test_retired_sources_are_preserved_and_source_order_is_stable(self):
        for item_id in ITEM_IDS:
            record = self.batch_items[item_id]
            previous_ids = record["previous_source_ids"]
            retired = {row["id"]: row for row in record["retired_sources"]}
            source_ids = record["source_ids"]
            retained = [source_id for source_id in previous_ids if source_id not in retired]
            self.assertEqual(source_ids[:len(retained)], retained)
            self.assertEqual(set(previous_ids) - set(source_ids), set(retired))
            for source_id, row in retired.items():
                self.assertEqual(self.runtime_sources[source_id], self.baseline_sources[source_id])
                self.assertEqual(
                    row["prior_source_sha256"],
                    hashlib.sha256(json.dumps(
                        self.baseline_sources[source_id],
                        ensure_ascii=False,
                        sort_keys=True,
                    ).encode("utf-8")).hexdigest(),
                )

    def test_frequency_and_reader_action_are_scoped_to_the_evidence(self):
        fall = self.batch_items["TW-13-002"]
        glaucoma = self.batch_items["TW-13-006"]
        thunderclap = self.batch_items["TW-13-009"]
        vte = self.batch_items["TW-13-011"]

        self.assertIn("6,685", fall["frequency_assessment"])
        self.assertIn("7.9%", fall["frequency_assessment"])
        self.assertIn("信賴區間", fall["frequency_assessment"])
        self.assertIn("不涵蓋未受傷或未就醫跌倒", fall["frequency_assessment"])
        self.assertIn("4,722", glaucoma["frequency_assessment"])
        self.assertIn("9.48", glaucoma["frequency_assessment"])
        self.assertIn("1997至2003年", glaucoma["frequency_assessment"])
        self.assertIn("住院率", glaucoma["frequency_assessment"])
        self.assertIn("未找到", thunderclap["frequency_assessment"])
        self.assertIn("分母", thunderclap["frequency_assessment"])
        self.assertIn("5,347", vte["frequency_assessment"])
        self.assertIn("15.9", vte["frequency_assessment"])
        self.assertIn("每10萬人年", vte["frequency_assessment"])
        self.assertIn("總人年", vte["frequency_assessment"])

        bodies = {item_id: self.runtime_items[item_id]["body"] for item_id in ITEM_IDS}
        self.assertIn("儘快到急診評估", bodies["TW-13-002"])
        self.assertIn("不是骨折或頭部出血比例", bodies["TW-13-002"])
        self.assertIn("白天", bodies["TW-13-006"])
        self.assertIn("不等於目前急性發作率", bodies["TW-13-006"])
        self.assertIn("撥打119", bodies["TW-13-009"])
        self.assertIn("無法估算", bodies["TW-13-009"])
        self.assertIn("立即撥打119", bodies["TW-13-011"])
        self.assertIn("不是單側腿腫者的罹病機率", bodies["TW-13-011"])

    def test_counts_and_runtime_are_synchronized(self):
        # This batch records a historical snapshot; later batches may add reader sources.
        self.assertGreaterEqual(len(self.runtime["items"]), self.batch["counts_after"]["runtime_items"])
        self.assertGreaterEqual(len(self.runtime["sources"]), self.batch["counts_after"]["runtime_sources"])
        coverage = read_json("localization/tw-edition/coverage.json")
        self.assertGreaterEqual(coverage["core_reviewed_entries"], self.batch["counts_after"]["core_completed"])
        self.assertGreaterEqual(coverage["registry_sources"], self.batch["counts_after"]["registry_sources"])
        self.assertGreaterEqual(coverage["json_files_checked"], self.batch["counts_after"]["json_files"])
        self.assertGreaterEqual(self.runtime["updated_at"], self.batch["reviewed_at"])
        self.assertGreaterEqual(self.runtime["review_due_at"], self.batch["review_due_at"])


if __name__ == "__main__":
    unittest.main()

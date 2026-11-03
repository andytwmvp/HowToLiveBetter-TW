"""驗證第13章四篇急症歷史再審的正文、來源、統計限制與追溯鏈。"""
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


BASE = "d5edd26bd6487ace6f1b94d8ee7a6bf6adc7831b"
BATCH_PATH = "localization/ch13-p0-emergency-recheck-20261104.json"
SOURCE_PATH = "localization/tw-edition/sources/ch13-p0-emergency-recheck-20261104.json"
ITEM_IDS = ("TW-13-004", "TW-13-005", "TW-13-008", "TW-13-010")


def read_json(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


class Chapter13P0EmergencyRecheckTests(unittest.TestCase):
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
        cls.baseline = json.loads(subprocess.check_output(
            ["git", "show", f"{BASE}:localization/tw-edition/runtime.json"],
            cwd=ROOT,
            text=True,
        ))
        cls.baseline_sources = {source["id"]: source for source in cls.baseline["sources"]}

    def test_batch_records_match_runtime_manifest_review_and_hash_edges(self):
        self.assertEqual(self.batch["baseline_main_sha"], BASE)
        self.assertEqual(self.batch["reviewed_at"], "2026-11-04")
        self.assertEqual(self.batch["review_due_at"], "2027-02-04")
        self.assertEqual(set(self.batch_items), set(ITEM_IDS))
        self.assertEqual(self.batch["professional_review"]["obtained"], False)
        self.assertTrue(self.batch["professional_review"]["required"])

        evidence_by_id = {row[0]: row for row in self.source_rows}
        self.assertEqual(set(evidence_by_id), set(self.batch["new_source_ids"]))
        for source_id, row in evidence_by_id.items():
            source = self.runtime_sources[source_id]
            self.assertEqual(row, [source["id"], source["title"], source["url"], source["supports"]])

        for item_id in ITEM_IDS:
            with self.subTest(item_id=item_id):
                item = self.runtime_items[item_id]
                record = self.batch_items[item_id]
                review = self.reviews[item_id]
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
                self.assertEqual(review["reviewed_at"], record["reviewed_at"])
                self.assertEqual(review["review_due_at"], record["review_due_at"])
                self.assertEqual(self.manifest_items[item_id]["target_path"], item["target_path"])
                self.assertEqual(self.manifest_items[item_id]["sources"], item["source_ids"])
                self.assertEqual(self.manifest_items[item_id]["status"], "verified")

                source_ids = set(record["source_ids"])
                body_urls = set(re.findall(r"\]\((https?://[^)]+)\)", body))
                review_urls = {check["url"] for check in review["source_checks"]}
                runtime_urls = {self.runtime_sources[sid]["url"] for sid in source_ids}
                self.assertEqual(body_urls, runtime_urls)
                self.assertEqual(review_urls, runtime_urls)
                self.assertEqual(set(item["source_ids"]), source_ids)
                self.assertNotRegex(
                    body,
                    r"(?:批次摘要|PR\s*#\d+|CI\s*(?:成功|通過)|(?:本次|本輪).{0,16}(?:AI|審查|再審|核對))",
                )
                validate_recheck_history(ROOT, record, item)

    def test_retired_sources_remain_unchanged_and_prior_source_order_is_preserved(self):
        for item_id in ITEM_IDS:
            record = self.batch_items[item_id]
            old_ids = record["previous_source_ids"]
            retired = {row["id"]: row for row in record["retired_sources"]}
            new_ids = record["source_ids"]
            retained = [source_id for source_id in old_ids if source_id not in retired]
            self.assertEqual(new_ids[:len(retained)], retained)
            self.assertEqual(set(old_ids) - set(new_ids), set(retired))
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

    def test_frequency_evidence_is_scoped_and_unknown_rates_are_not_inferred(self):
        dizziness = self.batch_items["TW-13-004"]
        monocular = self.batch_items["TW-13-005"]
        aorta = self.batch_items["TW-13-008"]
        head_injury = self.batch_items["TW-13-010"]

        for record in (dizziness, monocular):
            self.assertIn("未找到", record["frequency_assessment"])
            self.assertIn("分母", record["frequency_assessment"])
            self.assertIn("不", record["frequency_assessment"])
        self.assertIn("12.69", aorta["statistics_assessed"][0]["value"])
        self.assertIn("5.34", aorta["statistics_assessed"][0]["value"])
        self.assertEqual(aorta["statistics_assessed"][0]["period"], "2005至2018年")
        self.assertIn("前兩年", aorta["statistics_assessed"][0]["denominator"])
        self.assertIn("已診斷率", aorta["statistics_assessed"][0]["limitations"])
        self.assertIn("254/14,026", head_injury["statistics_assessed"][0]["value"])
        self.assertIn("4.39", head_injury["statistics_assessed"][0]["period"])
        self.assertIn("不能區分", head_injury["statistics_assessed"][0]["limitations"])

        self.assertIn("短暫單眼視力", self.runtime_items["TW-13-005"]["body"])
        self.assertIn("即使視力已恢復", self.runtime_items["TW-13-005"]["body"])
        self.assertNotIn("未核對", self.runtime_items["TW-13-008"]["body"])
        aorta_checks = self.batch_items["TW-13-008"]["source_checks"]
        femh_check = next(check for check in aorta_checks if check["source_id"] == "ch13_aortic_dissection_femh_202512")
        self.assertIn("未採該文每小時死亡率", femh_check["supporting_passage"])
        self.assertIn("無法區分急性與慢性", self.runtime_items["TW-13-010"]["body"])

    def test_batch_counts_and_source_ids_match_current_exports(self):
        self.assertEqual(self.batch["new_source_ids"], [
            "ch13_nhia_stroke_alert_20231129",
            "ch13_aortic_dissection_taiwan_nhi_2023",
            "ch13_aortic_dissection_femh_202512",
            "ch13_csdh_taiwan_nhi_2014",
        ])
        self.assertEqual(self.batch["counts_after"]["runtime_items"], len(self.runtime["items"]))
        self.assertEqual(self.batch["counts_after"]["runtime_sources"], len(self.runtime["sources"]))
        self.assertEqual(self.batch["counts_after"]["registry_sources"], 1142)
        self.assertEqual(self.batch["counts_after"]["json_files"], 543)
        self.assertEqual(self.runtime["updated_at"], self.batch["reviewed_at"])
        self.assertEqual(self.runtime["review_due_at"], self.batch["review_due_at"])


if __name__ == "__main__":
    unittest.main()

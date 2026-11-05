"""第13章動物暴露、蜱蟲、飲水與骨折再審契約。"""
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


BASE = "48269f3f6b18c0474f5ce78beaa6acd8266011c8"
BATCH = "localization/ch13-rabies-ticks-water-fracture-recheck-20261105.json"
SOURCE_INDEX = "localization/tw-edition/sources/ch13-rabies-ticks-water-fracture-recheck-20261105.json"
IDS = ("TW-13-013", "TW-13-034", "TW-13-035", "TW-13-041")


def read_json(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


class Chapter13RabiesTicksWaterFractureRecheckTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.runtime = validate_runtime()
        cls.items = {item["id"]: item for item in cls.runtime["items"]}
        cls.sources = {source["id"]: source for source in cls.runtime["sources"]}
        cls.manifest = {item["id"]: item for item in read_json("localization/manifest.json")["entries"]}
        cls.reviews = {key: read_json(f"localization/reviews/{key}.json") for key in IDS}
        cls.register = read_json("localization/retroactive-review-register-20261019.json")
        cls.batch = read_json(BATCH)
        cls.batch_items = {item["id"]: item for item in cls.batch["items"]}
        cls.base_runtime = json.loads(subprocess.check_output(
            ["git", "show", f"{BASE}:localization/tw-edition/runtime.json"], cwd=ROOT, text=True
        ))

    def test_four_rechecks_match_current_runtime_and_append_only_history(self):
        self.assertEqual(self.batch["baseline_main_sha"], BASE)
        self.assertEqual(self.batch["reviewed_at"], "2026-11-05")
        self.assertEqual(self.batch["review_due_at"], "2027-02-05")
        self.assertEqual(set(self.batch_items), set(IDS))
        self.assertTrue(self.batch["professional_review"]["required"])
        self.assertFalse(self.batch["professional_review"]["obtained"])

        for key in IDS:
            with self.subTest(item_id=key):
                item = self.items[key]
                record = self.batch_items[key]
                review = self.reviews[key]
                body_path = ROOT / item["target_path"]
                body_bytes = body_path.read_bytes()
                body_sha = hashlib.sha256(body_bytes).hexdigest()
                history = [row for row in self.register["substantive_rechecks"]
                           if row["id"] == key and row["reviewed_at"] == "2026-11-05"]
                self.assertEqual(len(history), 1)
                self.assertEqual(history[0], record)
                self.assertEqual(record["status"], "ai_source_rechecked_professional_pending")
                self.assertEqual(record["prior_revision"], BASE)
                self.assertEqual(body_path.read_text(encoding="utf-8"), item["body"])
                self.assertEqual(body_sha, record["after_sha256"])
                self.assertEqual(body_sha, review["target_sha256"])
                self.assertEqual(body_sha, review["source_reviewed_sha256"])
                self.assertEqual(review["source_checks"], record["source_checks"])
                self.assertEqual(self.manifest[key]["sources"], item["source_ids"])
                self.assertEqual(self.manifest[key]["status"], "verified")
                self.assertEqual(item["reviewed_at"], "2026-11-05")
                self.assertEqual(item["review_due_at"], "2027-02-05")

                urls = {self.sources[sid]["url"] for sid in item["source_ids"]}
                self.assertEqual(set(re.findall(r"\]\((https?://[^)]+)\)", item["body"])), urls)
                self.assertEqual({check["url"] for check in review["source_checks"]}, urls)
                self.assertEqual(item["body"].count("\n## "), 5)
                self.assertNotRegex(item["body"], r"(?:批次摘要|AI輔助|內部審查|本次.{0,12}(?:AI|審查|再審|核對))")
                self.assertTrue(record["statistics_assessed"])
                for statistic in record["statistics_assessed"]:
                    for field in ("period", "geographic_scope", "population", "numerator",
                                  "denominator", "event_definition", "data_type", "accessed_at",
                                  "limitations"):
                        self.assertTrue(statistic[field], f"{key}: missing statistics field {field}")
                validate_recheck_history(ROOT, record, item)

    def test_retired_sources_keep_baseline_objects_and_prior_hashes(self):
        base_sources = {source["id"]: source for source in self.base_runtime["sources"]}
        for key, record in self.batch_items.items():
            old_ids = record["previous_source_ids"]
            retired = {row["id"]: row for row in record["retired_sources"]}
            retained = [source_id for source_id in old_ids if source_id not in retired]
            self.assertEqual([source_id for source_id in record["source_ids"] if source_id in retained], retained)
            self.assertEqual(set(old_ids) - set(record["source_ids"]), set(retired))
            for source_id, row in retired.items():
                self.assertEqual(self.sources[source_id], base_sources[source_id])
                self.assertEqual(row["prior_source_sha256"], hashlib.sha256(
                    json.dumps(base_sources[source_id], ensure_ascii=False, sort_keys=True).encode("utf-8")
                ).hexdigest())

    def test_taiwan_safety_and_frequency_boundaries_are_in_reader_copy(self):
        rabies = self.items["TW-13-013"]["body"]
        ticks = self.items["TW-13-034"]["body"]
        water = self.items["TW-13-035"]["body"]
        fracture = self.items["TW-13-041"]["body"]
        self.assertIn("0800-761-590", rabies)
        self.assertIn("1,332件動物檢體", rabies)
        self.assertIn("不是7名人類感染者", rabies)
        self.assertIn("2026年累計1例", ticks)
        self.assertIn("蜱蟲主要活動季節為4至10月", ticks)
        self.assertIn("不能推算個人感染機率", ticks)
        self.assertIn("沒有列出全部調查件數", water)
        self.assertIn("煮沸、消毒錠和一般濾水器都不能保證安全", water)
        self.assertIn("超過6,500英尺", water)
        self.assertIn("冰敷不是疑似骨折的必要急救步驟", fracture)
        self.assertIn("末端發白發紫或冰冷", fracture)

    def test_new_sources_and_coverage_are_recorded_without_claiming_ready(self):
        source_rows = read_json(SOURCE_INDEX)["sources"]
        coverage = read_json("localization/tw-edition/coverage.json")
        self.assertEqual({row[0] for row in source_rows}, set(self.batch["new_source_ids"]))
        for row in source_rows:
            self.assertEqual(row, [self.sources[row[0]]["id"], self.sources[row[0]]["title"],
                                   self.sources[row[0]]["url"], self.sources[row[0]]["supports"]])
        after = self.batch["counts_after"]
        self.assertEqual(after["core_reviewed"], coverage["core_reviewed_entries"])
        self.assertEqual(after["runtime_items"], len(self.runtime["items"]))
        self.assertGreaterEqual(len(self.runtime["sources"]), after["runtime_sources"])
        self.assertGreaterEqual(coverage["registry_sources"], after["source_registry"])
        self.assertGreaterEqual(coverage["json_files_checked"], after["json_files_checked"])
        self.assertGreaterEqual(len(self.register["substantive_rechecks"]), after["substantive_rechecks"])
        self.assertFalse(coverage["publication_ready"])


if __name__ == "__main__":
    unittest.main()

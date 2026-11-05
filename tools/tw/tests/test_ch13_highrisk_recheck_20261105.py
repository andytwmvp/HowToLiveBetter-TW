"""第13章六篇高風險歷史再審的台灣證據與讀者內容契約。"""
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


BASE = "8591a38edaabd67fde37186a6f259ea2b8998fda"
BATCH = "localization/ch13-highrisk-recheck-20261105.json"
SOURCE_INDEX = "localization/tw-edition/sources/ch13-highrisk-recheck-20261105.json"
IDS = ("TW-13-030", "TW-13-033", "TW-13-038", "TW-13-040", "TW-13-042", "TW-13-047")


def read_json(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


class Chapter13HighRiskRecheckTests(unittest.TestCase):
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

    def test_six_rechecks_match_current_runtime_and_append_only_history(self):
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
                self.assertNotRegex(item["body"], r"(?:批次摘要|未宣稱閱讀|原始研究未讀|PDF第[一二12]頁|本次.{0,12}(?:AI|審查|再審|核對))")
                self.assertTrue(record["statistics_assessed"])
                for statistic in record["statistics_assessed"]:
                    self.assertTrue(statistic["period"])
                    self.assertTrue(statistic["geographic_scope"])
                    self.assertTrue(statistic["population"])
                    self.assertTrue(statistic["numerator"])
                    self.assertTrue(statistic["denominator"])
                    self.assertTrue(statistic["event_definition"])
                    self.assertTrue(statistic["data_type"])
                    self.assertTrue(statistic["limitations"])
                validate_recheck_history(ROOT, record, item)

    def test_retired_sources_keep_baseline_objects_and_prior_hashes(self):
        base_sources = {source["id"]: source for source in self.base_runtime["sources"]}
        for key, record in self.batch_items.items():
            old_ids = record["previous_source_ids"]
            retired = {row["id"]: row for row in record["retired_sources"]}
            retained = [source_id for source_id in old_ids if source_id not in retired]
            self.assertEqual(record["source_ids"][:len(retained)], retained)
            self.assertEqual(set(old_ids) - set(record["source_ids"]), set(retired))
            for source_id, row in retired.items():
                self.assertEqual(self.sources[source_id], base_sources[source_id])
                self.assertEqual(row["prior_source_sha256"], hashlib.sha256(
                    json.dumps(base_sources[source_id], ensure_ascii=False, sort_keys=True).encode("utf-8")
                ).hexdigest())

    def test_taiwan_specific_risk_and_frequency_boundaries_are_in_reader_copy(self):
        quake = self.items["TW-13-030"]["body"]
        altitude = self.items["TW-13-033"]["body"]
        pep = self.items["TW-13-038"]["body"]
        assault = self.items["TW-13-042"]["body"]
        impalement = self.items["TW-13-040"]["body"]
        amputation = self.items["TW-13-047"]["body"]
        self.assertIn("車站", quake)
        self.assertIn("不能當成個人受傷機率", quake)
        self.assertIn("871名", altitude)
        self.assertNotIn("2017年36％公告", altitude)
        self.assertIn("870", pep)
        self.assertNotIn("舊FAQ", pep)
        self.assertIn("9,565", assault)
        self.assertIn("列在名單不代表該院區當下有提供採證", assault)
        self.assertIn("不要旋轉、推入或拔出異物", impalement)
        self.assertIn("不是可以等待6小時", amputation)

    def test_new_sources_and_counts_are_recorded_without_claiming_publication_ready(self):
        source_rows = read_json(SOURCE_INDEX)["sources"]
        coverage = read_json("localization/tw-edition/coverage.json")
        self.assertEqual({row[0] for row in source_rows}, set(self.batch["new_source_ids"]))
        for row in source_rows:
            self.assertEqual(row, [self.sources[row[0]]["id"], self.sources[row[0]]["title"],
                                   self.sources[row[0]]["url"], self.sources[row[0]]["supports"]])
        after = self.batch["counts_after"]
        self.assertEqual(after["core_reviewed"], coverage["core_reviewed_entries"])
        self.assertEqual(after["runtime_items"], len(self.runtime["items"]))
        self.assertEqual(after["runtime_sources"], len(self.runtime["sources"]))
        self.assertEqual(after["source_registry"], coverage["registry_sources"])
        self.assertEqual(after["json_files_checked"], coverage["json_files_checked"])
        self.assertEqual(after["substantive_rechecks"], len(self.register["substantive_rechecks"]))
        self.assertFalse(coverage["publication_ready"])


if __name__ == "__main__":
    unittest.main()

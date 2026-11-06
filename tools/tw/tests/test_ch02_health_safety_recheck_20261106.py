"""第2章酒精、一氧化碳與食品安全再審的內容、頻率及追溯契約。"""
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


BASE = "f888451b95165a4bd6369b020eaa35ac531e3bc7"
BATCH_PATH = "localization/ch02-health-safety-recheck-20261106.json"
SOURCE_PATH = "localization/tw-edition/sources/ch02-health-safety-recheck-20261106.json"
ITEM_IDS = ("TW-02-029", "TW-02-020", "TW-02-047", "TW-02-046")
NEW_SOURCE_IDS = {
    "tw02_taichung_vgh_alcohol_treatment_20261106",
    "tw02_mohw_alcohol_subsidy_115",
    "tw02_twhch_co_enclosed_balcony_2026",
    "tw02_tfda_food_safety_faq_20261106",
}


def read_json(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


class Chapter2HealthSafetyRecheckTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.runtime = validate_runtime()
        cls.items = {item["id"]: item for item in cls.runtime["items"]}
        cls.sources = {source["id"]: source for source in cls.runtime["sources"]}
        cls.manifest = {
            item["id"]: item for item in read_json("localization/manifest.json")["entries"]
        }
        cls.reviews = {
            item_id: read_json(f"localization/reviews/{item_id}.json")
            for item_id in ITEM_IDS
        }
        cls.register = read_json("localization/retroactive-review-register-20261019.json")
        cls.batch = read_json(BATCH_PATH)
        cls.batch_items = {item["id"]: item for item in cls.batch["items"]}
        cls.base_runtime = json.loads(
            subprocess.check_output(
                ["git", "show", f"{BASE}:localization/tw-edition/runtime.json"],
                cwd=ROOT,
                text=True,
            )
        )

    def test_batch_matches_runtime_manifest_review_and_append_only_history(self):
        self.assertEqual(self.batch["baseline_main_sha"], BASE)
        self.assertEqual(self.batch["reviewed_at"], "2026-11-06")
        self.assertEqual(self.batch["review_due_at"], "2027-02-06")
        self.assertEqual(set(self.batch_items), set(ITEM_IDS))
        self.assertEqual(set(self.batch["new_source_ids"]), NEW_SOURCE_IDS)
        self.assertTrue(self.batch["professional_review"]["required"])
        self.assertFalse(self.batch["professional_review"]["obtained"])

        for item_id in ITEM_IDS:
            with self.subTest(item_id=item_id):
                item = self.items[item_id]
                record = self.batch_items[item_id]
                review = self.reviews[item_id]
                body_path = ROOT / item["target_path"]
                body_bytes = body_path.read_bytes()
                body = body_bytes.decode("utf-8")
                body_sha = hashlib.sha256(body_bytes).hexdigest()
                history = [
                    row for row in self.register["substantive_rechecks"]
                    if row["id"] == item_id and row["reviewed_at"] == "2026-11-06"
                ]

                self.assertEqual(len(history), 1)
                self.assertEqual(history[0], record)
                self.assertEqual(record["status"], "ai_source_rechecked_professional_pending")
                self.assertEqual(record["prior_revision"], BASE)
                self.assertEqual(record["after_sha256"], body_sha)
                self.assertEqual(item["body"], body)
                self.assertEqual(review["target_sha256"], body_sha)
                self.assertEqual(review["source_reviewed_sha256"], body_sha)
                self.assertIsNone(review.get("reader_copy_cleanup"))
                self.assertEqual(review["source_checks"], record["source_checks"])
                self.assertEqual(review["reviewed_at"], "2026-11-06")
                self.assertEqual(review["review_due_at"], "2027-02-06")
                self.assertEqual(item["reviewed_at"], "2026-11-06")
                self.assertEqual(item["review_due_at"], "2027-02-06")
                self.assertEqual(self.manifest[item_id]["sources"], item["source_ids"])
                self.assertEqual(self.manifest[item_id]["verified_at"], "2026-11-06")
                self.assertEqual(self.manifest[item_id]["status"], "verified")
                self.assertEqual(record["source_ids"], item["source_ids"])

                body_urls = set(re.findall(r"\]\((https?://[^)]+)\)", body))
                source_urls = {self.sources[source_id]["url"] for source_id in item["source_ids"]}
                review_urls = {check["url"] for check in review["source_checks"]}
                self.assertEqual(body_urls, source_urls)
                self.assertEqual(review_urls, source_urls)
                self.assertNotRegex(
                    body,
                    r"(?:批次摘要|未宣稱閱讀|原始研究未讀|本次.{0,12}(?:AI|審查|再審|核對)|CI\s*(?:成功|通過)|PR\s*#\d+|非律師|非醫師)",
                )
                self.assertTrue(record["statistics_assessed"])
                for statistic in record["statistics_assessed"]:
                    for key in (
                        "period", "geographic_scope", "population", "numerator",
                        "denominator", "event_definition", "data_type", "limitations",
                    ):
                        self.assertTrue(statistic[key], (item_id, statistic["topic"], key))
                validate_recheck_history(ROOT, record, item)

    def test_source_history_is_preserved_and_replaced_sources_are_explicit(self):
        base_sources = {source["id"]: source for source in self.base_runtime["sources"]}
        source_rows = read_json(SOURCE_PATH)["sources"]
        self.assertEqual({row[0] for row in source_rows}, NEW_SOURCE_IDS)
        for row in source_rows:
            source = self.sources[row[0]]
            self.assertEqual(row, [source["id"], source["title"], source["url"], source["supports"]])

        for item_id, record in self.batch_items.items():
            previous_ids = record["previous_source_ids"]
            retired = {source["id"]: source for source in record["retired_sources"]}
            retained = [source_id for source_id in previous_ids if source_id not in retired]
            self.assertEqual(record["source_ids"][:len(retained)], retained)
            self.assertEqual(set(previous_ids) - set(record["source_ids"]), set(retired))
            for source_id, row in retired.items():
                self.assertEqual(self.sources[source_id], base_sources[source_id])
                self.assertEqual(
                    row["prior_source_sha256"],
                    hashlib.sha256(
                        json.dumps(base_sources[source_id], ensure_ascii=False, sort_keys=True)
                        .encode("utf-8")
                    ).hexdigest(),
                )

        food = self.batch_items["TW-02-047"]
        self.assertEqual(
            {row["id"] for row in food["retired_sources"]},
            {"tw02_tfda_food_safety_2026", "tw02_tfda_food_poisoning_reporting"},
        )

    def test_taiwan_scenarios_and_frequency_limits_are_explicit(self):
        alcohol = self.items["TW-02-020"]["body"]
        carbon_monoxide = self.items["TW-02-029"]["body"]
        mycotoxin = self.items["TW-02-046"]["body"]
        food = self.items["TW-02-047"]["body"]

        self.assertIn("計畫減量或停酒前先聯絡醫療院所", alcohol)
        self.assertIn("立即撥119", alcohol)
        self.assertIn("全國同口徑發生率資料", alcohol)
        self.assertIn("陽臺加裝窗戶或採光罩", carbon_monoxide)
        self.assertIn("22件一氧化碳中毒事故、5人死亡、59人送醫", carbon_monoxide)
        self.assertIn("不能換算成個人發生率", carbon_monoxide)
        self.assertIn("38件", mycotoxin)
        self.assertIn("不是全臺市場普查", mycotoxin)
        self.assertIn("不要試吃確認", mycotoxin)
        self.assertIn("兩人以上吃過相同餐點", food)
        self.assertIn("室溫超過32℃", food)
        self.assertIn("不要冷凍", food)
        self.assertNotIn("sid=3158", food)
        self.assertIn("海水魚生魚片不是這種寄生蟲的感染途徑", food)
        self.assertIn("沒有提供足以估算目前全臺病例頻率的資料", food)

    def test_coverage_matches_counts_and_publication_stays_blocked(self):
        coverage = read_json("localization/tw-edition/coverage.json")
        after = self.batch["counts_after"]
        self.assertGreaterEqual(coverage["core_reviewed_entries"], after["core_reviewed"])
        self.assertGreaterEqual(len(self.runtime["items"]), after["runtime_items"])
        self.assertGreaterEqual(len(self.runtime["sources"]), after["runtime_sources"])
        self.assertGreaterEqual(coverage["registry_sources"], after["source_registry"])
        self.assertGreaterEqual(coverage["json_files_checked"], after["json_files_checked"])
        self.assertGreaterEqual(
            len(self.register["substantive_rechecks"]), after["substantive_rechecks"]
        )
        self.assertFalse(coverage["publication_ready"])


if __name__ == "__main__":
    unittest.main()

"""第13章雷擊及施救者權益再審的內容、頻率與追溯契約。"""
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


BASE = "fa333ad63581967bd12e234ff5b671dd297c60a8"
BATCH_PATH = "localization/ch13-lightning-rescue-recheck-20261106.json"
SOURCE_PATH = "localization/tw-edition/sources/ch13-lightning-rescue-recheck-20261106.json"
ITEM_IDS = ("TW-13-032", "TW-13-039")
NEW_SOURCE_IDS = {
    "lightning_cwa_qpeplus_20261106",
    "lightning_cwa_observation_spec_20261106",
    "lightning_cwa_thunder_alert_20261106",
    "lightning_mohw_death_stats_114",
    "aid_firefighter_injury_report_111",
    "aid_civil_law_150_recheck_20261106",
}


def read_json(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


class Chapter13LightningRescueRecheckTests(unittest.TestCase):
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
        cls.base_reviews = {
            item_id: json.loads(
                subprocess.check_output(
                    ["git", "show", f"{BASE}:localization/reviews/{item_id}.json"],
                    cwd=ROOT,
                    text=True,
                )
            )
            for item_id in ITEM_IDS
        }

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
                self.assertIsNone(review["reader_copy_cleanup"])
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
                self.assertEqual(record["source_ids"], item["source_ids"])

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

    def test_retired_sources_remain_unchanged_and_new_source_index_matches_runtime(self):
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
                        json.dumps(
                            base_sources[source_id], ensure_ascii=False, sort_keys=True
                        ).encode("utf-8")
                    ).hexdigest(),
                )

    def test_taiwan_frequency_and_safety_distinctions_are_explicit(self):
        lightning = self.items["TW-13-032"]["body"]
        rescue = self.items["TW-13-039"]["body"]
        self.assertIn("一聽見雷聲或看到閃電", lightning)
        self.assertIn("QPEplus", lightning)
        self.assertIn("不能把年報未列出可辨認的雷擊死因項目解讀成零死亡", lightning)
        self.assertIn("沒有可與戶外活動人次配對的雷擊傷亡發生率", lightning)
        self.assertNotIn("臺灣國家公園", lightning)
        self.assertIn("蹲低只能作為無處可躲時的最後手段", lightning)
        self.assertIn("最後一次雷聲或閃電後30分鐘", lightning)
        self.assertIn("2013年1月18日生效", rescue)
        self.assertIn("2023年7月1日施行", rescue)
        self.assertIn("205件事件", rescue)
        self.assertIn("94件是沒有造成受傷的近失事件", rescue)
        self.assertIn("不能拿來估算民眾臨時救人的受傷率", rescue)
        self.assertIn("0800-005-850", rescue)
        self.assertNotIn("2026-08-17", rescue)

    def test_coverage_and_tracker_match_the_actual_batch_without_publication_claim(self):
        coverage = read_json("localization/tw-edition/coverage.json")
        for item_id in ITEM_IDS:
            tracked = next(row for row in self.register["tracked_formal_items"] if row["id"] == item_id)
            self.assertEqual(
                tracked["new_standard_substantive_review"],
                "ai_source_rechecked_professional_pending",
            )
        after = self.batch["counts_after"]
        self.assertGreaterEqual(coverage["core_reviewed_entries"], after["core_reviewed"])
        self.assertGreaterEqual(len(self.runtime["items"]), after["runtime_items"])
        self.assertGreaterEqual(len(self.runtime["sources"]), after["runtime_sources"])
        self.assertGreaterEqual(coverage["registry_sources"], after["source_registry"])
        self.assertGreaterEqual(coverage["json_files_checked"], after["json_files_checked"])
        self.assertGreaterEqual(len(self.register["substantive_rechecks"]), after["substantive_rechecks"])
        self.assertFalse(coverage["publication_ready"])


if __name__ == "__main__":
    unittest.main()

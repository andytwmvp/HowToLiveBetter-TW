"""臺灣山域、失溫、蛇咬與嬰兒急救五篇歷史再審契約。"""

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
from recheck_history_assertions import assert_historical_recheck_edge
from review_contract import publication_report, validate_runtime


BASELINE = "79c0c7c51004763cb9f08ad867681cb8604b4499"
HISTORICAL_HEAD = "171783959adfc988ad6cd2cff04cfcdf21a745f6"
MOUNTAIN_FREQUENCY_HEAD = "c46443b55942139d0067e2011d2f004fad1e44eb"
ITEM_IDS = ("TW-13-027", "TW-13-028", "TW-13-029", "TW-13-043", "TW-13-044")


def read(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def read_at(revision, path):
    raw = subprocess.check_output(["git", "show", f"{revision}:{path}"], cwd=ROOT)
    return json.loads(raw)


def sha256(data):
    return hashlib.sha256(data).hexdigest()


class Ch13MountainColdSnakeInfantRecheckTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.runtime = validate_runtime()
        cls.current_register = read("localization/retroactive-review-register-20261019.json")

        # This batch test is a contract for its immutable 10/31 snapshot. Later
        # reviews are checked by the audit chain and must not replace this row.
        snapshot_runtime = read_at(HISTORICAL_HEAD, "localization/tw-edition/runtime.json")
        snapshot_manifest = read_at(HISTORICAL_HEAD, "localization/manifest.json")
        snapshot_reviews = {
            key: read_at(HISTORICAL_HEAD, f"localization/reviews/{key}.json")
            for key in ITEM_IDS
        }
        snapshot_register = read_at(
            HISTORICAL_HEAD, "localization/retroactive-review-register-20261019.json"
        )
        cls.historical_items = {item["id"]: item for item in snapshot_runtime["items"]}
        cls.historical_sources = {source["id"]: source for source in snapshot_runtime["sources"]}
        cls.historical_manifest = {item["id"]: item for item in snapshot_manifest["entries"]}
        cls.historical_reviews = snapshot_reviews
        cls.historical_records = {
            item_id: next(
                row for row in snapshot_register["substantive_rechecks"]
                if row["id"] == item_id and row["reviewed_at"] == "2026-10-31"
            )
            for item_id in ITEM_IDS
        }
        frequency_runtime = read_at(
            MOUNTAIN_FREQUENCY_HEAD, "localization/tw-edition/runtime.json"
        )
        frequency_register = read_at(
            MOUNTAIN_FREQUENCY_HEAD, "localization/retroactive-review-register-20261019.json"
        )
        cls.frequency_items = {
            item["id"]: item for item in snapshot_runtime["items"]
            if item["id"] in ITEM_IDS and item["id"] != "TW-13-027"
        }
        cls.frequency_items["TW-13-027"] = next(
            item for item in frequency_runtime["items"] if item["id"] == "TW-13-027"
        )
        cls.frequency_records = {
            "TW-13-027": next(
                row for row in frequency_register["substantive_rechecks"]
                if row["id"] == "TW-13-027" and row["reviewed_at"] == "2026-11-14"
            ),
            "TW-13-029": cls.historical_records["TW-13-029"],
        }

    def test_progress_and_source_inventories_reconcile_to_branch_baseline(self):
        previous_runtime = read_at(BASELINE, "localization/tw-edition/runtime.json")
        previous_coverage = read_at(BASELINE, "localization/tw-edition/coverage.json")
        previous_register = read_at(BASELINE, "localization/retroactive-review-register-20261019.json")
        coverage = read("localization/tw-edition/coverage.json")
        register = read("localization/retroactive-review-register-20261019.json")
        self.assertEqual(coverage, audit_drafts())
        self.assertGreaterEqual(coverage["publication_completed_entries"], previous_coverage["publication_completed_entries"])
        previous_item_ids = {row["id"] for row in previous_runtime["items"]}
        current_item_ids = {row["id"] for row in self.runtime["items"]}
        self.assertTrue(previous_item_ids <= current_item_ids)
        self.assertGreaterEqual(len(self.runtime["items"]), len(previous_runtime["items"]))
        current_source_ids = {row["id"] for row in self.runtime["sources"]}
        previous_source_ids = {row["id"] for row in previous_runtime["sources"]}
        self.assertTrue(previous_source_ids <= current_source_ids)
        self.assertTrue({
            "ch13_mountain_nfa_20260528",
            "ch13_mountain_cause_nfa_20250626",
            "ch13_cold_cdc",
            "ch13_snake_cdc_epidemiology_2025",
            "ch13_infant_peds_bls_aha_2025",
            "ch13_infant_cpr_lay_aha_2025",
        } <= current_source_ids - previous_source_ids)
        previous_review_hashes = {row["after_sha256"] for row in previous_register["substantive_rechecks"]}
        current_review_hashes = {row["after_sha256"] for row in register["substantive_rechecks"]}
        self.assertTrue(previous_review_hashes <= current_review_hashes)
        self.assertEqual(publication_report()["publication_completed_entries"], coverage["publication_completed_entries"])
        self.assertFalse(publication_report()["publication_ready"])

    def test_five_rechecks_preserve_history_and_sync_reader_contracts(self):
        for item_id in ITEM_IDS:
            with self.subTest(item=item_id):
                record = self.historical_records[item_id]
                item = self.historical_items[item_id]
                review = self.historical_reviews[item_id]
                manifest = self.historical_manifest[item_id]
                raw = subprocess.check_output(
                    ["git", "show", f"{HISTORICAL_HEAD}:{manifest['target_path']}"], cwd=ROOT
                )
                body = item["body"]
                digest = sha256(body.encode("utf-8"))

                self.assertEqual(raw.decode("utf-8"), body)
                self.assertIn(record, self.current_register["substantive_rechecks"])
                assert_historical_recheck_edge(
                    self, ROOT, record, merged_revision=HISTORICAL_HEAD
                )
                self.assertEqual(record["prior_revision"], BASELINE)
                self.assertEqual(record["after_sha256"], digest)
                self.assertEqual(record["before_sha256"], sha256(record["previous_body"].encode("utf-8")))
                self.assertEqual(item["body"], body)
                self.assertEqual(item["source_ids"], manifest["sources"])
                self.assertEqual(item["source_ids"], record["source_ids"])
                self.assertEqual(sum(line.startswith("## ") for line in body.splitlines()), 5)
                self.assertEqual(review["target_sha256"], digest)
                self.assertEqual(review["source_reviewed_sha256"], digest)
                self.assertEqual(manifest["verified_at"], review["reviewed_at"])
                self.assertEqual(item["reviewed_at"], review["reviewed_at"])
                expected_urls = {
                    self.historical_sources[source_id]["url"]
                    for source_id in item["source_ids"]
                }
                self.assertEqual({check["url"] for check in review["source_checks"]}, expected_urls)
                self.assertEqual(set(re.findall(r"\]\((https://[^)]+)\)", body)), expected_urls)
                self.assertNotRegex(body, r"本批|本次再審|來源實質再核對|\bPR\s*#|CI\s*(?:通過|成功)|AI輔助")
                self.assertNotRegex(item["limits"], r"本次|本批|\bPR\s*#|AI輔助")

    def test_frequency_claims_keep_population_and_denominator_limits(self):
        mountain = self.frequency_records["TW-13-027"]["statistics_assessed"]
        accidents = next(row for row in mountain if row["topic"].startswith("臺灣山域事故件數"))
        self.assertEqual(accidents["value"], {
            "2015_incident_cases": 179,
            "2025_incident_cases": 502,
            "2025_involved_people": 695,
        })
        self.assertEqual(accidents["unit"], "行政山域事故件數及涉入人數")
        self.assertIsNone(accidents["denominator"])
        self.assertIn("登山人次", accidents["denominator_definition"])

        snake = self.frequency_records["TW-13-029"]["statistics_assessed"]
        fatality = next(row for row in snake if "0.18%" in row["value"])
        self.assertEqual(fatality["numerator"], "9名死亡者")
        self.assertEqual(fatality["denominator"], "4,893名抗蛇毒血清使用者")
        self.assertIn("全部蛇咬死亡率", fatality["limitations"])

        for item_id in ("TW-13-028", "TW-13-043", "TW-13-044"):
            self.assertEqual(self.historical_records[item_id]["statistics_assessed"], [])
            self.assertRegex(self.frequency_items[item_id]["body"], r"沒有找到|沒有.*資料|未查得")

    def test_emergency_actions_precede_background_statistics(self):
        bodies = {key: self.frequency_items[key]["body"] for key in ITEM_IDS}
        for key, marker in {
            "TW-13-027": "502件",
            "TW-13-029": "4,893名",
            "TW-13-043": "沒有全國未滿一歲嬰兒哽塞事件數",
            "TW-13-044": "目前沒有與嬰兒相同母群及結果定義的全國院外心跳停止資料",
        }.items():
            with self.subTest(item=key):
                self.assertLess(bodies[key].index("119"), bodies[key].index(marker))
        self.assertIn("自己立即撥119", bodies["TW-13-027"])
        self.assertLess(bodies["TW-13-028"].index("立即打119"), bodies["TW-13-028"].index("沒有找到同一病例定義"))
        self.assertIn("不做腹部推擠", bodies["TW-13-043"])
        self.assertIn("不盲目用手指挖", bodies["TW-13-043"])
        self.assertIn("臺北市消防局", bodies["TW-13-043"])
        self.assertIn("本文建議立即打119開擴音", bodies["TW-13-044"])
        self.assertNotIn("仍待臺灣急救專業審閱", bodies["TW-13-043"])
        review = read("localization/reviews/TW-13-043.json")
        self.assertTrue(any("獨立醫療、急救及相關專業審閱仍待取得" in row for row in review["limits"]))


if __name__ == "__main__":
    unittest.main()

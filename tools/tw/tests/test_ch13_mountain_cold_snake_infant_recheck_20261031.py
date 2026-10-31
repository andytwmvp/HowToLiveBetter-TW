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
from retroactive_audit import validate_recheck_history
from review_contract import publication_report, validate_runtime


BASELINE = "79c0c7c51004763cb9f08ad867681cb8604b4499"
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
        cls.items = {item["id"]: item for item in cls.runtime["items"]}
        cls.sources = {source["id"]: source for source in cls.runtime["sources"]}
        cls.manifest = {item["id"]: item for item in read("localization/manifest.json")["entries"]}
        cls.reviews = {key: read(f"localization/reviews/{key}.json") for key in ITEM_IDS}
        register = read("localization/retroactive-review-register-20261019.json")
        cls.records = {}
        for row in sorted(register["substantive_rechecks"],
                           key=lambda entry: (entry.get("reviewed_at", ""), entry.get("after_sha256", ""))):
            cls.records[row["id"]] = row

    def test_progress_and_source_inventories_reconcile_to_branch_baseline(self):
        previous_runtime = read_at(BASELINE, "localization/tw-edition/runtime.json")
        previous_coverage = read_at(BASELINE, "localization/tw-edition/coverage.json")
        previous_register = read_at(BASELINE, "localization/retroactive-review-register-20261019.json")
        coverage = read("localization/tw-edition/coverage.json")
        register = read("localization/retroactive-review-register-20261019.json")
        self.assertEqual(coverage, audit_drafts())
        self.assertEqual(coverage["publication_completed_entries"], previous_coverage["publication_completed_entries"])
        self.assertEqual(len(self.runtime["items"]), len(previous_runtime["items"]))
        self.assertEqual(len(self.runtime["sources"]), len(previous_runtime["sources"]) + 6)
        self.assertEqual(len(register["substantive_rechecks"]),
                         len(previous_register["substantive_rechecks"]) + len(ITEM_IDS))
        self.assertEqual(publication_report()["publication_completed_entries"], coverage["publication_completed_entries"])
        self.assertFalse(publication_report()["publication_ready"])

    def test_five_rechecks_preserve_history_and_sync_reader_contracts(self):
        for item_id in ITEM_IDS:
            with self.subTest(item=item_id):
                item = self.items[item_id]
                record = self.records[item_id]
                review = self.reviews[item_id]
                manifest = self.manifest[item_id]
                raw = (ROOT / manifest["target_path"]).read_bytes()
                body = raw.decode("utf-8")
                digest = sha256(raw)

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
                expected_urls = {self.sources[source_id]["url"] for source_id in item["source_ids"]}
                self.assertEqual({check["url"] for check in review["source_checks"]}, expected_urls)
                self.assertEqual(set(re.findall(r"\]\((https://[^)]+)\)", body)), expected_urls)
                self.assertNotRegex(body, r"本批|本次再審|來源實質再核對|\bPR\s*#|CI\s*(?:通過|成功)|AI輔助")
                self.assertNotRegex(item["limits"], r"本次|本批|\bPR\s*#|AI輔助")
                validate_recheck_history(ROOT, record, item)

    def test_frequency_claims_keep_population_and_denominator_limits(self):
        mountain = self.records["TW-13-027"]["statistics_assessed"]
        accidents = next(row for row in mountain if "179件" in row["value"])
        self.assertEqual(accidents["unit"], "山域事故件數（件）")
        self.assertIsNone(accidents["denominator"])
        self.assertIn("登山活動人次", accidents["denominator_definition"])

        snake = self.records["TW-13-029"]["statistics_assessed"]
        fatality = next(row for row in snake if "0.18%" in row["value"])
        self.assertEqual(fatality["numerator"], "9名死亡者")
        self.assertEqual(fatality["denominator"], "4,893名抗蛇毒血清使用者")
        self.assertIn("全部蛇咬死亡率", fatality["limitations"])

        for item_id in ("TW-13-028", "TW-13-043", "TW-13-044"):
            self.assertEqual(self.records[item_id]["statistics_assessed"], [])
            self.assertRegex(self.items[item_id]["body"], r"沒有找到|沒有.*資料|未查得")

    def test_emergency_actions_precede_background_statistics(self):
        bodies = {key: self.items[key]["body"] for key in ITEM_IDS}
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

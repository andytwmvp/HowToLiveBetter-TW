"""臺灣癌症篩檢導航條目的歷史再審與數據界線。"""
import hashlib
import json
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from retroactive_audit import validate_recheck_history
from review_contract import ROOT, publication_report, validate_runtime

BASE = "54b9b8a5dad61fdd5ea32accbeb56b6a885b4454"
IDS = {f"TW-NAV-{number:03d}" for number in range(4, 10)}


def load(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


class CancerScreeningNavigationRecheckTests(unittest.TestCase):
    def test_six_rechecks_match_runtime_hashes_and_prior_snapshot(self):
        runtime = validate_runtime()
        items = {item["id"]: item for item in runtime["items"]}
        sources = {source["id"]: source for source in runtime["sources"]}
        rows = {
            row["id"]: row
            for row in load("localization/retroactive-review-register-20261019.json")["substantive_rechecks"]
        }
        prior = json.loads(subprocess.check_output(
            ["git", "show", f"{BASE}:localization/tw-edition/runtime.json"],
            cwd=ROOT, text=True))
        prior_items = {item["id"]: item for item in prior["items"]}

        self.assertEqual(IDS, IDS & set(items))
        self.assertEqual(IDS, IDS & set(rows))
        for key in IDS:
            item = items[key]
            review = load(f"localization/reviews/{key}.json")
            row = rows[key]
            validate_recheck_history(ROOT, row, item)
            self.assertNotEqual(item["body"], prior_items[key]["body"])
            self.assertEqual(row["before_sha256"], hashlib.sha256(
                prior_items[key]["body"].encode("utf-8")).hexdigest())
            self.assertEqual(review["target_sha256"], hashlib.sha256(
                item["body"].encode("utf-8")).hexdigest())
            self.assertEqual({check["url"] for check in review["source_checks"]},
                             {sources[source_id]["url"] for source_id in item["source_ids"]})
            self.assertEqual(row["status"], "ai_source_rechecked_professional_pending")

        self.assertIn("taipei_screening", sources)
        old_sources = {source["id"]: source for source in prior["sources"]}
        for source_id, source in old_sources.items():
            self.assertEqual(sources[source_id], source)

    def test_screening_intervals_symptom_followup_and_future_rule_are_distinguished(self):
        items = {item["id"]: item for item in validate_runtime()["items"]}
        cervical_30 = items["TW-NAV-006"]["body"]
        self.assertIn("每年可補助一次", cervical_30)
        self.assertIn("至少每3年接受一次", cervical_30)
        self.assertIn("不等於每年都需要檢查", cervical_30)
        self.assertIn("有症狀或過往異常者", items["TW-NAV-006"]["limits"])

        future = next(source for source in validate_runtime()["sources"]
                      if source["id"] == "hpa_preventive_service_rules_20261008")
        self.assertEqual(future["published_at"], "2026-10-08")
        self.assertEqual(future["effective_at"], "2027-01-01")
        evidence = load("localization/ch01-cancer-screening-navigation-recheck-20261026.json")
        self.assertIn("尚未生效", evidence["policy_dates"][0]["status_at_review"])
        self.assertIn("2027-01-01", items["TW-NAV-007"]["limits"])
        self.assertEqual(items["TW-NAV-007"]["review_due_at"], "2026-12-15")

        colorectal = items["TW-NAV-008"]
        for phrase in ("陰性仍按2年週期", "陽性應儘速接受大腸鏡", "即使最近篩檢陰性也要就醫"):
            self.assertIn(phrase, colorectal["limits"])
        family = items["TW-NAV-009"]
        for relative in ("父母", "兄弟姊妹", "子女"):
            self.assertIn(relative, family["body"])
        self.assertIn("優先由醫師評估全大腸鏡", family["limits"])

    def test_registry_counts_are_not_personal_risk_and_publication_stays_blocked(self):
        evidence = load("localization/ch01-cancer-screening-navigation-recheck-20261026.json")
        self.assertEqual(evidence["statistics"]["period"], "2023年（民國112年）新發侵襲癌登記")
        self.assertIn("不含原位癌", evidence["statistics"]["data_type"])
        self.assertIn("2000年世界標準人口", evidence["statistics"]["standardization"])
        measures = {row["site"]: row for row in evidence["statistics"]["measures"]}
        self.assertEqual(measures["乳房（女性）"]["numerator"], 17779)
        self.assertEqual(measures["乳房（女性）"]["value"], 91.2)
        self.assertEqual(measures["大腸癌（男女合計）"]["numerator"], 19074)
        self.assertEqual(measures["大腸癌（男女合計）"]["value"], 43.1)
        self.assertEqual(measures["子宮頸（女性）"]["numerator"], 1429)
        self.assertEqual(measures["子宮頸（女性）"]["value"], 7.4)
        self.assertEqual(evidence["professional_review"], "pending")
        self.assertFalse(evidence["publication_ready"])
        self.assertFalse(publication_report()["publication_ready"])


if __name__ == "__main__":
    unittest.main()

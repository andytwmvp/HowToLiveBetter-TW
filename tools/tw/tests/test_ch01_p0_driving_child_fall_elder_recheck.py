"""第1章交通、兒童乘車、窗戶防墜與長者跌倒四篇實質再審。"""
import hashlib
import json
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from retroactive_audit import validate_recheck_history
from review_contract import ROOT, publication_report, validate_entry, validate_runtime

BASE = "4275074f15296ee625521834a6cad49d08bef796"
IDS = ("TW-01-009", "TW-01-010", "TW-01-011", "TW-01-013")
NEW_SOURCE_IDS = {
    "ch01_moj_road_act_handheld_2026", "ch01_motc_distraction_a1_2026janapr",
    "ch01_moj_child_restraint_2026", "ch01_gazette_childseat_2020",
    "ch01_moj_child_seatbelt_rule_2026", "ch01_gazette_seatbelt_2022",
    "ch01_nlma_condo_fall_protection", "ch01_kl_health_child_fall_prevention",
    "ch01_mnd_casualty_care_2026", "ch01_mohw_fall_prevention_2026",
    "ch01_mohw_fall_firstaid_2022",
}
RETIRED_SOURCE_IDS = {
    "TW-01-009": {"ch01_moj_road_act_2026"},
    "TW-01-010": {"ch01_motc_childseat_2020", "ch01_hpa_childbook_202606", "ch01_motc_2025_30day"},
    "TW-01-011": {"ch01_mohw_childaccident_2016", "ch01_tpe_child_fall_precaution"},
    "TW-01-013": {"ch01_mohw_fall_environment"},
}
EVIDENCE = "localization/ch01-p0-driving-child-fall-elder-recheck-20261026.json"


def load(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


class Chapter01DrivingChildFallRecheckTests(unittest.TestCase):
    def test_bodies_reviews_sources_and_history_are_synchronized(self):
        manifest = {entry["id"]: entry for entry in load("localization/manifest.json")["entries"]}
        runtime = validate_runtime()
        items = {item["id"]: item for item in runtime["items"]}
        sources = {source["id"]: source for source in runtime["sources"]}
        register = load("localization/retroactive-review-register-20261019.json")
        rows = {row["id"]: row for row in register["substantive_rechecks"]}
        evidence = load(EVIDENCE)
        evidence_articles = {row["id"]: row for row in evidence["articles"]}

        for key in IDS:
            with self.subTest(key=key):
                entry, item, row = manifest[key], items[key], rows[key]
                review = load("localization/reviews/" + key + ".json")
                raw = (ROOT / entry["target_path"]).read_bytes()
                self.assertTrue(validate_entry(entry))
                self.assertEqual(entry["sources"], item["source_ids"])
                self.assertEqual(raw.decode("utf-8"), item["body"])
                self.assertEqual(hashlib.sha256(raw).hexdigest(), review["target_sha256"])
                self.assertEqual(review["reviewed_at"], "2026-10-26")
                self.assertEqual(review["review_due_at"], "2027-01-31")
                self.assertEqual(row["status"], "ai_source_rechecked_professional_pending")
                self.assertEqual(row["prior_revision"], BASE)
                self.assertEqual(row["source_ids"], item["source_ids"])
                self.assertEqual(row["source_checks"], review["source_checks"])
                self.assertEqual({check["url"] for check in review["source_checks"]},
                                 {sources[source_id]["url"] for source_id in item["source_ids"]})
                self.assertEqual({source["id"] for source in row["retired_sources"]},
                                 RETIRED_SOURCE_IDS[key])
                self.assertEqual(set(evidence_articles[key]["source_ids"]), set(item["source_ids"]))
                self.assertEqual(set(evidence_articles[key]["retired_source_ids"]), RETIRED_SOURCE_IDS[key])
                validate_recheck_history(ROOT, row, item)

        self.assertTrue(NEW_SOURCE_IDS.issubset(sources))

    def test_frequency_evidence_keeps_denominators_and_periods_distinct(self):
        evidence = load(EVIDENCE)
        stats = evidence["statistics"]
        dui, highway = stats["TW-01-009"]
        self.assertEqual(dui["period"], "2025全年")
        self.assertEqual(dui["numerator"]["30日死亡人數"], 143)
        self.assertEqual(dui["numerator"]["受傷人數"], 8751)
        self.assertIsNone(dui["denominator"])
        self.assertEqual(highway["numerator"], {"死亡事故件數": 27, "死亡人數": 30, "其中歸因分心駕駛死亡人數": 14})
        self.assertEqual(highway["period"], "2026-01至2026-04")
        self.assertIsNone(highway["denominator"])

        for key in ("TW-01-010", "TW-01-011"):
            self.assertTrue(all(stat.get("denominator") is None for stat in stats[key]))
        survey, death_rate = stats["TW-01-013"]
        self.assertEqual(survey["period"], "2021年國民健康訪問調查（衛福部2026摘要再述）")
        self.assertIn("抽樣調查", survey["denominator"])
        self.assertEqual(death_rate["unit"], "跌倒死亡率26.4人／十萬名65歲以上人口")
        self.assertIn("26.4人", death_rate["unit"])
        self.assertIn("未列可重算分子", death_rate["numerator"])
        self.assertIn("不是跌倒受傷者致死率", death_rate["limitations"])

    def test_safety_actions_precede_statistics_and_removed_claims_stay_removed(self):
        items = {item["id"]: item["body"] for item in validate_runtime()["items"]}
        markers = {
            "TW-01-009": "## 臺灣事件數與統計界線",
            "TW-01-010": "## 臺灣資料與法規範圍",
            "TW-01-011": "## 臺灣統計能說到哪裡",
            "TW-01-013": "## 臺灣頻率與統計口徑",
        }
        for key in IDS:
            self.assertIn("119", items[key])
            self.assertLess(items[key].index("## 適用情境"), items[key].index(markers[key]))
        self.assertIn("沒有車流量、行駛里程或旅次暴露分母", items["TW-01-009"])
        self.assertIn("約占整體事故五成", items["TW-01-009"])
        self.assertIn("口徑不清，本文不採用該比例", items["TW-01-009"])
        self.assertIn("兒童乘車旅次", items["TW-01-010"])
        self.assertNotIn("2,858", items["TW-01-010"])
        self.assertIn("附件未能直接取得並逐項核讀", items["TW-01-011"])
        self.assertIn("不再以2016年多種事故傷害死亡合計239人代表窗墜發生率", items["TW-01-011"])
        self.assertIn("不是跌倒後的致死率", items["TW-01-013"])

    def test_counts_and_publication_state_are_dynamic(self):
        evidence = load(EVIDENCE)
        before, after = evidence["counts_before"], evidence["counts_after"]
        self.assertEqual(evidence["base_main_sha"], BASE)
        self.assertEqual(evidence["scope"]["new_core_ids"], [])
        self.assertEqual(set(evidence["scope"]["substantive_recheck_ids"]), set(IDS))
        self.assertEqual(after["core_completed"], before["core_completed"])
        self.assertEqual(after["substantive_rechecks"], before["substantive_rechecks"] + len(IDS))
        self.assertEqual(after["runtime_sources"], before["runtime_sources"] + len(NEW_SOURCE_IDS))
        self.assertEqual(after["source_registry"], before["source_registry"] + len(NEW_SOURCE_IDS))
        self.assertEqual(after["source_registry"], load("localization/tw-edition/coverage.json")["registry_sources"])
        self.assertEqual(len(validate_runtime()["sources"]), after["runtime_sources"])
        self.assertFalse(after["publication_ready"])
        self.assertFalse(publication_report()["publication_ready"])

        old = json.loads(subprocess.check_output(
            ["git", "show", BASE + ":localization/tw-edition/runtime.json"], cwd=ROOT, text=True))
        runtime = validate_runtime()
        current_sources = {source["id"]: source for source in runtime["sources"]}
        for source in old["sources"]:
            self.assertEqual(current_sources[source["id"]], source)


if __name__ == "__main__":
    unittest.main()

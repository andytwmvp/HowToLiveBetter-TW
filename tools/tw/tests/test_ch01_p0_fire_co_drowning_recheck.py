"""第1章P0居家火災、CO、電動二輪車與兒童防溺歷史實質再審。"""
import hashlib
import json
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from retroactive_audit import validate_recheck_history
from review_contract import ROOT, publication_report, validate_entry, validate_runtime

BASE = "66b24c548bb3b3731579bd2421e37124d437d303"
IDS = ("TW-01-003", "TW-01-004", "TW-01-006", "TW-01-012")
NEW_SOURCE_IDS = {
    "ch01_nfa_co_detector_3714", "ch01_wda_co_first_aid_2026",
    "ch01_vghtpe_inhalation_firstaid", "ch01_nfa_co_2024",
    "ch01_klfd_co_2025", "ch01_moea_gas_emergency_2025",
    "ch01_ftc_gas_check_2023", "ch01_nfa_micro_ev_fire_safety",
    "ch01_mohw_drowning_age_2025", "ch01_nfa_water_rescue_2022",
    "ch01_moe_rescue_five_2019", "ch01_cga_118_hotline",
}


def load(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


class Chapter01P0FireCoDrowningRecheckTests(unittest.TestCase):
    def test_bodies_manifest_reviews_and_historical_edges(self):
        manifest = {entry["id"]: entry for entry in load("localization/manifest.json")["entries"]}
        runtime = validate_runtime()
        items = {item["id"]: item for item in runtime["items"]}
        sources = {source["id"]: source for source in runtime["sources"]}
        register = load("localization/retroactive-review-register-20261019.json")
        rows = {row["id"]: row for row in register["substantive_rechecks"]}
        for key in IDS:
            with self.subTest(key=key):
                entry = manifest[key]
                item = items[key]
                review = load("localization/reviews/" + key + ".json")
                row = rows[key]
                raw = (ROOT / entry["target_path"]).read_bytes()
                self.assertTrue(validate_entry(entry))
                self.assertEqual(entry["sources"], item["source_ids"])
                self.assertEqual(raw.decode("utf-8"), item["body"])
                self.assertEqual(hashlib.sha256(raw).hexdigest(), review["target_sha256"])
                self.assertEqual(review["reviewed_at"], "2026-10-25")
                self.assertEqual(review["review_due_at"], "2027-01-31")
                self.assertEqual(row["status"], "ai_source_rechecked_professional_pending")
                self.assertEqual(row["prior_revision"], BASE)
                self.assertEqual(row["source_ids"], item["source_ids"])
                self.assertEqual(row["source_checks"], review["source_checks"])
                self.assertEqual({check["url"] for check in review["source_checks"]},
                                 {sources[sid]["url"] for sid in item["source_ids"]})
                validate_recheck_history(ROOT, row, item)

    def test_life_safety_actions_precede_frequency_context(self):
        bodies = {item["id"]: item["body"] for item in validate_runtime()["items"]}
        stats_marker = {
            "TW-01-003": "臺灣發生頻率與統計定義",
            "TW-01-004": "臺灣事件頻率與統計口徑",
            "TW-01-006": "臺灣事件頻率與統計口徑",
            "TW-01-012": "臺灣事故頻率與統計界線",
        }
        for key in IDS:
            body = bodies[key]
            self.assertLess(body.index("## 臺灣實作與下一步"), body.index(stats_marker[key]))
            self.assertIn("119", body)
        self.assertIn("4,514次", bodies["TW-01-003"])
        self.assertIn("3,171次", bodies["TW-01-003"])
        self.assertIn("不是全臺房屋戶數", bodies["TW-01-003"])
        self.assertIn("住警器不會偵測一氧化碳", bodies["TW-01-003"])
        self.assertIn("24件", bodies["TW-01-004"])
        self.assertIn("22件", bodies["TW-01-004"])
        self.assertNotIn("118件", bodies["TW-01-004"])
        self.assertIn("家庭暴露分母", bodies["TW-01-004"])
        self.assertIn("71件", bodies["TW-01-006"])
        self.assertIn("29.3%", bodies["TW-01-006"])
        self.assertIn("絕非電動車起火率", bodies["TW-01-006"])
        self.assertIn("2023年）8人", bodies["TW-01-012"])
        self.assertIn("2024年）1人", bodies["TW-01-012"])
        self.assertIn("2025年）3人", bodies["TW-01-012"])
        self.assertIn("海巡署118", bodies["TW-01-012"])
        self.assertIn("優先從岸上以工具救援", bodies["TW-01-012"])

    def test_sources_retirements_and_progress_snapshot(self):
        runtime = validate_runtime()
        sources = {source["id"]: source for source in runtime["sources"]}
        self.assertTrue(NEW_SOURCE_IDS.issubset(sources))
        self.assertEqual(len(runtime["sources"]), 677)
        register = load("localization/retroactive-review-register-20261019.json")
        self.assertEqual(len(register["substantive_rechecks"]), 124)
        rows = {row["id"]: row for row in register["substantive_rechecks"]}
        self.assertEqual(len(rows["TW-01-004"]["retired_sources"]), 2)
        self.assertEqual(len(rows["TW-01-012"]["retired_sources"]), 1)
        previous = json.loads(subprocess.check_output(
            ["git", "show", BASE + ":localization/tw-edition/runtime.json"], cwd=ROOT, text=True))
        previous_sources = {source["id"]: source for source in previous["sources"]}
        for source_id, old_source in previous_sources.items():
            self.assertEqual(sources[source_id], old_source)
        for key in ("TW-01-004", "TW-01-012"):
            for retired in rows[key]["retired_sources"]:
                old_source = previous_sources[retired["id"]]
                digest = hashlib.sha256(json.dumps(old_source, ensure_ascii=False,
                                                   sort_keys=True).encode("utf-8")).hexdigest()
                self.assertEqual(retired["prior_source_sha256"], digest)
        evidence = load("localization/ch01-p0-fire-co-evehicle-drowning-recheck-20261025.json")
        self.assertEqual(evidence["base_main_sha"], BASE)
        self.assertEqual(evidence["new_core_ids"], [])
        self.assertEqual(evidence["counts_before"]["core_reviewed_entries"], 278)
        self.assertEqual(evidence["counts_after"]["core_reviewed_entries"], 278)
        self.assertEqual(evidence["counts_before"]["substantive_rechecks"], 120)
        self.assertEqual(evidence["counts_after"]["substantive_rechecks"], 124)
        self.assertEqual(evidence["statistics"]["TW-01-012"][0]["numerator"]["2025_deaths"], 3)
        coverage = load("localization/tw-edition/coverage.json")
        report = publication_report()
        self.assertEqual(coverage["registry_sources"], 758)
        self.assertEqual(coverage["core_reviewed_entries"], report["publication_completed_entries"])
        self.assertEqual(report["publication_completed_entries"], 278)
        self.assertFalse(report["publication_ready"])


if __name__ == "__main__":
    unittest.main()

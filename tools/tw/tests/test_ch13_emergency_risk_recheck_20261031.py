"""第13章熱傷害、火場、溺水與哽塞四篇高風險歷史再審契約。"""

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


EVIDENCE_PATH = "localization/ch13-emergency-risk-recheck-20261031.json"
ITEM_IDS = ("TW-13-022", "TW-13-024", "TW-13-025", "TW-13-026")
BASELINE = "302fb655c443965511231f24ad18dac4cff66afe"


def read(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def read_at(revision, path):
    raw = subprocess.check_output(["git", "show", f"{revision}:{path}"], cwd=ROOT)
    return json.loads(raw)


def sha256(data):
    return hashlib.sha256(data).hexdigest()


class EmergencyRiskRecheckTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.evidence = read(EVIDENCE_PATH)
        cls.runtime = validate_runtime()
        cls.items = {item["id"]: item for item in cls.runtime["items"]}
        cls.sources = {source["id"]: source for source in cls.runtime["sources"]}
        cls.manifest = {
            item["id"]: item for item in read("localization/manifest.json")["entries"]
        }
        cls.reviews = {
            item_id: read(f"localization/reviews/{item_id}.json")
            for item_id in ITEM_IDS
        }
        register = read("localization/retroactive-review-register-20261019.json")
        # 一個核心可能有多次再審；驗證本批正文時必須取日期最新的紀錄，
        # 保留較早紀錄作為歷史鏈的一部分，不可讓舊 SHA 遮蔽新紀錄。
        cls.records = {}
        for item in sorted(
            register["substantive_rechecks"],
            key=lambda row: (row.get("reviewed_at", ""), row.get("after_sha256", "")),
        ):
            cls.records[item["id"]] = item
        cls.evidence_items = {item["id"]: item for item in cls.evidence["items"]}

    def test_counts_reconcile_to_latest_main_and_dynamic_coverage(self):
        self.assertEqual(self.evidence["baseline_main_sha"], BASELINE)
        self.assertEqual(set(self.evidence_items), set(ITEM_IDS))
        before = self.evidence["counts_before"]
        after = self.evidence["counts_after"]
        previous_coverage = read_at(BASELINE, "localization/tw-edition/coverage.json")
        previous_runtime = read_at(BASELINE, "localization/tw-edition/runtime.json")
        previous_register = read_at(
            BASELINE, "localization/retroactive-review-register-20261019.json"
        )
        coverage = read("localization/tw-edition/coverage.json")
        current_runtime = read("localization/tw-edition/runtime.json")
        current_register = read("localization/retroactive-review-register-20261019.json")

        self.assertEqual(before["core_completed"], previous_coverage["publication_completed_entries"])
        self.assertEqual(before["runtime_items"], len(previous_runtime["items"]))
        self.assertEqual(before["runtime_sources_before"], len(previous_runtime["sources"]))
        self.assertEqual(before["substantive_rechecks_before"], len(previous_register["substantive_rechecks"]))
        self.assertEqual(after["core_completed"], coverage["publication_completed_entries"])
        self.assertEqual(after["core_completed"], before["core_completed"])
        self.assertEqual(after["core_total"], coverage["publication_total_entries"])
        self.assertEqual(after["runtime_items"], len(current_runtime["items"]))
        self.assertEqual(after["runtime_sources"], len(current_runtime["sources"]))
        self.assertEqual(
            after["runtime_sources"],
            before["runtime_sources_before"] + len(self.evidence["new_source_ids"]),
        )
        self.assertEqual(after["source_registry"], coverage["registry_sources"])
        self.assertEqual(after["json_files"], coverage["json_files_checked"])
        self.assertEqual(after["coverage_json_files"], coverage["json_files_checked"])
        self.assertEqual(after["substantive_rechecks"], len(current_register["substantive_rechecks"]))
        self.assertEqual(
            after["substantive_rechecks"], before["substantive_rechecks_before"] + len(ITEM_IDS)
        )
        self.assertEqual(after["unresolved_source_ids"], len(coverage["unresolved_source_ids"]))
        self.assertEqual(
            after["unresolved_reference_occurrences"], coverage["unresolved_reference_occurrences"]
        )
        self.assertFalse(after["publication_ready"])
        self.assertEqual(coverage, audit_drafts())
        self.assertEqual(coverage["publication_completed_entries"], publication_report()["publication_completed_entries"])

    def test_historical_sources_bodies_reviews_and_runtime_align(self):
        for item_id in ITEM_IDS:
            with self.subTest(item=item_id):
                item = self.items[item_id]
                record = self.records[item_id]
                evidence = self.evidence_items[item_id]
                review = self.reviews[item_id]
                manifest = self.manifest[item_id]
                body_bytes = (ROOT / manifest["target_path"]).read_bytes()
                body = body_bytes.decode("utf-8")
                body_sha = sha256(body_bytes)

                self.assertEqual(record, evidence)
                self.assertEqual(record["prior_revision"], BASELINE)
                self.assertEqual(record["before_sha256"], sha256(record["previous_body"].encode("utf-8")))
                self.assertEqual(record["after_sha256"], body_sha)
                self.assertEqual(item["body"], body)
                self.assertIn("# " + item["title"], body)
                self.assertEqual(sum(line.startswith("## ") for line in body.splitlines()), 5)
                self.assertEqual(body_sha, review["target_sha256"])
                self.assertEqual(body_sha, review["source_reviewed_sha256"])
                self.assertIn(item["limits"], review["limits"])
                self.assertIn(item["title"], item["question"])
                self.assertNotRegex(item["limits"], r"本次|本批|AI|專業審閱仍待")
                self.assertEqual(manifest["verified_at"], review["reviewed_at"])
                self.assertEqual(item["reviewed_at"], review["reviewed_at"])
                self.assertEqual(item["source_ids"], manifest["sources"])
                self.assertEqual(item["source_ids"], record["source_ids"])
                self.assertEqual(
                    {source["url"] for source in review["source_checks"]},
                    {self.sources[sid]["url"] for sid in item["source_ids"]},
                )
                body_urls = set(re.findall(r"\]\((https://[^)]+)\)", body))
                self.assertEqual(body_urls, {self.sources[sid]["url"] for sid in item["source_ids"]})
                self.assertNotRegex(body, r"本批|本次再審|來源實質再核對|PR\s*#|CI\s*(?:通過|成功)|專業審閱仍待")
                self.assertNotIn("先救命再看統計", body)
                validate_recheck_history(ROOT, record, item)

    def test_frequency_records_identify_unit_scope_and_missing_denominators(self):
        expected = {
            "TW-13-022": ("683", "急診就醫人次", "ch13_heat_hpa_20250822"),
            "TW-13-024": ("25,895", "建築物火災", "ch01_nfa_fire_2025"),
            "TW-13-025": ("4,597", "溺水人數", "retro_drown_nfa_2025"),
            "TW-13-026": ("W79：138；W80：107", "死亡人數", "ch13_choke_mohw_death_2025"),
        }
        for item_id, (value, unit, source_id) in expected.items():
            with self.subTest(item=item_id):
                stats = self.records[item_id]["statistics_assessed"]
                self.assertTrue(any(value in row["value"] for row in stats))
                self.assertTrue(any(unit in row["unit"] for row in stats))
                self.assertTrue(any(row["source_id"] == source_id for row in stats))
                for row in stats:
                    for field in (
                        "value", "unit", "period", "geographic_scope", "population",
                        "numerator", "denominator_definition", "event_definition",
                        "data_type", "accessed_at", "limitations",
                    ):
                        self.assertTrue(row.get(field), (item_id, field))

        heat = self.records["TW-13-022"]["statistics_assessed"][0]
        self.assertIsNone(heat["denominator"])
        self.assertIn("不是唯一患者", heat["limitations"])
        fire = self.records["TW-13-024"]["statistics_assessed"][0]
        self.assertIn("25,895", fire["denominator"])
        self.assertIn("未提供住宅戶數", fire["denominator"])
        drowning = self.records["TW-13-025"]["statistics_assessed"]
        self.assertTrue(any("2,888" in row["value"] and "62.8%" in row["value"] for row in drowning))
        self.assertTrue(any("631" in row["value"] for row in drowning))
        choking = self.records["TW-13-026"]["statistics_assessed"][0]
        self.assertIsNone(choking["denominator"])
        self.assertIn("不含存活", choking["limitations"])

    def test_reader_copy_puts_emergency_action_first_and_uses_current_taiwan_guidance(self):
        bodies = {key: self.items[key]["body"] for key in ITEM_IDS}
        self.assertLess(bodies["TW-13-022"].index("打119"), bodies["TW-13-022"].index("683人次"))
        self.assertLess(bodies["TW-13-024"].index("打119"), bodies["TW-13-024"].index("25,895件"))
        self.assertLess(bodies["TW-13-025"].index("打119"), bodies["TW-13-025"].index("4,597人"))
        self.assertLess(bodies["TW-13-026"].index("打119"), bodies["TW-13-026"].index("死亡138人"))

        fire = bodies["TW-13-024"]
        self.assertIn("不要進入或硬闖", fire)
        self.assertNotIn("低姿勢爬", fire)
        self.assertIn("公寓大樓", fire)
        self.assertIn("租屋處", fire)

        drowning = bodies["TW-13-025"]
        self.assertIn("海巡署118", drowning)
        self.assertIn("不要因為會游泳就直接跳下水", drowning)
        self.assertIn("溪水暴漲", drowning)

        choking = bodies["TW-13-026"]
        for phrase in ("拍擊5次", "5次腹部推擠", "孕婦", "胸部推擠", "嬰兒", "盲挖"):
            self.assertIn(phrase, choking)
        self.assertIn("能說話或有效咳嗽", choking)
        self.assertIn("咳嗽微弱或無聲", choking)
        self.assertNotIn("還能說話、呼吸或大聲咳嗽", choking)
        self.assertNotIn("沒有全國一致", choking)
        self.assertIn("依派遣員指示", choking)


if __name__ == "__main__":
    unittest.main()

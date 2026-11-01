# -*- coding: utf-8 -*-
"""第16、17、24章長照、壓傷、急診分級與癌後運動歷史實質再審。"""
import hashlib
import json
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import retroactive_audit as audit
from ci_language_policy import audit_drafts
from review_contract import ROOT, publication_report, validate_runtime

BASE = "349bbc8957a9ceff7d75dcec2327c6544af764ec"
IDS = ("TW-16-014", "TW-17-007", "TW-17-008", "TW-24-007")
NEW_SOURCE_IDS = {
    "ch17_ltc_allowance_2026",
    "ltc_device_rule_2026",
    "ltc_smart_assistive_2026",
    "mohw_homecare_pressure",
    "ch24_triage_standards_2026",
    "ch16_challenge_os_2026",
}


def read(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def git_bytes(revision, path):
    return subprocess.check_output(["git", "show", f"{revision}:{path}"], cwd=ROOT)


class MedicalCareP1RecheckTests(unittest.TestCase):
    def test_rechecks_preserve_history_and_sync_reader_contracts(self):
        old_runtime = json.loads(git_bytes(BASE, "localization/tw-edition/runtime.json"))
        old_sources = {row["id"]: row for row in old_runtime["sources"]}
        old_items = {row["id"]: row for row in old_runtime["items"]}
        runtime = validate_runtime()
        current_sources = {row["id"]: row for row in runtime["sources"]}
        items = {row["id"]: row for row in runtime["items"]}
        manifest = {row["id"]: row for row in read("localization/manifest.json")["entries"]}
        records = {row["id"]: row for row in read(
            "localization/retroactive-review-register-20261019.json")["substantive_rechecks"]}

        self.assertEqual(old_runtime["sources"], [row for row in runtime["sources"] if row["id"] in old_sources])
        self.assertTrue(NEW_SOURCE_IDS <= set(current_sources) - set(old_sources))
        self.assertEqual({row["id"] for row in runtime["items"] if not row["id"].startswith("TW-NAV-")},
                         {row["id"] for row in old_runtime["items"] if not row["id"].startswith("TW-NAV-")})

        for item_id in IDS:
            with self.subTest(item_id=item_id):
                item = items[item_id]
                row = records[item_id]
                review = read(f"localization/reviews/{item_id}.json")
                prior_review = git_bytes(BASE, f"localization/reviews/{item_id}.json")
                body_bytes = (ROOT / item["target_path"]).read_bytes()
                digest = hashlib.sha256(body_bytes).hexdigest()
                self.assertEqual(row["prior_revision"], BASE)
                self.assertEqual(row["prior_review_sha256"], hashlib.sha256(prior_review).hexdigest())
                self.assertEqual(row["before_sha256"], hashlib.sha256(old_items[item_id]["body"].encode()).hexdigest())
                self.assertEqual(row["after_sha256"], digest)
                self.assertNotEqual(row["before_sha256"], row["after_sha256"])
                self.assertEqual(item["body"], body_bytes.decode("utf-8"))
                self.assertEqual(review["target_sha256"], digest)
                self.assertEqual(review["source_checks"], row["source_checks"])
                self.assertEqual(row["limits"], review["limits"])
                self.assertEqual(manifest[item_id]["sources"], item["source_ids"])
                self.assertEqual(
                    {current_sources[source_id]["url"] for source_id in item["source_ids"]},
                    {check["url"] for check in review["source_checks"]},
                )
                self.assertEqual(item["reviewed_at"], "2026-11-01")
                self.assertEqual(item["review_due_at"], "2027-01-31")
                self.assertEqual(row["status"], "ai_source_rechecked_professional_pending")
                for check in review["source_checks"]:
                    self.assertGreaterEqual(len(check["supporting_passage"]), 50)
                    self.assertTrue(check["retrieval_method"].strip())
                audit.validate_recheck_history(ROOT, row, item)

        law_check = next(
            check for check in read("localization/reviews/TW-17-007.json")["source_checks"]
            if check["url"] == "https://law.moj.gov.tw/LawClass/LawAll.aspx?pcode=L0070040"
        )
        self.assertIn("第2條規定中央與地方主管機關", law_check["supporting_passage"])
        self.assertIn("第3條第1款定義", law_check["supporting_passage"])
        self.assertEqual(law_check["supporting_passage"], next(
            check["supporting_passage"]
            for check in records["TW-17-007"]["source_checks"]
            if check["url"] == law_check["url"]
        ))

        self.assertEqual(items["TW-17-008"]["source_ids"].count("ch17_pressure"), 0)
        retired = records["TW-17-008"]["retired_sources"]
        self.assertEqual([entry["id"] for entry in retired], ["ch17_pressure"])
        self.assertIn("mohw_homecare_pressure", retired[0]["replacement_ids"])

    def test_taiwan_specific_claims_and_statistical_limits_remain_explicit(self):
        items = {row["id"]: row for row in validate_runtime()["items"]}
        ltc = items["TW-17-007"]["body"]
        pressure = items["TW-17-008"]["body"]
        triage = items["TW-24-007"]["body"]
        exercise = items["TW-16-014"]["body"]

        for phrase in ("2026年7月1日", "每3年最高4萬元", "每3年最高6萬元", "兩組二擇一", "甲類輔具評估人員", "第二類自付5%至10%", "第三類自付16%至30%"):
            self.assertIn(phrase, ltc)
        self.assertIn("同定義全臺失能發生率", ltc)
        self.assertIn("目前沒有可代表全臺居家臥床者", pressure)
        self.assertIn("不能完全取代變換姿勢", pressure)
        self.assertIn("不是壓傷專款", pressure)
        self.assertIn("兒童版、成人非外傷版", triage)
        self.assertIn("民眾不宜用網路表格自行分級", triage)
        for phrase in ("889人", "80.3%對73.9%", "90.3%對83.2%", "95%信賴區間", "不是臺灣全國術後發生率"):
            self.assertIn(phrase, exercise)

        evidence = read("localization/medical-care-p1-recheck-20261101.json")
        stats = {row["id"]: row for row in evidence["statistics"]}
        self.assertEqual(set(stats), {
            "challenge_5y_disease_free_survival",
            "challenge_8y_overall_survival",
            "challenge_musculoskeletal_adverse_events",
        })
        self.assertEqual(stats["challenge_5y_disease_free_survival"]["value"]["difference_95_ci_percentage_points"], [0.6, 12.2])
        self.assertEqual(stats["challenge_8y_overall_survival"]["value"]["difference_95_ci_percentage_points"], [1.8, 12.3])
        self.assertIsNone(stats["challenge_5y_disease_free_survival"]["numerator"])
        self.assertIsNone(stats["challenge_5y_disease_free_survival"]["denominator"])
        self.assertIn("風險集", stats["challenge_5y_disease_free_survival"]["denominator_definition"])
        self.assertIsNone(stats["challenge_musculoskeletal_adverse_events"]["denominator"])
        self.assertEqual(evidence["new_core_entries"], [])

    def test_progress_is_unchanged_and_publication_remains_incomplete(self):
        current = validate_runtime()
        old_runtime = json.loads(git_bytes(BASE, "localization/tw-edition/runtime.json"))
        current_core = {row["id"] for row in current["items"] if not row["id"].startswith("TW-NAV-")}
        old_core = {row["id"] for row in old_runtime["items"] if not row["id"].startswith("TW-NAV-")}
        self.assertEqual(current_core, old_core)
        report = publication_report()
        coverage = read("localization/tw-edition/coverage.json")
        draft_coverage = audit_drafts()
        self.assertEqual(coverage["json_files_checked"], draft_coverage["json_files_checked"])
        self.assertEqual(coverage["registry_sources"], draft_coverage["registry_sources"])
        self.assertEqual(report["publication_completed_entries"], coverage["publication_completed_entries"])
        self.assertEqual(report["publication_completed_entries"], coverage["core_reviewed_entries"])
        self.assertFalse(report["publication_ready"])
        self.assertFalse(coverage["publication_ready"])


if __name__ == "__main__":
    unittest.main()

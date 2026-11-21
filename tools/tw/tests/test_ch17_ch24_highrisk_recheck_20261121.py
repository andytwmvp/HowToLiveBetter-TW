"""第17、24章高風險歷史內容於2026-11-21的實質再審契約。"""
import hashlib
import json
import re
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools/tw"))
import retroactive_audit as audit
from ci_language_policy import audit_drafts
from review_contract import publication_report, validate_runtime
from source_bundle_test_support import source_bundle_ids_added_since

BASE = "ce06f4b2f2493e8f6becb02cc2834e599d6f4303"
DATE = "2026-11-21"
DUE = "2027-02-21"
REGISTER = "localization/retroactive-review-register-20261019.json"
BUNDLE = "localization/tw-edition/sources/ch17-ch24-highrisk-recheck-20261121.json"
EVIDENCE = "localization/ch17-ch24-highrisk-recheck-20261121.json"
IDS = ("TW-24-006", "TW-17-003", "TW-24-009", "TW-17-001")
SPECS = {
    "TW-24-006": {
        "path": "locales/zh-TW/book/ch24/TW-24-006.md",
        "new_sources": {"ch24_medical_accident_care_5day_20261121"},
    },
    "TW-17-003": {
        "path": "locales/zh-TW/book/ch17/TW-17-003.md",
        "new_sources": {
            "ch17_elder_protection_stats_2025_20261121",
            "ch17_elder_protection_stats_method_20261121",
        },
    },
    "TW-24-009": {
        "path": "locales/zh-TW/book/ch24/TW-24-009.md",
        "new_sources": {
            "ch24_major_illness_effective_dates_20261121",
            "ch24_disability_process_law_20261121",
        },
    },
    "TW-17-001": {
        "path": "locales/zh-TW/book/ch17/TW-17-001.md",
        "new_sources": set(),
    },
}
NEW_SOURCE_IDS = set().union(*(spec["new_sources"] for spec in SPECS.values()))


def read(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def git_bytes(revision, path):
    result = subprocess.run(
        ["git", "show", f"{revision}:{path}"], cwd=ROOT, capture_output=True
    )
    return result.stdout if result.returncode == 0 else None


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


class Ch17Ch24HighriskRecheck20261121Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.runtime = validate_runtime()
        cls.items = {row["id"]: row for row in cls.runtime["items"]}
        cls.sources = {row["id"]: row for row in cls.runtime["sources"]}
        cls.manifest = {
            row["id"]: row for row in read("localization/manifest.json")["entries"]
        }
        cls.reviews = {key: read(f"localization/reviews/{key}.json") for key in IDS}
        cls.register = read(REGISTER)
        cls.rows = cls.register["substantive_rechecks"]
        cls.batch_rows = {
            key: next(
                row for row in reversed(cls.rows)
                if row["id"] == key and row["prior_revision"] == BASE
            )
            for key in IDS
        }
        cls.coverage = read("localization/tw-edition/coverage.json")
        cls.evidence = read(EVIDENCE)
        cls.bundle = read(BUNDLE)

    def test_append_only_history_and_prior_revisions_are_preserved(self):
        baseline_register = json.loads(git_bytes(BASE, REGISTER))
        baseline_runtime = json.loads(
            git_bytes(BASE, "localization/tw-edition/runtime.json")
        )
        baseline_rows = baseline_register["substantive_rechecks"]
        self.assertEqual(self.rows[:len(baseline_rows)], baseline_rows)
        baseline_items = {row["id"]: row for row in baseline_runtime["items"]}
        baseline_sources = {row["id"]: row for row in baseline_runtime["sources"]}
        for key in IDS:
            with self.subTest(id=key):
                row = self.batch_rows[key]
                review = self.reviews[key]
                prior_body = baseline_items[key]["body"].encode("utf-8")
                prior_review = git_bytes(BASE, f"localization/reviews/{key}.json")
                body = (ROOT / SPECS[key]["path"]).read_bytes()
                item = self.items[key]
                self.assertEqual(row["before_sha256"], digest(prior_body))
                self.assertEqual(row["previous_body"], baseline_items[key]["body"])
                self.assertEqual(row["prior_review_sha256"], digest(prior_review))
                self.assertEqual(row["after_sha256"], digest(body))
                self.assertEqual(row["review_sha256"], digest(
                    (ROOT / f"localization/reviews/{key}.json").read_bytes()
                ))
                self.assertEqual(row["status"], "ai_source_rechecked_professional_pending")
                self.assertEqual((row["reviewed_at"], row["review_due_at"]), (DATE, DUE))
                self.assertEqual(item["body"].encode("utf-8"), body)
                self.assertEqual((item["reviewed_at"], item["review_due_at"]), (DATE, DUE))
                self.assertEqual(self.manifest[key]["verified_at"], DATE)
                self.assertEqual(review["target_sha256"], digest(body))
                self.assertEqual(review["source_reviewed_sha256"], digest(body))
                self.assertEqual(review["source_checks"], row["source_checks"])
                self.assertEqual(review["legal_temporal_checks"], row["legal_temporal_checks"])
                self.assertEqual(review["limits"], row["limits"])
                self.assertEqual(review["prior_review_sha256"], digest(prior_review))
                self.assertEqual(row["source_bundle_path"], BUNDLE)
                self.assertEqual(row["source_bundle_sha256"], digest(
                    (ROOT / BUNDLE).read_bytes()
                ))
                self.assertEqual(review["professional_review"]["required"], True)
                self.assertEqual(review["professional_review"]["obtained"], False)
                self.assertTrue(review["unresolved_questions"])
                self.assertEqual(row["statistics_assessed"], review["statistics_assessed"])
                self.assertEqual(self.manifest[key]["sources"], item["source_ids"])
                self.assertEqual(review["source_ids"], item["source_ids"])

                body_urls = {
                    url.rstrip(".,;，。；")
                    for url in re.findall(r"https://[^\s)>]+", body.decode("utf-8"))
                }
                source_urls = {self.sources[sid]["url"] for sid in item["source_ids"]}
                review_urls = {check["url"] for check in review["source_checks"]}
                self.assertEqual(body_urls, source_urls)
                self.assertEqual(review_urls, source_urls)
                self.assertEqual(
                    {check["source_id"] for check in review["source_checks"]},
                    set(item["source_ids"]),
                )
                for check in review["source_checks"]:
                    self.assertTrue(check["supporting_passage"])
                    self.assertLessEqual(check["accessed_at"], DATE)
                    self.assertTrue(check["retrieval_method"])
                audit.validate_recheck_history(ROOT, row, item)

        self.assertEqual(self.runtime["sources"][:len(baseline_runtime["sources"])],
                         baseline_runtime["sources"])
        self.assertEqual(set(self.sources) - set(baseline_sources), NEW_SOURCE_IDS)
        self.assertEqual(source_bundle_ids_added_since(ROOT, BASE), NEW_SOURCE_IDS)
        self.assertEqual({source[0] for source in self.bundle["sources"]}, NEW_SOURCE_IDS)

    def test_taiwan_risk_guidance_and_statistical_limits_are_specific(self):
        elder_protection = self.items["TW-17-003"]["body"]
        self.assertIn("30,576通報件次", elder_protection)
        self.assertIn("26,684件通報案件", elder_protection)
        self.assertIn("362通報人次", elder_protection)
        self.assertIn("沒有全體長者或財務接觸人數作分母", elder_protection)
        self.assertIn("不能換算發生率或個人受害機率", elder_protection)
        stats = self.reviews["TW-17-003"]["statistics_assessed"]
        self.assertEqual(len(stats), 1)
        stat = stats[0]
        self.assertEqual(stat["period"], "2025-01-01至2025-12-31")
        self.assertEqual(stat["scope"].startswith("臺灣全國"), True)
        self.assertEqual(stat["numerator"], {
            "report_forms": 30576,
            "deduplicated_report_cases": 26684,
            "economic_violence_person_times": 362,
        })
        self.assertIsNone(stat["denominator"])
        self.assertIn("行政通報紀錄", stat["data_type"])
        self.assertIn("同一被害人、同一案發年月日", stat["event_definition"])
        self.assertTrue(stat["limitations"])

        medical_dispute = self.items["TW-24-006"]["body"]
        self.assertIn("醫療事故", medical_dispute)
        self.assertIn("翌日起五個工作日內", medical_dispute)
        self.assertIn("不等於承認過失或賠償責任", medical_dispute)
        self.assertIn("先119或立即告知醫護", medical_dispute)
        self.assertIsNone(self.reviews["TW-24-006"]["statistics_assessed"][0]["denominator"])

        entitlements = self.items["TW-24-009"]["body"]
        self.assertIn("自提出申請日生效", entitlements)
        self.assertIn("罕見疾病", entitlements)
        self.assertIn("屆滿前三個月內", entitlements)
        self.assertIn("屆滿前一個月內", entitlements)
        self.assertIn("屆滿前十四日內", entitlements)
        self.assertIn("自新申請日生效", entitlements)
        self.assertIn("身心障礙者福利與服務需求評估及證明核發辦法", entitlements)

        guardianship = self.items["TW-17-001"]["body"]
        self.assertIn("民法第1113-2至1113-10條", guardianship)
        self.assertIn("不是公證當下生效", guardianship)
        self.assertIn("不能把未生效修正套用到本篇程序", guardianship)

    def test_legal_temporal_checks_separate_promulgation_from_effective_dates(self):
        checks = {
            key: {entry["law"]: entry for entry in review["legal_temporal_checks"]}
            for key, review in self.reviews.items()
        }

        civil = checks["TW-17-001"]["民法"]["relevant_provision_amendments"]
        self.assertEqual(
            next(row for row in civil if row["provisions"] == ["第1101條", "第1113條"])
            ["promulgated_at"],
            "2008-05-23",
        )
        self.assertEqual(
            next(row for row in civil if row["provisions"] == ["第1101條", "第1113條"])
            ["effective_at"],
            "2009-11-23",
        )
        self.assertEqual(
            next(row for row in civil if row["provisions"] == ["第1113-2條至第1113-10條"])
            ["promulgated_at"],
            "2019-06-19",
        )
        self.assertEqual(
            next(row for row in civil if row["provisions"] == ["第1113-2條至第1113-10條"])
            ["effective_at"],
            "2019-06-21",
        )

        family_violence = checks["TW-17-003"]["家庭暴力防治法"]
        self.assertEqual(
            family_violence["relevant_provision_amendments"][0]["promulgated_at"],
            "2015-02-04",
        )
        self.assertEqual(
            family_violence["relevant_provision_amendments"][0]["effective_at"],
            "2015-02-06",
        )

        med_accident = checks["TW-24-006"]["醫療事故預防及爭議處理法"]
        self.assertEqual(med_accident["promulgated_at"], "2022-06-22")
        self.assertEqual(med_accident["effective_at"], "2024-01-01")
        med_care = checks["TW-24-006"]["醫療法"]["relevant_provision_amendments"][0]
        self.assertEqual(med_care["promulgated_at"], "2004-04-28")
        self.assertEqual(med_care["effective_at"], "2004-04-30")

        nhi = checks["TW-24-009"]["全民健康保險保險對象免自行負擔費用辦法"]
        self.assertEqual(nhi["relevant_provision_amendment"]["promulgated_at"], "2022-12-19")
        self.assertEqual(nhi["relevant_provision_amendment"]["effective_at"], "2022-12-21")
        disability = checks["TW-24-009"]["身心障礙者福利與服務需求評估及證明核發辦法"]
        self.assertEqual(disability["relevant_provision_amendment"]["promulgated_at"], "2023-05-26")
        self.assertEqual(disability["relevant_provision_amendment"]["effective_at"], "2023-05-28")

        evidence_checks = self.evidence["legal_temporal_checks"]
        self.assertEqual(
            {entry["article_id"]: entry["checks"] for entry in evidence_checks},
            {key: review["legal_temporal_checks"] for key, review in self.reviews.items()},
        )
        self.assertEqual(self.bundle["legal_temporal_checks"], evidence_checks)

    def test_stage_counts_match_baseline_and_dynamic_coverage(self):
        baseline_coverage = json.loads(
            git_bytes(BASE, "localization/tw-edition/coverage.json")
        )
        baseline_runtime = json.loads(
            git_bytes(BASE, "localization/tw-edition/runtime.json")
        )
        baseline_register = json.loads(git_bytes(BASE, REGISTER))
        before = self.evidence["counts_before"]
        after = self.evidence["counts_after"]
        self.assertEqual(before["core_reviewed_entries"],
                         baseline_coverage["core_reviewed_entries"])
        self.assertEqual(before["runtime_items"], len(baseline_runtime["items"]))
        self.assertEqual(before["runtime_sources"], len(baseline_runtime["sources"]))
        self.assertEqual(before["source_registry"], baseline_coverage["registry_sources"])
        self.assertEqual(before["json_files_checked"], baseline_coverage["json_files_checked"])
        self.assertEqual(before["substantive_rechecks"],
                         len(baseline_register["substantive_rechecks"]))
        self.assertEqual(after["core_reviewed_entries"], before["core_reviewed_entries"])
        self.assertEqual(after["runtime_items"], before["runtime_items"])
        self.assertEqual(after["runtime_sources"], before["runtime_sources"] + len(NEW_SOURCE_IDS))
        self.assertEqual(after["source_registry"], before["source_registry"] + len(NEW_SOURCE_IDS))
        self.assertEqual(after["json_files_checked"], before["json_files_checked"] + 2)
        self.assertEqual(after["substantive_rechecks"],
                         before["substantive_rechecks"] + len(IDS))
        self.assertFalse(after["publication_ready"])
        self.assertEqual(self.coverage, audit_drafts())
        self.assertFalse(self.coverage["publication_ready"])
        self.assertFalse(publication_report()["publication_ready"])
        self.assertEqual(self.evidence["baseline_main_sha"], BASE)
        self.assertEqual(self.evidence["scope"]["new_core_ids"], [])
        self.assertEqual(self.evidence["scope"]["historical_core_ids"], list(IDS))
        self.assertEqual(self.evidence["scope"]["priority_order"], list(IDS))
        self.assertEqual(self.evidence["new_source_ids"], sorted(NEW_SOURCE_IDS))
        self.assertFalse(self.evidence["publication_ready"])


if __name__ == "__main__":
    unittest.main()

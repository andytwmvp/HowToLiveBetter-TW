"""第16、17、24章高風險醫療與照護歷史內容再審契約。"""
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

BASE = "61a680dd537da3e65d5a3381b7b7530f220fb1d9"
DATE = "2026-11-23"
DUE = "2027-02-23"
REGISTER = "localization/retroactive-review-register-20261019.json"
BUNDLE = "localization/tw-edition/sources/ch16-17-24-health-rights-recheck-20261123.json"
EVIDENCE = "localization/ch16-17-24-health-rights-recheck-20261123.json"
IDS = ("TW-16-003", "TW-17-012", "TW-24-005", "TW-24-012")
SPECS = {
    "TW-16-003": {
        "path": "locales/zh-TW/book/ch16/TW-16-003.md",
        "new_sources": {
            "tw16_hpa_bp_schedule_20261123",
            "tw16_hpa_home_measurement_20261123",
            "tw16_hpa_survey_method_20261123",
        },
        "retired_sources": {"ch16_hpa_722", "ch16_ada_kidney", "risk_bp_722"},
    },
    "TW-17-012": {
        "path": "locales/zh-TW/book/ch17/TW-17-012.md",
        "new_sources": {"tw17_leave_rule_history_20261123"},
        "retired_sources": set(),
    },
    "TW-24-005": {
        "path": "locales/zh-TW/book/ch24/TW-24-005.md",
        "new_sources": {"tw24_medical_law_gazette_20261123"},
        "retired_sources": set(),
    },
    "TW-24-012": {
        "path": "locales/zh-TW/book/ch24/TW-24-012.md",
        "new_sources": {
            "tw24_implant_consent_template_20261123",
            "tw24_taiwan_implant_cohort_20261123",
        },
        "retired_sources": set(),
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


class Ch16Ch17Ch24HealthRightsRecheck20261123Tests(unittest.TestCase):
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
                row
                for row in reversed(cls.rows)
                if row["id"] == key and row["prior_revision"] == BASE
            )
            for key in IDS
        }
        cls.coverage = read("localization/tw-edition/coverage.json")
        cls.evidence = read(EVIDENCE)
        cls.bundle = read(BUNDLE)

    def test_append_only_history_hashes_sources_and_runtime_are_consistent(self):
        baseline_register = json.loads(git_bytes(BASE, REGISTER))
        baseline_runtime = json.loads(
            git_bytes(BASE, "localization/tw-edition/runtime.json")
        )
        baseline_manifest = {
            row["id"]: row
            for row in json.loads(git_bytes(BASE, "localization/manifest.json"))["entries"]
        }
        baseline_rows = baseline_register["substantive_rechecks"]
        self.assertEqual(self.rows[: len(baseline_rows)], baseline_rows)
        baseline_items = {row["id"]: row for row in baseline_runtime["items"]}
        baseline_sources = {row["id"]: row for row in baseline_runtime["sources"]}

        for key in IDS:
            with self.subTest(id=key):
                spec = SPECS[key]
                row = self.batch_rows[key]
                review = self.reviews[key]
                prior_body = baseline_items[key]["body"].encode("utf-8")
                prior_review = git_bytes(BASE, f"localization/reviews/{key}.json")
                body = (ROOT / spec["path"]).read_bytes()
                body_sha = digest(body)
                item = self.items[key]
                manifest = self.manifest[key]
                review_bytes = (ROOT / f"localization/reviews/{key}.json").read_bytes()

                self.assertEqual(row["before_sha256"], digest(prior_body))
                self.assertEqual(row["previous_body"], baseline_items[key]["body"])
                self.assertEqual(row["prior_review_sha256"], digest(prior_review))
                self.assertEqual(row["after_sha256"], body_sha)
                self.assertEqual(row["review_sha256"], digest(review_bytes))
                self.assertEqual(row["status"], "ai_source_rechecked_professional_pending")
                self.assertEqual((row["reviewed_at"], row["review_due_at"]), (DATE, DUE))
                self.assertEqual(item["body"].encode("utf-8"), body)
                self.assertEqual((item["reviewed_at"], item["review_due_at"]), (DATE, DUE))
                self.assertEqual(manifest["verified_at"], DATE)
                self.assertEqual(manifest["sources"], item["source_ids"])
                self.assertEqual(set(item["source_ids"]) & spec["new_sources"], spec["new_sources"])
                self.assertEqual(
                    set(baseline_manifest[key]["sources"]) - set(item["source_ids"]),
                    spec["retired_sources"],
                )
                self.assertEqual(review["target_sha256"], body_sha)
                self.assertEqual(review["source_reviewed_sha256"], body_sha)
                self.assertEqual(review["source_ids"], item["source_ids"])
                self.assertEqual(review["source_checks"], row["source_checks"])
                self.assertEqual(review["legal_temporal_checks"], row["legal_temporal_checks"])
                self.assertEqual(review["statistics_assessed"], row["statistics_assessed"])
                self.assertEqual(review["limits"], row["limits"])
                self.assertEqual(review["prior_review_sha256"], digest(prior_review))
                self.assertEqual(review["prior_source_checks"], row["prior_source_checks"])
                self.assertEqual(row["source_bundle_path"], BUNDLE)
                self.assertEqual(
                    review["source_bundle_sha256"], digest((ROOT / BUNDLE).read_bytes())
                )
                self.assertEqual(row["source_bundle_sha256"], digest((ROOT / BUNDLE).read_bytes()))
                self.assertTrue(review["professional_review"]["required"])
                self.assertFalse(review["professional_review"]["obtained"])
                self.assertTrue(review["unresolved_questions"])
                self.assertEqual(item["limits"], row["limits"][0])

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

                for retired in row["retired_sources"]:
                    prior_source = baseline_sources[retired["id"]]
                    self.assertEqual(self.sources[retired["id"]], prior_source)
                    self.assertEqual(
                        retired["prior_source_sha256"],
                        digest(json.dumps(prior_source, ensure_ascii=False, sort_keys=True).encode()),
                    )

        self.assertEqual(
            self.runtime["sources"][: len(baseline_runtime["sources"])],
            baseline_runtime["sources"],
        )
        self.assertEqual(NEW_SOURCE_IDS, set(self.sources) - set(baseline_sources))
        self.assertEqual(NEW_SOURCE_IDS, source_bundle_ids_added_since(ROOT, BASE))
        self.assertEqual({source[0] for source in self.bundle["sources"]}, NEW_SOURCE_IDS)

    def test_statistics_and_law_dates_keep_their_scope(self):
        bp = self.items["TW-16-003"]["body"]
        self.assertIn("每年至少做一次居家722", bp)
        self.assertIn("每3個月在回診前做一次", bp)
        self.assertIn("盛行率為30.4%", bp)
        self.assertIn("2022至2025年", bp)
        bp_stat = self.reviews["TW-16-003"]["statistics_assessed"][0]
        self.assertEqual(bp_stat["value"], 30.4)
        self.assertEqual(bp_stat["numerator"], None)
        self.assertEqual(bp_stat["denominator"], None)
        self.assertIn("不完全一致", bp_stat["limitations"])

        care = self.items["TW-17-012"]["body"]
        self.assertIn("2025年12月9日", care)
        self.assertIn("2026年1月1日施行", care)
        self.assertIn("只有第2條及第12條", care)
        self.assertNotIn("育兒修法", care)
        labor_law = next(
            check
            for check in self.reviews["TW-17-012"]["legal_temporal_checks"]
            if check["law"] == "勞工請假規則"
        )
        dates = [
            (amendment["promulgated_at"], amendment["effective_at"])
            for amendment in labor_law["relevant_provision_amendments"]
        ]
        self.assertEqual(dates, [("2025-12-09", "2026-01-01"), ("2026-09-30", "2026-10-01")])

        records = self.items["TW-24-005"]["body"]
        self.assertIn("第71條", records)
        self.assertIn("第73條", records)
        self.assertIn("第74條", records)
        self.assertIn("並未修改本篇引用的第71、73、74條", records)

    def test_implant_statistics_distinguish_units_and_study_limits(self):
        body = self.items["TW-24-012"]["body"]
        for phrase in (
            "685顆",
            "199位臺灣成年人",
            "92.58%",
            "81.38%",
            "71.00%",
            "38.02%",
            "單一牙周診所",
            "Kaplan–Meier",
            "不能換算成全臺成功率或個人保證",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, body)
        stats = self.reviews["TW-24-012"]["statistics_assessed"]
        self.assertEqual(len(stats), 5)
        self.assertEqual([row["value"] for row in stats[:4]], [92.58, 81.38, 71.00, 38.02])
        for row in stats[:4]:
            self.assertIsNone(row["numerator"])
            self.assertIsNone(row["denominator"])
            self.assertIn("Kaplan–Meier", row["denominator_definition"])
            self.assertTrue(
                any(term in row["limitations"] for term in ("診所", "全國", "個人"))
            )
        template = stats[4]
        self.assertEqual(template["value"], "80至90")
        self.assertIsNone(template["numerator"])
        self.assertIsNone(template["denominator"])
        self.assertIn("未附原研究", template["limitations"])

    def test_reader_copy_has_no_internal_process_and_expert_review_is_pending(self):
        forbidden = ("本批", "AI來源實質再審", "專業審閱仍待取得", "批次證據", "fork 維護")
        for key in IDS:
            body = self.items[key]["body"]
            for phrase in forbidden:
                with self.subTest(id=key, phrase=phrase):
                    self.assertNotIn(phrase, body)
            review = self.reviews[key]
            self.assertTrue(review["professional_review"]["required"])
            self.assertFalse(review["professional_review"]["obtained"])
        self.assertFalse(self.coverage["publication_ready"])
        self.assertFalse(publication_report()["publication_ready"])

    def test_dynamic_counts_match_this_batch_without_promoting_core_items(self):
        baseline_coverage = json.loads(
            git_bytes(BASE, "localization/tw-edition/coverage.json")
        )
        baseline_runtime = json.loads(
            git_bytes(BASE, "localization/tw-edition/runtime.json")
        )
        baseline_register = json.loads(git_bytes(BASE, REGISTER))
        before = self.evidence["counts_before"]
        after = self.evidence["counts_after"]
        self.assertEqual(before["core_reviewed_entries"], baseline_coverage["core_reviewed_entries"])
        self.assertEqual(before["runtime_items"], len(baseline_runtime["items"]))
        self.assertEqual(before["runtime_sources"], len(baseline_runtime["sources"]))
        self.assertEqual(before["source_registry"], baseline_coverage["registry_sources"])
        self.assertEqual(before["json_files_checked"], baseline_coverage["json_files_checked"])
        self.assertEqual(before["substantive_rechecks"], len(baseline_register["substantive_rechecks"]))
        self.assertEqual(after["core_reviewed_entries"], before["core_reviewed_entries"])
        self.assertEqual(after["runtime_items"], before["runtime_items"])
        self.assertEqual(after["runtime_sources"], len(self.runtime["sources"]))
        self.assertEqual(after["source_registry"], self.coverage["registry_sources"])
        self.assertEqual(after["json_files_checked"], self.coverage["json_files_checked"])
        self.assertEqual(after["substantive_rechecks"], len(self.rows))
        self.assertEqual(after["runtime_sources"], before["runtime_sources"] + len(NEW_SOURCE_IDS))
        self.assertEqual(after["source_registry"], before["source_registry"] + len(NEW_SOURCE_IDS))
        self.assertEqual(after["json_files_checked"], before["json_files_checked"] + 2)
        self.assertEqual(after["substantive_rechecks"], before["substantive_rechecks"] + len(IDS))
        self.assertFalse(after["publication_ready"])
        self.assertEqual(self.coverage, audit_drafts())
        self.assertEqual(self.evidence["baseline_main_sha"], BASE)
        self.assertEqual(self.evidence["scope"]["new_core_ids"], [])
        self.assertEqual(self.evidence["scope"]["historical_core_ids"], list(IDS))
        self.assertEqual(self.evidence["scope"]["priority_order"], list(IDS))
        self.assertEqual(self.evidence["new_source_ids"], sorted(NEW_SOURCE_IDS))
        self.assertFalse(self.evidence["publication_ready"])


if __name__ == "__main__":
    unittest.main()

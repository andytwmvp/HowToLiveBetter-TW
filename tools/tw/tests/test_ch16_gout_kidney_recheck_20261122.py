"""第16章痛風與糖尿病腎病高風險歷史內容於2026-11-22的實質再審契約。"""
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

BASE = "bf2400573a1f679a7bdc029454b9910731cc5926"
DATE = "2026-11-22"
DUE = "2027-02-22"
REGISTER = "localization/retroactive-review-register-20261019.json"
BUNDLE = "localization/tw-edition/sources/ch16-gout-kidney-recheck-20261122.json"
EVIDENCE = "localization/ch16-gout-kidney-recheck-20261122.json"
IDS = ("TW-16-009", "TW-16-013")
SPECS = {
    "TW-16-009": {
        "path": "locales/zh-TW/book/ch16/TW-16-009.md",
        "new_sources": {
            "ch16_acr_gout_wiley_20261122",
            "ch16_acr_gout_erratum_20261122",
            "risk_fda_allo_2023_20261122",
            "risk_allo_cohort_pmc_2015_20261122",
            "risk_nhi_hla_12213b_20261122",
        },
        "retired_sources": {"ch16_acr_gout", "risk_allo_cohort"},
    },
    "TW-16-013": {
        "path": "locales/zh-TW/book/ch16/TW-16-013.md",
        "new_sources": {
            "ch16_tsn_ckd_2025_20261122",
            "follow_hpa_egfr_order_2026_20261122",
            "follow_hpa_egfr_form_2026_20261122",
            "follow_hpa_kidney_stats_2026_20261122",
        },
        "retired_sources": {
            "ch16_ada_kidney", "ch16_kdigo_2024", "follow_kidney_stats"
        },
    },
}
NEW_SOURCE_IDS = set().union(*(row["new_sources"] for row in SPECS.values()))


def read(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def git_bytes(revision, path):
    result = subprocess.run(
        ["git", "show", f"{revision}:{path}"], cwd=ROOT, capture_output=True
    )
    return result.stdout if result.returncode == 0 else None


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


class Ch16GoutKidneyRecheck20261122Tests(unittest.TestCase):
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
        self.assertEqual(self.rows[:len(baseline_rows)], baseline_rows)
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
                self.assertEqual(set(baseline_manifest[key]["sources"]) - set(item["source_ids"]),
                                 spec["retired_sources"])
                self.assertEqual(review["target_sha256"], body_sha)
                self.assertEqual(review["source_reviewed_sha256"], body_sha)
                self.assertEqual(review["source_ids"], item["source_ids"])
                self.assertEqual(review["source_checks"], row["source_checks"])
                self.assertEqual(review["legal_temporal_checks"], row["legal_temporal_checks"])
                self.assertEqual(review["limits"], row["limits"])
                self.assertEqual(review["prior_review_sha256"], digest(prior_review))
                self.assertEqual(review["prior_source_checks"], row["prior_source_checks"])
                self.assertEqual(row["source_bundle_path"], BUNDLE)
                self.assertEqual(review["source_bundle_sha256"], digest((ROOT / BUNDLE).read_bytes()))
                self.assertEqual(row["source_bundle_sha256"], digest((ROOT / BUNDLE).read_bytes()))
                self.assertEqual(review["professional_review"]["required"], True)
                self.assertEqual(review["professional_review"]["obtained"], False)
                self.assertTrue(review["unresolved_questions"])
                self.assertEqual(row["statistics_assessed"], review["statistics_assessed"])

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
        added_since_baseline = set(self.sources) - set(baseline_sources)
        self.assertTrue(NEW_SOURCE_IDS.issubset(added_since_baseline))
        self.assertTrue(NEW_SOURCE_IDS.issubset(source_bundle_ids_added_since(ROOT, BASE)))
        self.assertEqual({source[0] for source in self.bundle["sources"]}, NEW_SOURCE_IDS)

    def test_gout_medication_safety_and_nhi_payment_rules_are_precise(self):
        body = self.items["TW-16-009"]["body"]
        self.assertIn("先停用別嘌醇並儘速就醫", body)
        self.assertIn("不要為了確認是否過敏而自行再吃一次", body)
        self.assertIn("某些亞洲族群（例如漢人、韓國人、泰國人）", body)
        self.assertIn("健保不予支付", body)
        self.assertIn("陰性，且一個月內未開立別嘌醇", body)
        self.assertIn("檢測後一個月內未上傳結果", body)
        self.assertIn("衛福部核准之實驗室開發檢測施行計畫", body)
        self.assertIn("支付資料中的點數不是病人自付金額", body)

        sources = self.sources
        nhi = sources["risk_nhi_hla_12213b_20261122"]
        self.assertIn("每日更新", nhi["title"])
        self.assertIn("陰性後開藥／結果上傳期限", nhi["supports"])
        acr = self.items["TW-16-009"]["source_ids"]
        self.assertIn("ch16_acr_gout_erratum_20261122", acr)

        stats = self.reviews["TW-16-009"]["statistics_assessed"]
        self.assertEqual(len(stats), 1)
        stat = stats[0]
        self.assertEqual(stat["period"], "2009-07至2014-08")
        self.assertEqual(stat["scope"], "臺灣15家醫學中心")
        self.assertEqual((stat["numerator"], stat["denominator"]), (571, 2910))
        self.assertEqual(stat["value"], 19.6)
        self.assertIn("不是服藥後嚴重皮膚不良反應", stat["event_definition"])
        self.assertIn("不是SCAR發生率", stat["limitations"])
        self.assertIn("不是服藥後嚴重過敏的比例", body)

    def test_diabetic_kidney_guidance_dates_scope_and_statistics_are_limited(self):
        body = self.items["TW-16-013"]["body"]
        self.assertIn("第2型糖尿病通常從確診時開始", body)
        self.assertIn("第1型糖尿病通常在確診五年後開始", body)
        self.assertIn("若結果異常，指引建議每3至6個月追蹤", body)
        self.assertIn("清晨第一泡尿", body)
        self.assertIn("溯及自2026年1月1日生效", body)
        self.assertIn("成人預防保健服務報告自2026年起採用2021 CKD-EPI公式", body)
        self.assertIn("不應直接推論所有醫療院所", body)
        self.assertIn("約每5人有1人", body)
        self.assertIn("不能當成個人患病機率", body)
        self.assertIn("（下載需登入）", body)
        self.assertNotIn("/archive/20251203/", body)

        stats = self.reviews["TW-16-013"]["statistics_assessed"]
        self.assertEqual(len(stats), 1)
        stat = stats[0]
        self.assertEqual(stat["period"], "2021至2023（民國110至112年）")
        self.assertEqual(stat["numerator"], None)
        self.assertEqual(stat["denominator"], None)
        self.assertIn("篩檢比例", stat["data_type"])
        self.assertIn("不能代表全臺人口", stat["limitations"])

        source = self.sources["ch16_tsn_ckd_2025_20261122"]
        self.assertEqual(source["url"], "https://www.tsn.org.tw/guide.html")
        self.assertTrue(any("指引下載需登入" in text for text in self.reviews["TW-16-013"]["limits"]))
        self.assertEqual(
            source["published_at"], "2025-12-03"
        )
        stats_source = self.sources["follow_hpa_kidney_stats_2026_20261122"]
        self.assertEqual(stats_source["published_at"], "2026-03-10")

        legal = {entry["law"]: entry for entry in self.reviews["TW-16-013"]["legal_temporal_checks"]}
        hpa = legal["醫事服務機構辦理預防保健服務注意事項（成人預防保健服務eGFR計算公式附表）"]
        amendment = hpa["relevant_provision_amendments"][0]
        self.assertEqual(amendment["promulgated_at"], "2026-02-06")
        self.assertEqual(amendment["effective_at"], "2026-01-01")

    def test_reader_text_has_no_internal_review_process_and_expert_review_stays_pending(self):
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
        self.assertEqual(self.evidence["baseline_main_sha"], BASE)
        self.assertEqual(self.evidence["scope"]["new_core_ids"], [])
        self.assertEqual(self.evidence["scope"]["historical_core_ids"], list(IDS))
        self.assertEqual(self.evidence["scope"]["priority_order"], list(IDS))
        self.assertEqual(self.evidence["new_source_ids"], sorted(NEW_SOURCE_IDS))
        self.assertFalse(self.evidence["publication_ready"])


if __name__ == "__main__":
    unittest.main()

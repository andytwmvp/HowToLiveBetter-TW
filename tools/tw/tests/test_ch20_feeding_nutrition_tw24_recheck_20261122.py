"""第20章餵養／營養首次發布及第24章慢箋歷史再審契約。"""
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

BASE = "968afd839664c869bd7c5834717ab8a0c6a5dbdd"
DATE = "2026-11-22"
DUE = "2027-02-22"
REGISTER = "localization/retroactive-review-register-20261019.json"
BUNDLE = "localization/tw-edition/sources/ch20-feeding-nutrition-tw24-prescription-recheck-20261122.json"
STAGE = "localization/ch20-feeding-nutrition-tw24-prescription-recheck-20261122.json"
NEW_IDS = ("TW-20-004", "TW-20-012", "TW-20-014", "TW-20-016")
RECHECK_ID = "TW-24-014"
SPECS = {
    "TW-20-004": {
        "path": "locales/zh-TW/book/ch20/TW-20-004.md",
        "sources": [
            "tw20_hpa_feeding_position_20250828", "tw20_hpa_newborn_feeding",
            "tw20_hpa_complementary_food_20261122", "tw20_hpa_formula_feeding_20261122",
            "tw20_hpa_formula_preparation",
        ],
        "draft_sha256": "3bb2d18ca86cc4aba3e934e89221469a92f1a7c416f246335be0ca7f663b2b31",
    },
    "TW-20-012": {
        "path": "locales/zh-TW/book/ch20/TW-20-012.md",
        "sources": [
            "tw20_hpa_complementary_food_20261122", "tw20_leap_rct_2015",
            "tw20_niaid_peanut_texture_2017", "ch13_ana_taaaci_2024",
        ],
        "draft_sha256": "2235f8f492419d0e5d159039154b3ec64b2c2ee9d4696cd466ddd433774e0b71",
    },
    "TW-20-014": {
        "path": "locales/zh-TW/book/ch20/TW-20-014.md",
        "sources": [
            "tw20_hpa_infant_b12_20261122", "tw20_hpa_maternal_b12_20261122",
            "tw20_ods_b12_consumer_20261122", "tw20_hpa_formula_feeding_20261122",
        ],
        "draft_sha256": "6cfffd505ff5394fa42621c980423cc74603e7716761efb7c45738bcf5d9cada",
    },
    "TW-20-016": {
        "path": "locales/zh-TW/book/ch20/TW-20-016.md",
        "sources": [
            "tw20_hpa_dri_vitd8_20261122", "tw20_tpa_vitd_education_20250924",
            "tw20_hpa_infant_nutrition_20261122", "tw20_taiwan_infant_vitd_2020",
        ],
        "draft_sha256": "d3215b63b89a2c328b06a033f485929095fa089d5e9885651cb483afc52df448",
    },
}
NEW_SOURCE_IDS = {
    "tw20_hpa_feeding_position_20250828", "tw20_hpa_complementary_food_20261122",
    "tw20_hpa_formula_feeding_20261122", "tw20_leap_rct_2015",
    "tw20_niaid_peanut_texture_2017", "tw20_hpa_infant_b12_20261122",
    "tw20_hpa_maternal_b12_20261122", "tw20_ods_b12_consumer_20261122",
    "tw20_hpa_dri_vitd8_20261122", "tw20_tpa_vitd_education_20250924",
    "tw20_hpa_infant_nutrition_20261122", "tw20_taiwan_infant_vitd_2020",
    "tw24_nhi_medical_rules_20261122", "tw24_nhi_chronic_rx_20261122",
    "tw24_nhi_app_locator_20261122", "tw24_telemedicine_rules_20261122",
}


def read(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def git_bytes(revision, path):
    result = subprocess.run(
        ["git", "show", f"{revision}:{path}"], cwd=ROOT, capture_output=True
    )
    return result.stdout if result.returncode == 0 else None


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


class Chapter20FeedingNutritionAndCh24RecheckTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.runtime = validate_runtime()
        cls.items = {row["id"]: row for row in cls.runtime["items"]}
        cls.sources = {row["id"]: row for row in cls.runtime["sources"]}
        cls.manifest = {row["id"]: row for row in read("localization/manifest.json")["entries"]}
        cls.reviews = {
            key: read(f"localization/reviews/{key}.json")
            for key in (*NEW_IDS, RECHECK_ID)
        }
        cls.bodies = {key: (ROOT / spec["path"]).read_text(encoding="utf-8") for key, spec in SPECS.items()}
        cls.register = read(REGISTER)
        cls.rows = cls.register["substantive_rechecks"]
        cls.batch_recheck = next(
            row for row in reversed(cls.rows)
            if row["id"] == RECHECK_ID and row["prior_revision"] == BASE
        )
        cls.bundle = read(BUNDLE)
        cls.stage = read(STAGE)

    def test_first_publication_preserves_draft_provenance_and_ids(self):
        baseline_manifest = {
            row["id"]: row
            for row in json.loads(git_bytes(BASE, "localization/manifest.json"))["entries"]
        }
        baseline_runtime = json.loads(git_bytes(BASE, "localization/tw-edition/runtime.json"))
        baseline_item_ids = [row["id"] for row in baseline_runtime["items"]]
        current_item_ids = [row["id"] for row in self.runtime["items"]]
        self.assertEqual(
            [key for key in current_item_ids if key in set(baseline_item_ids)],
            baseline_item_ids,
        )
        for key, spec in SPECS.items():
            old = baseline_manifest[key]
            self.assertEqual((old["status"], old["target_path"], old["sources"]), ("pending", None, []))
            self.assertIsNone(git_bytes(BASE, spec["path"]))
            entry, item, review = self.manifest[key], self.items[key], self.reviews[key]
            self.assertEqual((entry["status"], entry["target_path"], entry["verified_at"]), ("verified", spec["path"], DATE))
            self.assertEqual(entry["treatment"], "taiwan_independent_rewrite")
            self.assertEqual((entry["upstream_commit"], entry["upstream_text_sha256"]), (old["upstream_commit"], old["upstream_text_sha256"]))
            self.assertEqual((entry["sources"], item["source_ids"], review["source_ids"]), (spec["sources"],) * 3)
            self.assertEqual(review["prior_chapter_draft_sha256"], spec["draft_sha256"])
            self.assertEqual(review["prior_manifest_entry_sha256"], digest(json.dumps(old, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()))
        baseline_register = json.loads(git_bytes(BASE, REGISTER))
        prior_rows = baseline_register["substantive_rechecks"]
        self.assertEqual(self.rows[:len(prior_rows)], prior_rows)
        later_rows = self.rows[len(prior_rows):]
        for key in baseline_item_ids:
            baseline = next(row for row in baseline_runtime["items"] if row["id"] == key)
            current = self.items[key]
            if current != baseline:
                current_sha = digest(current["body"].encode())
                matching_rechecks = [
                    row for row in later_rows
                    if row["id"] == key and row["after_sha256"] == current_sha
                ]
                self.assertEqual(
                    len(matching_rechecks), 1,
                    f"既有正式條目有差異，但基線後沒有唯一對應的實質再審：{key}",
                )

    def test_markdown_runtime_review_source_urls_and_hashes_match(self):
        for key, spec in SPECS.items():
            body = self.bodies[key]
            raw = body.encode("utf-8")
            body_sha = digest(raw)
            item, entry, review = self.items[key], self.manifest[key], self.reviews[key]
            self.assertEqual((item["body"], item["target_path"], item["title"]), (body, spec["path"], re.search(r"^# (.+)$", body, re.MULTILINE).group(1)))
            self.assertEqual(item["review_status"], "source_checked")
            self.assertEqual((item["reviewed_at"], item["review_due_at"]), (DATE, DUE))
            self.assertEqual((review["target_sha256"], review["source_reviewed_sha256"], review["after_sha256"]), (body_sha, body_sha, body_sha))
            self.assertIsNone(review["before_sha256"])
            self.assertEqual(review["source_bundle_path"], BUNDLE)
            self.assertEqual(review["source_bundle_sha256"], digest((ROOT / BUNDLE).read_bytes()))
            self.assertEqual(review["source_ids"], spec["sources"])
            self.assertEqual(review["prior_structured_draft_sha256"], None)
            self.assertTrue(review["professional_review"]["required"])
            self.assertFalse(review["professional_review"]["obtained"])
            self.assertTrue(review["professional_review"]["scope"])
            self.assertTrue(review["unresolved_questions"])
            self.assertEqual({row["source_id"] for row in review["source_checks"]}, set(spec["sources"]))
            body_urls = set(re.findall(r"\]\((https://[^)]+)\)", body))
            source_urls = {self.sources[sid]["url"] for sid in spec["sources"]}
            self.assertEqual(body_urls, source_urls, key)
            self.assertNotRegex(body, r"(批次摘要|AI協助|本次.{0,12}(?:審查|再審|核對)|CI\s*(?:成功|通過)|PR\s*#\d+|待專業審閱|fork管理|本輪|本批)")

    def test_topic_fidelity_frequency_and_statistical_limits_are_explicit(self):
        feeding = self.bodies["TW-20-004"]
        self.assertIn("母乳或嬰兒配方奶都是合適選擇", feeding)
        self.assertIn("不代表要斷奶", feeding)
        self.assertIn("未找到能以一致定義和適當母群分母", feeding)
        self.assertEqual(self.reviews["TW-20-004"]["statistics_assessed"], [])

        peanut = self.bodies["TW-20-012"]
        self.assertIn("不是台灣嬰兒花生過敏盛行率", peanut)
        self.assertIn("不能保證個別寶寶不會過敏", peanut)
        self.assertIn("https://www.niaid.nih.gov/sites/default/files/addendum-peanut-allergy-prevention-guidelines.pdf", peanut)
        stat = self.reviews["TW-20-012"]["statistics_assessed"][0]
        self.assertEqual((stat["denominator"], stat["numerator"]), (530, None))
        self.assertEqual(stat["reported_values"], {"花生迴避組": 13.7, "花生攝取組": 1.9})
        self.assertIn("不反推人數", stat["limitations"][1])
        self.assertIn("英國", stat["limitations"][2])
        self.assertIn("不反推人數", self.items["TW-20-012"]["limits"])
        self.assertNotIn("專業人員審閱", self.items["TW-20-012"]["limits"])

        b12 = self.bodies["TW-20-014"]
        self.assertIn("一般植物性食品除非經營養強化", b12)
        self.assertIn("一般豆漿或植物飲品不等同嬰兒配方奶", b12)
        self.assertIn("未找到可代表台灣全國", self.reviews["TW-20-014"]["frequency_assessment"])
        self.assertEqual(self.reviews["TW-20-014"]["statistics_assessed"], [])

        vitamin_d = self.bodies["TW-20-016"]
        self.assertIn("這是總攝取的參考值", vitamin_d)
        self.assertIn("這是專業學會建議，不是台灣政府強制規定", vitamin_d)
        self.assertIn("兩種門檻不可混為一談", vitamin_d)
        vitd_stat = self.reviews["TW-20-016"]["statistics_assessed"][0]
        self.assertEqual((vitd_stat["numerator"], vitd_stat["denominator"], vitd_stat["unit"]), (212, 481, "人；44.1%"))
        self.assertEqual(vitd_stat["period"], "2012-10至2014-01")
        self.assertIn("北臺灣三家醫院", vitd_stat["scope"])
        self.assertTrue(any("不能當作全台代表性盛行率" in x for x in vitd_stat["limitations"]))

    def test_tw24_recheck_is_append_only_and_validates_the_full_hash_edge(self):
        baseline = json.loads(git_bytes(BASE, REGISTER))
        prefix = baseline["substantive_rechecks"]
        self.assertEqual(self.rows[:len(prefix)], prefix)
        appended_batch_rows = [
            row for row in self.rows[len(prefix):]
            if row["id"] == RECHECK_ID and row["prior_revision"] == BASE
        ]
        self.assertEqual(appended_batch_rows, [self.batch_recheck])
        baseline_cleanups = baseline.get("reader_copy_cleanups", [])
        current_cleanups = self.register.get("reader_copy_cleanups", [])
        self.assertEqual(current_cleanups[:len(baseline_cleanups)], baseline_cleanups)
        row = self.batch_recheck
        review = self.reviews[RECHECK_ID]
        item = self.items[RECHECK_ID]
        old_runtime = json.loads(git_bytes(BASE, "localization/tw-edition/runtime.json"))
        old_item = next(entry for entry in old_runtime["items"] if entry["id"] == RECHECK_ID)
        old_review = git_bytes(BASE, f"localization/reviews/{RECHECK_ID}.json")
        self.assertEqual(row["before_sha256"], digest(old_item["body"].encode()))
        self.assertEqual(row["prior_review_sha256"], digest(old_review))
        self.assertEqual(row["after_sha256"], digest(item["body"].encode()))
        cleanup = audit._reader_copy_cleanup_for(ROOT, RECHECK_ID, row["after_sha256"])
        if cleanup:
            appended_cleanups = current_cleanups[len(baseline_cleanups):]
            self.assertEqual(
                {entry["id"] for entry in appended_cleanups},
                {"TW-20-012", RECHECK_ID},
            )
            self.assertEqual(len(appended_cleanups), 2)
            self.assertIn(cleanup, appended_cleanups)
            cleanup_prior_review = git_bytes(
                cleanup["prior_revision"], f"localization/reviews/{RECHECK_ID}.json"
            )
            self.assertEqual(row["review_sha256"], cleanup["prior_review_sha256"])
            self.assertEqual(row["review_sha256"], digest(cleanup_prior_review))
            audit.validate_reader_copy_cleanup_history(ROOT, cleanup, item)
            self.assertEqual(
                review["reader_copy_cleanup"],
                {key: cleanup[key] for key in (
                    "transform", "before_sha256", "after_sha256",
                    "before_reader_sha256", "after_reader_sha256",
                )},
            )
        else:
            self.assertEqual(
                row["review_sha256"],
                digest((ROOT / f"localization/reviews/{RECHECK_ID}.json").read_bytes()),
            )
        self.assertEqual(row["source_checks"], review["source_checks"])
        self.assertEqual(row["legal_temporal_checks"], review["legal_temporal_checks"])
        self.assertEqual(row["limits"], review["limits"])
        self.assertEqual(item["source_ids"], review["source_ids"])
        self.assertEqual(review["prior_review_sha256"], digest(old_review))
        prior_review_after_recheck = (json.loads(cleanup_prior_review)
                                      if cleanup else review)
        self.assertEqual(
            prior_review_after_recheck["reader_copy_cleanup"],
            json.loads(old_review)["reader_copy_cleanup"],
        )
        self.assertEqual(review["source_reviewed_sha256"], digest(item["body"].encode()))
        self.assertEqual(review["review_due_at"], DUE)
        current_runtime = validate_runtime()
        self.assertEqual(
            current_runtime["sources"][:len(old_runtime["sources"])],
            old_runtime["sources"],
            "慢箋再審不能重排或改寫既有 runtime 來源",
        )
        for retired in row["retired_sources"]:
            old_source = next(source for source in old_runtime["sources"] if source["id"] == retired["id"])
            new_source = self.sources[retired["id"]]
            self.assertEqual(new_source, old_source)
            self.assertEqual(retired["prior_source_sha256"], digest(json.dumps(old_source, ensure_ascii=False, sort_keys=True).encode()))
            self.assertTrue(retired["replacement_ids"])
        audit.validate_recheck_history(ROOT, row, item)
        content = (ROOT / "locales/zh-TW/book/ch24/TW-24-014.md").read_text(encoding="utf-8")
        self.assertIn("不限原院所所在縣市", content)
        self.assertIn("每次最多三十日", content)
        self.assertIn("前十日內", content)
        self.assertIn("2024年6月20日修正", content)
        self.assertIn("2024-08-01", " ".join(check["basis"] for law in review["legal_temporal_checks"] for check in law["relevant_provision_amendments"]))
        self.assertEqual(content.count("2024年1月22日修正"), 1)

    def test_runtime_source_append_only_bundle_coverage_and_stage_counts(self):
        baseline_runtime = json.loads(git_bytes(BASE, "localization/tw-edition/runtime.json"))
        self.assertEqual(
            self.runtime["sources"][:len(baseline_runtime["sources"])],
            baseline_runtime["sources"],
        )
        self.assertTrue(NEW_SOURCE_IDS.issubset(set(self.sources) - {row["id"] for row in baseline_runtime["sources"]}))
        self.assertEqual({row[0] for row in self.bundle["sources"]}, NEW_SOURCE_IDS)
        self.assertTrue(NEW_SOURCE_IDS.issubset(source_bundle_ids_added_since(ROOT, BASE)))
        bundled = {row[0]: row for row in self.bundle["sources"]}
        for sid in NEW_SOURCE_IDS:
            source = self.sources[sid]
            self.assertEqual(bundled[sid], [source[k] for k in ("id", "title", "url", "supports")])

        chapter = (ROOT / "locales/zh-TW/book/ch20/README.md").read_text(encoding="utf-8")
        chapter_ids = [int(value) for value in re.findall(r"TW-20-(\d{3})\.md", chapter)]
        formal_ids = sorted(
            int(row["id"].rsplit("-", 1)[1]) for row in self.runtime["items"]
            if row["id"].startswith("TW-20-") and row.get("target_path", "").startswith("locales/zh-TW/book/ch20/")
        )
        self.assertEqual(chapter_ids, formal_ids)
        self.assertTrue({4, 12, 14, 16}.issubset(chapter_ids))

        coverage = read("localization/tw-edition/coverage.json")
        self.assertEqual(coverage, audit_drafts())
        publication = publication_report(ROOT)
        self.assertEqual(coverage["publication_completed_entries"], publication["publication_completed_entries"])
        self.assertFalse(publication["publication_ready"])
        self.assertFalse(coverage["publication_ready"])
        self.assertEqual(self.stage["baseline_main_sha"], BASE)
        self.assertEqual(self.stage["counts_before"]["publication_ready"], False)
        baseline_runtime = json.loads(git_bytes(BASE, "localization/tw-edition/runtime.json"))
        baseline_coverage = json.loads(git_bytes(BASE, "localization/tw-edition/coverage.json"))
        baseline_register = json.loads(git_bytes(BASE, REGISTER))
        before = self.stage["counts_before"]
        after = self.stage["counts_after"]
        self.assertEqual(before["core_reviewed_entries"], baseline_coverage["publication_completed_entries"])
        self.assertEqual(after["core_reviewed_entries"], before["core_reviewed_entries"] + len(NEW_IDS))
        self.assertGreaterEqual(publication["publication_completed_entries"], after["core_reviewed_entries"])
        self.assertEqual(before["runtime_items"], len(baseline_runtime["items"]))
        self.assertEqual(after["runtime_items"], before["runtime_items"] + len(NEW_IDS))
        self.assertEqual(before["runtime_sources"], len(baseline_runtime["sources"]))
        self.assertEqual(after["runtime_sources"], before["runtime_sources"] + len(NEW_SOURCE_IDS))
        self.assertEqual(
            after["substantive_rechecks"],
            len(baseline_register["substantive_rechecks"]) + 1,
        )
        self.assertEqual(after["source_registry"], before["source_registry"] + len(NEW_SOURCE_IDS))
        self.assertEqual(after["json_files_checked"], before["json_files_checked"] + len(NEW_IDS) + 2)
        self.assertEqual(self.stage["new_source_ids"], sorted(NEW_SOURCE_IDS))
        self.assertFalse(self.stage["publication_ready"])


if __name__ == "__main__":
    unittest.main()

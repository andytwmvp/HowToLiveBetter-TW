"""TW-02-031首次正式發布：日間自然光與壽命研究契約。"""
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
from recheck_history_assertions import assert_chapter_entries_preserved_or_rechecked
from review_contract import publication_report, validate_runtime
from source_bundle_test_support import source_bundle_ids_added_since

BASE = "9c0d0134435edc4a6879e42712ff1c60e004c1df"
DATE = "2026-11-21"
DUE = "2027-02-21"
ITEM_ID = "TW-02-031"
ARTICLE_PATH = "locales/zh-TW/book/ch02/TW-02-031.md"
REVIEW_PATH = "localization/reviews/TW-02-031.json"
BATCH_PATH = "localization/ch02-daylight-health-research-20261121.json"
SOURCE_PATH = "localization/tw-edition/sources/ch02-daylight-health-research-20261121.json"
REGISTER_PATH = "localization/retroactive-review-register-20261019.json"
SOURCE_IDS = {
    "tw02_sunlight_mortality_review_2025",
    "tw02_sunlight_sweden_miss_2016",
    "tw02_daylight_adventist_cohort_2025",
    "tw02_natural_light_circadian_2013",
    "tw02_who_uv_guidance",
    "tw02_cwa_uvi_observation",
    "tw02_cwa_town_forecast_service",
    "tw02_cwa_uvi_forecast_368town",
    "tw02_hpa_heat_safety_2026",
}
STRUCTURED_DRAFT_SHA256 = "4408c4e55b249805a5057cd579c893e5cec52e14029f315ca7e3171049347cc4"


def read(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def git_bytes(revision, path):
    result = subprocess.run(
        ["git", "show", f"{revision}:{path}"], cwd=ROOT, capture_output=True
    )
    return result.stdout if result.returncode == 0 else None


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


class DaylightHealthResearchPublicationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.runtime = validate_runtime()
        cls.items = {row["id"]: row for row in cls.runtime["items"]}
        cls.sources = {row["id"]: row for row in cls.runtime["sources"]}
        cls.manifest = {
            row["id"]: row for row in read("localization/manifest.json")["entries"]
        }
        cls.item = cls.items[ITEM_ID]
        cls.review = read(REVIEW_PATH)
        cls.batch = read(BATCH_PATH)
        cls.batch_item = cls.batch["items"][0]
        cls.bundle = read(SOURCE_PATH)
        cls.coverage = read("localization/tw-edition/coverage.json")
        cls.register = read(REGISTER_PATH)
        cls.article_bytes = (ROOT / ARTICLE_PATH).read_bytes()
        cls.body = cls.article_bytes.decode("utf-8")

    def test_first_publication_preserves_the_structured_draft_and_provenance(self):
        self.assertEqual(self.batch["baseline_main_sha"], BASE)
        self.assertIsNone(git_bytes(BASE, ARTICLE_PATH))
        self.assertIsNone(git_bytes(BASE, REVIEW_PATH))
        baseline_manifest = json.loads(git_bytes(BASE, "localization/manifest.json"))
        baseline_entry = next(row for row in baseline_manifest["entries"] if row["id"] == ITEM_ID)
        self.assertEqual(baseline_entry["status"], "pending")
        self.assertIsNone(baseline_entry["target_path"])
        self.assertEqual(baseline_entry["sources"], [])

        baseline_runtime = json.loads(git_bytes(BASE, "localization/tw-edition/runtime.json"))
        baseline_register = json.loads(git_bytes(BASE, REGISTER_PATH))
        baseline_chapter = json.loads(git_bytes(BASE, "localization/tw-edition/chapters/02.json"))
        current_chapter = read("localization/tw-edition/chapters/02.json")
        baseline_items = {row["id"]: row for row in baseline_runtime["items"]}
        current_items = {row["id"]: row for row in self.runtime["items"]}
        changed = assert_chapter_entries_preserved_or_rechecked(
            self,
            chapter_number=2,
            baseline_entries=baseline_chapter["entries"],
            current_entries=current_chapter["entries"],
            baseline_items=baseline_items,
            current_items=current_items,
            baseline_rechecks=baseline_register["substantive_rechecks"],
            current_rechecks=self.register["substantive_rechecks"],
        )
        chapter_runtime_ids = {
            f"TW-02-{row[0]:03d}" for row in current_chapter["entries"]
        }
        new_runtime_ids = (set(current_items) - set(baseline_items)) & chapter_runtime_ids
        self.assertIn(ITEM_ID, changed)
        self.assertTrue(new_runtime_ids <= changed)
        current_existing_ids = [
            row["id"] for row in self.runtime["items"]
            if row["id"] in baseline_items
        ]
        self.assertEqual(
            current_existing_ids,
            [row["id"] for row in baseline_runtime["items"]],
        )
        old_chapter = next(row for row in baseline_chapter["entries"] if row[0] == 31)
        self.assertEqual(
            sha(json.dumps(old_chapter, ensure_ascii=False, separators=(",", ":")).encode()),
            STRUCTURED_DRAFT_SHA256,
        )
        self.assertEqual(self.review["prior_structured_draft_sha256"], STRUCTURED_DRAFT_SHA256)
        self.assertEqual(self.batch_item["prior_structured_draft_sha256"], STRUCTURED_DRAFT_SHA256)
        self.assertEqual(self.batch_item["prior_structured_source_refs"], ["sleep", "sunsafety"])

    def test_article_manifest_runtime_review_coverage_and_navigation_match(self):
        entry = self.manifest[ITEM_ID]
        self.assertEqual((entry["status"], entry["treatment"], entry["verified_at"]),
                         ("verified", "taiwan_independent_rewrite", DATE))
        self.assertEqual(entry["target_path"], ARTICLE_PATH)
        self.assertEqual(entry["sources"], self.item["source_ids"])
        self.assertEqual(self.item["body"], self.body)
        self.assertEqual(self.item["target_path"], ARTICLE_PATH)
        self.assertIsInstance(self.item["limits"], str)
        self.assertEqual((self.item["reviewed_at"], self.item["review_due_at"]), (DATE, DUE))
        self.assertEqual((self.review["reviewed_at"], self.review["review_due_at"]), (DATE, DUE))
        self.assertEqual(self.review["target_sha256"], sha(self.article_bytes))
        self.assertEqual(self.review["source_reviewed_sha256"], sha(self.article_bytes))
        self.assertEqual(self.batch_item["after_sha256"], sha(self.article_bytes))
        self.assertEqual(self.item["source_ids"], self.review["source_ids"])
        self.assertEqual(self.batch_item["source_ids"], self.item["source_ids"])
        self.assertEqual(self.batch_item["review_sha256"], sha((ROOT / REVIEW_PATH).read_bytes()))
        self.assertEqual(self.batch_item["source_bundle_sha256"], sha((ROOT / SOURCE_PATH).read_bytes()))
        self.assertEqual(self.coverage, audit_drafts())
        self.assertEqual(self.coverage["publication_completed_entries"], publication_report()["publication_completed_entries"])
        self.assertGreaterEqual(
            self.coverage["publication_completed_entries"],
            self.batch["counts_after"]["publication_completed_entries"],
        )
        self.assertFalse(any(row.startswith(f"{ITEM_ID}:") for row in self.coverage["publication_blockers"]))
        chapter_readme = (ROOT / "locales/zh-TW/book/ch02/README.md").read_text(encoding="utf-8")
        self.assertEqual(chapter_readme.count("TW-02-031.md"), 1)
        self.assertIn("TW-02-030.md", chapter_readme)
        self.assertIn("TW-02-032.md", chapter_readme)

    def test_source_bundle_runtime_article_and_review_urls_are_exact(self):
        self.assertEqual(self.bundle["checked_at"], DATE)
        bundled = {row[0]: row for row in self.bundle["sources"]}
        checks = {row["source_id"]: row for row in self.review["source_checks"]}
        self.assertEqual(set(bundled), SOURCE_IDS)
        self.assertEqual(set(checks), SOURCE_IDS)
        self.assertEqual(set(self.item["source_ids"]), SOURCE_IDS)
        self.assertEqual(set(self.batch["new_source_ids"]), SOURCE_IDS)
        article_urls = set(re.findall(r"\]\((https://[^)]+)\)", self.body))
        self.assertEqual(article_urls, {self.sources[key]["url"] for key in SOURCE_IDS})

        baseline_runtime = json.loads(git_bytes(BASE, "localization/tw-edition/runtime.json"))
        baseline_source_ids = {row["id"] for row in baseline_runtime["sources"]}
        for old_source in baseline_runtime["sources"]:
            self.assertEqual(self.sources[old_source["id"]], old_source)
        self.assertTrue(SOURCE_IDS.isdisjoint(baseline_source_ids))
        added_since_baseline = set(self.sources) - baseline_source_ids
        self.assertTrue(SOURCE_IDS.issubset(added_since_baseline))
        self.assertEqual(added_since_baseline, source_bundle_ids_added_since(ROOT, BASE))

        for source_id in SOURCE_IDS:
            with self.subTest(source_id=source_id):
                source = self.sources[source_id]
                check = checks[source_id]
                self.assertEqual(check["url"], source["url"])
                self.assertEqual(check["title"], source["title"])
                self.assertEqual(check["accessed_at"], DATE)
                self.assertTrue(check["claim"])
                self.assertTrue(check["supporting_passage"])
                self.assertEqual(
                    bundled[source_id],
                    [source[key] for key in ("id", "title", "url", "supports")],
                )
                self.assertLessEqual(source["accessed_at"], DATE)

    def test_statistics_keep_population_scope_event_and_estimate_types_distinct(self):
        statistics = {row["topic"]: row for row in self.review["statistics_assessed"]}
        review = statistics["日照與死亡率的2025年系統性回顧"]
        self.assertEqual(review["value"], {"eligible_articles": 73, "included_in_narrative_synthesis": 55})
        sweden = statistics["瑞典南部女性日照習慣與預期壽命模型差異"]
        self.assertEqual(sweden["value"]["life_expectancy_difference_years_range"], [0.6, 2.1])
        self.assertIn("29,518", sweden["population"])
        self.assertIn("2,545", sweden["numerator"])
        ahs = statistics["北美AHS-2暖季戶外日照時間與死亡率"]
        self.assertEqual(ahs["value"]["all_cause_HR"], 0.90)
        self.assertEqual(ahs["value"]["all_cause_95_CI"], [0.86, 0.93])
        self.assertEqual(ahs["population"], "83,205名基督復臨安息日會健康研究AHS-2參與者")
        self.assertIn("11,515人死亡", ahs["numerator"])
        self.assertIn("非絕對死亡機率", ahs["unit"])
        circadian = statistics["自然光露營研究的生理時鐘變化"]
        self.assertEqual(circadian["value"]["circadian_marker_advance_approx_hours"], 2)
        self.assertIn("8名成人", circadian["population"])

        for stat in self.review["statistics_assessed"]:
            for field in (
                "value", "unit", "period", "geographic_scope", "population", "numerator",
                "denominator", "denominator_definition", "event_definition", "data_type",
                "limitations", "source_ids", "accessed_at",
            ):
                self.assertTrue(stat.get(field), (stat["topic"], field))
            self.assertLessEqual(stat["accessed_at"], DATE)
            self.assertTrue(set(stat["source_ids"]).issubset(SOURCE_IDS))

    def test_reader_text_preserves_the_question_without_prescribing_sun_exposure(self):
        fidelity = self.review["topic_fidelity_review"]
        self.assertEqual(
            fidelity["decision"],
            "retain_original_daylight_and_longevity_research_with_taiwan_safety_context",
        )
        self.assertIn("壽命", fidelity["original_question"])
        self.assertIn("不把海外結果或露營研究轉成台灣日曬時數處方", self.review["topic_fidelity_assessment"])
        self.assertIn("每天曬幾分鐘", self.body)
        self.assertIn("不能直接換算成台灣個人風險", self.body)
        self.assertIn("台灣目前缺少", self.body)
        self.assertIn("鄉鎮預報", self.body)
        self.assertIn("紫外線指數達3以上", self.body)
        self.assertTrue(self.review["professional_review"]["required"])
        self.assertFalse(self.review["professional_review"]["obtained"])
        self.assertEqual(self.batch_item["status"], "ai_source_checked_professional_pending")
        self.assertNotRegex(
            self.body,
            r"(批次摘要|AI協助|本次.{0,12}(?:審查|再審|核對)|CI\s*(?:成功|通過)|PR\s*#\d+|待專業審閱|fork管理)",
        )

    def test_first_publication_does_not_create_a_historical_recheck(self):
        baseline_register = json.loads(git_bytes(BASE, REGISTER_PATH))
        self.assertEqual(self.register, baseline_register)
        self.assertFalse(any(
            row["id"] == ITEM_ID and row["reviewed_at"] == DATE
            for row in self.register["substantive_rechecks"]
        ))

    def test_batch_counts_reflect_only_one_core_publication_and_nine_sources(self):
        before = self.batch["counts_before"]
        after = self.batch["counts_after"]
        baseline_coverage = json.loads(git_bytes(BASE, "localization/tw-edition/coverage.json"))
        baseline_runtime = json.loads(git_bytes(BASE, "localization/tw-edition/runtime.json"))
        baseline_manifest = json.loads(git_bytes(BASE, "localization/manifest.json"))
        self.assertEqual(before["manifest_entries"], len(baseline_manifest["entries"]))
        self.assertEqual(before["verified_core_entries"], baseline_coverage["core_reviewed_entries"])
        self.assertEqual(before["runtime_items"], len(baseline_runtime["items"]))
        self.assertEqual(before["runtime_sources"], len(baseline_runtime["sources"]))
        self.assertEqual(before["source_registry"], baseline_coverage["registry_sources"])
        self.assertEqual(before["coverage_json_files"], baseline_coverage["json_files_checked"])
        self.assertEqual(before["publication_ready"], baseline_coverage["publication_ready"])
        self.assertEqual(after["verified_core_entries"], before["verified_core_entries"] + 1)
        self.assertEqual(after["runtime_items"], before["runtime_items"] + 1)
        self.assertEqual(after["runtime_sources"], before["runtime_sources"] + len(SOURCE_IDS))
        self.assertEqual(after["source_registry"], before["source_registry"] + len(SOURCE_IDS))
        self.assertEqual(after["review_rechecks"], before["review_rechecks"])
        self.assertEqual(after["coverage_json_files"], before["coverage_json_files"] + 3)
        self.assertEqual(after["unresolved_source_ids"], before["unresolved_source_ids"] - 1)
        self.assertEqual(after["unresolved_reference_occurrences"], before["unresolved_reference_occurrences"] - 2)
        self.assertEqual(after["publication_completed_entries"], before["publication_completed_entries"] + 1)
        self.assertFalse(after["publication_ready"])
        self.assertGreaterEqual(self.coverage["core_reviewed_entries"], after["verified_core_entries"])
        self.assertGreaterEqual(len(self.runtime["items"]), after["runtime_items"])
        self.assertGreaterEqual(len(self.runtime["sources"]), after["runtime_sources"])
        self.assertGreaterEqual(self.coverage["registry_sources"], after["source_registry"])
        self.assertGreaterEqual(len(self.register["substantive_rechecks"]), after["review_rechecks"])
        self.assertGreaterEqual(self.coverage["json_files_checked"], after["coverage_json_files"])
        self.assertGreaterEqual(
            self.coverage["publication_completed_entries"], after["publication_completed_entries"]
        )
        self.assertEqual(len(self.manifest), after["manifest_entries"])


if __name__ == "__main__":
    unittest.main()

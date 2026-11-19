"""TW-02-044首次正式發布：養狗、遛狗活動量與長壽研究契約。"""
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

BASE = "0206632bb4c691238d663224c970bbb58754e4f7"
DATE = "2026-11-19"
DUE = "2027-02-19"
ITEM_ID = "TW-02-044"
ARTICLE_PATH = "locales/zh-TW/book/ch02/TW-02-044.md"
REVIEW_PATH = "localization/reviews/TW-02-044.json"
BATCH_PATH = "localization/ch02-dog-walking-longevity-20261119.json"
SOURCE_PATH = "localization/tw-edition/sources/ch02-dog-walking-longevity-20261119.json"
REGISTER_PATH = "localization/retroactive-review-register-20261019.json"
SOURCE_IDS = {
    "tw02_dog_mortality_meta_2019",
    "tw02_dog_mortality_reanalysis_2020",
    "tw02_dog_mortality_england_cohort_2018",
    "tw02_dog_mortality_sweden_cohort_2017",
    "tw02_dog_mortality_australia_hilda_2024",
    "tw02_dog_disability_japan_2022",
    "tw02_dog_disability_japan_correction_2024",
    "tw02_hpa_activity_2025",
    "tw02_moa_dog_care",
    "tw02_moa_shelter_adoption_manual",
}
STRUCTURED_DRAFT_SHA256 = "857c101ea7373563a96887f24075e042995a6f73d6e7268a30a48a7b679a6542"


def read(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def git_bytes(revision, path):
    result = subprocess.run(
        ["git", "show", f"{revision}:{path}"], cwd=ROOT, capture_output=True
    )
    return result.stdout if result.returncode == 0 else None


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


class DogOwnershipLongevityPublicationTests(unittest.TestCase):
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

    def test_first_publication_preserves_the_original_draft_and_provenance(self):
        self.assertEqual(self.batch["baseline_main_sha"], BASE)
        self.assertIsNone(git_bytes(BASE, ARTICLE_PATH))
        self.assertIsNone(git_bytes(BASE, REVIEW_PATH))
        baseline_manifest = json.loads(git_bytes(BASE, "localization/manifest.json"))
        baseline_entry = next(row for row in baseline_manifest["entries"] if row["id"] == ITEM_ID)
        self.assertEqual(baseline_entry["status"], "pending")
        self.assertIsNone(baseline_entry["target_path"])
        self.assertEqual(baseline_entry["sources"], [])

        baseline_runtime = json.loads(git_bytes(BASE, "localization/tw-edition/runtime.json"))
        baseline_register = json.loads(
            git_bytes(BASE, REGISTER_PATH)
        )
        baseline_chapter = json.loads(
            git_bytes(BASE, "localization/tw-edition/chapters/02.json")
        )
        current_chapter = read("localization/tw-edition/chapters/02.json")
        baseline_items = {row["id"]: row for row in baseline_runtime["items"]}
        current_items = {row["id"]: row for row in self.runtime["items"]}
        assert_chapter_entries_preserved_or_rechecked(
            self,
            chapter_number=2,
            baseline_entries=baseline_chapter["entries"],
            current_entries=current_chapter["entries"],
            baseline_items=baseline_items,
            current_items=current_items,
            baseline_rechecks=baseline_register["substantive_rechecks"],
            current_rechecks=self.register["substantive_rechecks"],
        )
        self.assertEqual(
            [row["id"] for row in self.runtime["items"][:len(baseline_runtime["items"])]],
            [row["id"] for row in baseline_runtime["items"]],
        )
        self.assertEqual(
            [row["id"] for row in self.runtime["sources"][:len(baseline_runtime["sources"])]],
            [row["id"] for row in baseline_runtime["sources"]],
        )

        baseline_chapter = json.loads(git_bytes(BASE, "localization/tw-edition/chapters/02.json"))
        baseline_row = next(row for row in baseline_chapter["entries"] if row[0] == 44)
        self.assertEqual(
            sha(json.dumps(baseline_row, ensure_ascii=False, separators=(",", ":")).encode()),
            STRUCTURED_DRAFT_SHA256,
        )
        self.assertEqual(self.review["prior_structured_draft_sha256"], STRUCTURED_DRAFT_SHA256)
        self.assertIsNone(self.review["prior_structured_draft_review"])
        self.assertIsNone(self.batch_item["prior_chapter_draft_sha256"])

    def test_article_manifest_runtime_review_and_navigation_match(self):
        entry = self.manifest[ITEM_ID]
        self.assertEqual(entry["status"], "verified")
        self.assertEqual(entry["treatment"], "taiwan_independent_rewrite")
        self.assertEqual(entry["verified_at"], DATE)
        self.assertEqual(entry["target_path"], ARTICLE_PATH)
        self.assertEqual(entry["sources"], self.item["source_ids"])
        self.assertEqual(self.item["body"], self.body)
        self.assertEqual(self.item["target_path"], ARTICLE_PATH)
        self.assertEqual((self.item["reviewed_at"], self.item["review_due_at"]), (DATE, DUE))
        self.assertEqual((self.review["reviewed_at"], self.review["review_due_at"]), (DATE, DUE))
        self.assertEqual(self.review["target_sha256"], sha(self.article_bytes))
        self.assertEqual(self.review["source_reviewed_sha256"], sha(self.article_bytes))
        self.assertEqual(self.batch_item["after_sha256"], sha(self.article_bytes))
        self.assertEqual(self.item["source_ids"], self.review["source_ids"])
        self.assertEqual(self.batch_item["source_ids"], self.item["source_ids"])
        self.assertEqual(self.batch_item["review_sha256"], sha((ROOT / REVIEW_PATH).read_bytes()))
        self.assertEqual(
            self.batch_item["source_bundle_sha256"], sha((ROOT / SOURCE_PATH).read_bytes())
        )
        self.assertEqual(self.coverage, audit_drafts())
        self.assertFalse(self.coverage["publication_ready"])
        self.assertFalse(publication_report()["publication_ready"])
        self.assertFalse(any(row.startswith(f"{ITEM_ID}:") for row in self.coverage["publication_blockers"]))
        chapter_readme = (ROOT / "locales/zh-TW/book/ch02/README.md").read_text(encoding="utf-8")
        self.assertEqual(chapter_readme.count("TW-02-044.md"), 1)
        self.assertIn("符合強度的遛狗算進活動量", chapter_readme)

    def test_source_bundle_runtime_article_links_and_review_checks_are_exact(self):
        self.assertEqual(self.bundle["checked_at"], DATE)
        bundled = {row[0]: row for row in self.bundle["sources"]}
        checks = {row["source_id"]: row for row in self.review["source_checks"]}
        self.assertEqual(set(bundled), SOURCE_IDS)
        self.assertEqual(set(checks), SOURCE_IDS)
        self.assertEqual(set(self.item["source_ids"]), SOURCE_IDS)
        self.assertEqual(set(self.batch["new_source_ids"]), SOURCE_IDS)
        article_urls = set(re.findall(r"\]\((https://[^)]+)\)", self.body))
        self.assertEqual(article_urls, {self.sources[source_id]["url"] for source_id in SOURCE_IDS})

        baseline_runtime = json.loads(git_bytes(BASE, "localization/tw-edition/runtime.json"))
        baseline_source_ids = {row["id"] for row in baseline_runtime["sources"]}
        for old_source in baseline_runtime["sources"]:
            self.assertEqual(self.sources[old_source["id"]], old_source)
        self.assertTrue(SOURCE_IDS.isdisjoint(baseline_source_ids))
        added_source_ids = set(self.sources) - baseline_source_ids
        self.assertTrue(SOURCE_IDS.issubset(added_source_ids))
        self.assertEqual(added_source_ids, source_bundle_ids_added_since(ROOT, BASE))
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
                    [source[k] for k in ("id", "title", "url", "supports")],
                )
                self.assertLessEqual(source["accessed_at"], DATE)
        hilda = checks["tw02_dog_mortality_australia_hilda_2024"]
        self.assertIn("未養寵物者", hilda["claim"])
        self.assertIn("未養寵物者", hilda["supporting_passage"])

    def test_research_statistics_distinguish_denominators_and_outcomes(self):
        stats = {row["topic"]: row for row in self.review["statistics_assessed"]}
        meta = stats["犬隻飼養與全因死亡的2019年未調整統合估計"]
        self.assertEqual(meta["value"]["RR"], 0.76)
        self.assertEqual(meta["population"], "10項研究合計3,837,005名參與者")
        self.assertIn("530,515項事件", meta["numerator"])
        self.assertIn("未調整混雜因素", meta["limitations"])

        adjusted = stats["犬隻飼養與全因死亡的2020年調整後再分析"]
        self.assertEqual(adjusted["value"]["effect_size"], 0.95)
        self.assertEqual(adjusted["value"]["95_CI"], [0.85, 1.05])
        self.assertIn("未達統計顯著", adjusted["limitations"])

        england = stats["英格蘭世代的犬隻飼養與全因／心血管死亡"]
        self.assertEqual(england["population"], "59,352名16歲以上參與者；679,441人年")
        self.assertIn("8,169人全因死亡", england["numerator"])
        self.assertIn("2,451人", england["numerator"])

        australia = stats["澳洲HILDA世代的犬隻飼養與全因死亡"]
        self.assertEqual(australia["value"]["dog_owner_OR"], 0.77)
        self.assertIn("犬飼主中106人死亡", australia["numerator"])
        self.assertIn("未養寵物者中229人死亡", australia["numerator"])
        self.assertIn("未養任何寵物者", australia["denominator_definition"])
        self.assertIn("6,210", australia["denominator"])
        self.assertIn("15,172", australia["denominator"])
        self.assertIn("缺少死因資料", australia["limitations"])

        japan = stats["日本東京高齡者犬隻飼養與新失能認定"]
        self.assertEqual(japan["value"]["adjusted_OR"], 0.54)
        self.assertEqual(japan["value"]["current_dog_owner_events"], "124/947 (13.1%)")
        self.assertIn("不是死亡", japan["limitations"])
        self.assertIn("研究於2024年更正方法文字及貓模型資料", japan["limitations"])
        self.assertIn("15,735名15至99歲參與者", australia["population"])

        for stat in self.review["statistics_assessed"]:
            for field in (
                "value", "unit", "period", "geographic_scope", "population", "numerator",
                "denominator", "denominator_definition", "event_definition", "data_type",
                "limitations", "source_ids", "accessed_at",
            ):
                self.assertTrue(stat.get(field), (stat["topic"], field))
            self.assertLessEqual(stat["accessed_at"], DATE)
            self.assertTrue(set(stat["source_ids"]).issubset(SOURCE_IDS))

    def test_reader_text_preserves_the_question_without_promising_health_effects(self):
        fidelity = self.review["topic_fidelity_review"]
        self.assertEqual(
            fidelity["decision"], "retain_original_research_question_with_taiwan_action_context"
        )
        self.assertIn("養狗與長壽", fidelity["original_question"])
        self.assertIn("不把觀察關聯寫成延壽承諾", fidelity["reader_content_decision"])
        self.assertIn("95% 信賴區間 0.85 至 1.05", self.body)
        self.assertIn("不一定都符合這個強度", self.body)
        self.assertIn("台灣資料沒有提供可代表全台", self.body)
        self.assertIn("這類台灣資料不足", self.body)
        self.assertIn("15 至 99 歲參與者", self.body)
        self.assertIn("相較於未養任何寵物者", self.body)
        self.assertIn("研究比較組是未養寵物者，不等同所有未養狗的人", self.body)
        self.assertIn("租屋契約或社區規約", self.body)
        self.assertIn("沒有全台通用的每月養狗成本數字", self.body)
        self.assertTrue(self.review["professional_review"]["required"])
        self.assertFalse(self.review["professional_review"]["obtained"])
        self.assertEqual(self.batch["items"][0]["status"], "ai_source_checked_professional_pending")
        self.assertNotRegex(
            self.body,
            r"(批次摘要|AI協助|本次.{0,12}(?:審查|再審|核對)|CI\s*(?:成功|通過)|PR\s*#\d+|待專業審閱|fork管理)",
        )

    def test_first_publication_does_not_create_a_false_historical_recheck(self):
        baseline_register = json.loads(git_bytes(BASE, REGISTER_PATH))
        current_register = self.register
        self.assertEqual(current_register["substantive_rechecks"][:len(baseline_register["substantive_rechecks"])],
                         baseline_register["substantive_rechecks"])
        baseline_without = dict(baseline_register)
        current_without = dict(current_register)
        baseline_without.pop("substantive_rechecks")
        current_without.pop("substantive_rechecks")
        self.assertEqual(current_without, baseline_without)
        self.assertFalse(any(
            row["id"] == ITEM_ID and row["reviewed_at"] == DATE
            for row in current_register["substantive_rechecks"]
        ))

    def test_batch_counts_advance_only_the_verified_core_and_registered_sources(self):
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
        self.assertEqual(after["unresolved_source_ids"], before["unresolved_source_ids"])
        self.assertEqual(after["unresolved_reference_occurrences"], before["unresolved_reference_occurrences"])
        self.assertFalse(after["publication_ready"])
        self.assertGreaterEqual(self.coverage["core_reviewed_entries"], after["verified_core_entries"])
        self.assertGreaterEqual(len(self.runtime["items"]), after["runtime_items"])
        self.assertGreaterEqual(len(self.runtime["sources"]), after["runtime_sources"])
        self.assertGreaterEqual(self.coverage["json_files_checked"], after["coverage_json_files"])


if __name__ == "__main__":
    unittest.main()

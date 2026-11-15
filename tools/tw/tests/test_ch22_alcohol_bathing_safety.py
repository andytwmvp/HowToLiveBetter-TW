"""Taiwan publication and topic-fidelity contract for TW-22-011."""
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
from review_contract import validate_runtime
from source_bundle_test_support import source_bundle_ids_added_since


BASE = "d1f33adf73104701eefaac24a79e875731a9a975"
DATE = "2026-11-15"
DUE = "2027-02-15"
ITEM_ID = "TW-22-011"
ARTICLE = "locales/zh-TW/book/ch22/TW-22-011.md"
REVIEW = f"localization/reviews/{ITEM_ID}.json"
SOURCE_BUNDLE = "localization/tw-edition/sources/ch22-alcohol-bathing-safety-20261115.json"
EVIDENCE = "localization/ch22-alcohol-bathing-topic-fidelity-20261115.json"
REGISTER = "localization/retroactive-review-register-20261019.json"


def read_json(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def git_json(revision, path):
    raw = subprocess.check_output(["git", "show", f"{revision}:{path}"], cwd=ROOT)
    return json.loads(raw)


def sha256(data):
    return hashlib.sha256(data).hexdigest()


class AlcoholBathingSafetyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.runtime = validate_runtime()
        cls.items = {row["id"]: row for row in cls.runtime["items"]}
        cls.sources = {row["id"]: row for row in cls.runtime["sources"]}
        cls.manifest = {
            row["id"]: row for row in read_json("localization/manifest.json")["entries"]
        }
        cls.review = read_json(REVIEW)
        cls.bundle = read_json(SOURCE_BUNDLE)
        cls.batch = read_json(EVIDENCE)
        cls.coverage = read_json("localization/tw-edition/coverage.json")
        cls.article_bytes = (ROOT / ARTICLE).read_bytes()
        cls.body = cls.article_bytes.decode("utf-8")
        cls.digest = sha256(cls.article_bytes)
        cls.item = cls.items[ITEM_ID]
        cls.register = read_json(REGISTER)

    def test_first_publication_hash_and_manifest_contract(self):
        old_manifest = git_json(BASE, "localization/manifest.json")
        old_entry = next(row for row in old_manifest["entries"] if row["id"] == ITEM_ID)
        old_runtime = git_json(BASE, "localization/tw-edition/runtime.json")
        self.assertEqual(old_entry["status"], "pending")
        self.assertIsNone(old_entry["target_path"])
        self.assertEqual(old_entry["sources"], [])
        self.assertNotIn(ITEM_ID, {row["id"] for row in old_runtime["items"]})
        self.assertEqual(self.manifest[ITEM_ID]["status"], "verified")
        self.assertEqual(self.manifest[ITEM_ID]["treatment"], "taiwan_independent_rewrite")
        self.assertEqual(self.manifest[ITEM_ID]["verified_at"], DATE)
        self.assertEqual(self.item["body"], self.body)
        self.assertEqual(self.item["target_path"], ARTICLE)
        self.assertEqual(self.item["source_ids"], self.manifest[ITEM_ID]["sources"])
        self.assertEqual((self.item["reviewed_at"], self.item["review_due_at"]), (DATE, DUE))
        self.assertEqual(self.review["target_sha256"], self.digest)
        self.assertEqual(self.review["source_reviewed_sha256"], self.digest)
        self.assertEqual(self.batch["item"]["after_sha256"], self.digest)
        self.assertIsNone(self.batch["item"]["before_sha256"])
        self.assertIsNone(self.batch["item"]["prior_taiwan_body_sha256"])
        self.assertEqual(self.batch["phase"], "topic_fidelity_and_initial_taiwan_publication")
        self.assertEqual(self.batch["baseline_main_sha"], BASE)

    def test_topic_is_retained_with_taiwan_terms_and_reader_actions(self):
        body = self.body
        self.assertIn("酒後先別泡湯、泡澡或進三溫暖", body)
        self.assertNotIn("桑拿", body)
        self.assertIn("國民健康署提醒避免喝酒後立即泡澡", body)
        self.assertIn("至少間隔2小時再泡湯", body)
        self.assertIn("2026年2月發布", body)
        self.assertIn("同年11月更新", body)
        self.assertIn("不是酒精已完全代謝或每個人都安全的保證", body)
        self.assertIn("沒有一個固定等待時數能保證", body)
        self.assertIn("立即請旁人撥119", body)
        self.assertIn("TW-13-046.md", body)
        self.assertIn("TW-02-036.md", body)
        self.assertIn("泡澡文化、健康研究和一般浴室安全", body)
        self.assertNotRegex(
            body,
            r"(批次摘要|本次.{0,12}(?:審查|再審|核對)|AI協助|PR\s*#|CI\s*(?:成功|通過))",
        )
        self.assertEqual(self.review["topic_fidelity_review"]["decision"],
                         "retain_taiwan_relevant_topic_with_local_guidance_and_bounded_foreign_case_evidence")
        self.assertIn("不以一般防跌內容取代本題", self.review["topic_fidelity_review"]["reader_content_decision"])
        self.assertFalse(self.review["professional_review"]["obtained"])

    def test_foreign_statistics_keep_their_population_and_case_denominators(self):
        body = self.body
        self.assertIn("芬蘭1990至2002年", body)
        self.assertIn("不到每10萬人口2人", body)
        self.assertIn("約一半死者", body)
        self.assertIn("不是每次使用三溫暖的風險", body)
        self.assertIn("東京一項2015至2016年的法醫研究檢視90件", body)
        self.assertIn("其中77件有溺水徵象", body)
        self.assertIn("25件", body)
        self.assertIn("22件", body)
        self.assertIn("沒有浴缸使用人數或泡澡人次作分母", body)
        self.assertIn("無法估算臺灣酒後入浴的個人發生率", body)

        stats = self.review["statistics_assessed"]
        self.assertEqual(len(stats), 2)
        required = {
            "value", "unit", "period", "geographic_scope", "population", "numerator",
            "denominator", "event_definition", "data_type", "limitations", "source_ids",
            "accessed_at",
        }
        for statistic in stats:
            self.assertTrue(required.issubset(statistic))
            self.assertTrue(all(statistic[key] for key in required))
            self.assertEqual(statistic["accessed_at"], DATE)
        finland, tokyo = stats
        self.assertEqual(finland["value"]["annual_deaths_per_100000_population"], "<2")
        self.assertEqual(finland["value"]["sauna_death_cases_under_alcohol_percent"], 50)
        self.assertIn("不是桑拿使用人次", finland["denominator"])
        self.assertEqual(tokyo["value"]["autopsied_bath_related_deaths"], 90)
        self.assertEqual(tokyo["value"]["drowning_cases"], 77)
        self.assertEqual(tokyo["value"]["alcohol_intoxication_factor_cases"], 25)
        self.assertIn("無浴缸使用人數或泡澡人次分母", tokyo["denominator"])
        self.assertIn("不估算臺灣個人發生率", self.review["frequency_assessment"])

    def test_sources_urls_review_and_new_source_bundle_are_synchronized(self):
        known_ids = set(self.sources)
        source_ids = self.item["source_ids"]
        self.assertTrue(set(source_ids).issubset(known_ids))
        self.assertEqual(self.review["source_ids"], source_ids)
        source_checks = {row["source_id"]: row for row in self.review["source_checks"]}
        self.assertEqual(set(source_checks), set(source_ids))
        external_urls = set(re.findall(r"\]\((https://[^)]+)\)", self.body))
        expected_urls = {self.sources[source_id]["url"] for source_id in source_ids}
        self.assertEqual(external_urls, expected_urls)
        for source_id in source_ids:
            self.assertEqual(source_checks[source_id]["url"], self.sources[source_id]["url"])
            self.assertLessEqual(source_checks[source_id]["accessed_at"], DATE)

        old_runtime = git_json(BASE, "localization/tw-edition/runtime.json")
        old_source_ids = {row["id"] for row in old_runtime["sources"]}
        added_source_ids = set(self.sources) - old_source_ids
        self.assertEqual(added_source_ids, source_bundle_ids_added_since(ROOT, BASE))
        expected_added = set(self.batch["new_source_ids"])
        bundle_source_ids = {row[0] for row in self.bundle["sources"]}
        self.assertEqual(bundle_source_ids, expected_added)
        self.assertTrue(expected_added.issubset(added_source_ids))
        self.assertEqual(self.batch["source_ids"], source_ids)
        self.assertEqual(
            self.batch["item"]["source_bundle_sha256"],
            sha256((ROOT / SOURCE_BUNDLE).read_bytes()),
        )
        self.assertEqual(self.batch["item"]["review_sha256"], sha256((ROOT / REVIEW).read_bytes()))

    def test_navigation_and_initial_publication_do_not_create_a_false_recheck(self):
        locale_index = (ROOT / "locales/zh-TW/README.md").read_text(encoding="utf-8")
        chapter_index = (ROOT / "locales/zh-TW/book/ch22/README.md").read_text(encoding="utf-8")
        self.assertIn("第22章：休閒與紓壓](book/ch22/README.md)", locale_index)
        self.assertIn("酒後先別泡湯、泡澡或進三溫暖](TW-22-011.md)", chapter_index)
        self.assertTrue((ROOT / ARTICLE).is_file())

        baseline_register = git_json(BASE, REGISTER)
        for field in ("substantive_rechecks", "reader_copy_cleanups"):
            old_rows = baseline_register[field]
            self.assertEqual(self.register[field][:len(old_rows)], old_rows)
        appended_rechecks = self.register["substantive_rechecks"][
            len(baseline_register["substantive_rechecks"]):
        ]
        self.assertFalse(any(row["id"] == ITEM_ID for row in appended_rechecks))
        self.assertEqual(self.batch["counts_before"]["runtime_items"], len(git_json(
            BASE, "localization/tw-edition/runtime.json")["items"]
        ))
        self.assertEqual(self.batch["counts_before"]["runtime_sources"], len(git_json(
            BASE, "localization/tw-edition/runtime.json")["sources"]
        ))

    def test_coverage_is_regenerated_and_only_this_core_item_is_added(self):
        self.assertEqual(self.coverage, audit_drafts())
        self.assertFalse(self.coverage["publication_ready"])
        old_runtime = git_json(BASE, "localization/tw-edition/runtime.json")
        old_coverage = git_json(BASE, "localization/tw-edition/coverage.json")
        before = self.batch["counts_before"]
        after = self.batch["counts_after"]
        self.assertEqual(before["runtime_items"], len(old_runtime["items"]))
        self.assertEqual(before["runtime_sources"], len(old_runtime["sources"]))
        self.assertEqual(after["runtime_items"], before["runtime_items"] + 1)
        self.assertEqual(after["runtime_sources"], before["runtime_sources"] + len(self.batch["new_source_ids"]))
        self.assertEqual(before["core_reviewed_entries"], old_coverage["core_reviewed_entries"])
        self.assertEqual(after["core_reviewed_entries"], before["core_reviewed_entries"] + 1)
        self.assertEqual(before["publication_completed_entries"], old_coverage["publication_completed_entries"])
        self.assertEqual(after["publication_completed_entries"], before["publication_completed_entries"] + 1)
        self.assertEqual(before["registry_sources"], old_coverage["registry_sources"])
        self.assertEqual(after["registry_sources"], before["registry_sources"] + len(self.batch["new_source_ids"]))
        self.assertEqual(before["topics_with_any_content"], old_coverage["topics_with_any_content"])
        self.assertEqual(after["topics_with_any_content"], before["topics_with_any_content"] + 1)
        self.assertEqual(before["entries_without_any_draft"], old_coverage["entries_without_any_draft"])
        self.assertEqual(after["entries_without_any_draft"], before["entries_without_any_draft"] - 1)
        self.assertFalse(any(row.startswith(f"{ITEM_ID}:") for row in self.coverage["publication_blockers"]))
        self.assertLessEqual(after["runtime_items"], len(self.runtime["items"]))
        self.assertLessEqual(after["runtime_sources"], len(self.runtime["sources"]))
        self.assertLessEqual(after["core_reviewed_entries"], self.coverage["core_reviewed_entries"])
        self.assertLessEqual(after["publication_completed_entries"], self.coverage["publication_completed_entries"])
        self.assertLessEqual(after["registry_sources"], self.coverage["registry_sources"])


if __name__ == "__main__":
    unittest.main()

"""第二章辣椒與食用油研究首次正式發布契約。"""
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
from review_contract import publication_report, validate_runtime
from source_bundle_test_support import source_bundle_ids_added_since

BASE = "6fc906b54a9f41d83fe44facaacb3c70219b485b"
DATE = "2026-11-21"
DUE = "2027-02-21"
REGISTER = "localization/retroactive-review-register-20261019.json"
CHAPTER = "localization/tw-edition/chapters/02.json"
SOURCE_BUNDLE = "localization/tw-edition/sources/ch02-diet-oil-chili-topic-fidelity-20261121.json"
BATCH = "localization/ch02-diet-oil-chili-topic-fidelity-20261121.json"
ARTICLES = {
    "TW-02-033": {
        "path": "locales/zh-TW/book/ch02/TW-02-033.md",
        "row_sha256": "b86e70983f7aa2756931db6185a5958f5cab34c1f81b7818a05f306b20b13a72",
        "source_ids": ["tw02_chili_molisani_2019", "tw02_chili_meta_2021", "tw02_chili_meta_2022"],
    },
    "TW-02-040": {
        "path": "locales/zh-TW/book/ch02/TW-02-040.md",
        "row_sha256": "4b8559a91a40d1b66dbda3ed8e070f39a4cf7e91424c6bf4fbfe17f21cc69672",
        "source_ids": ["tw02_tfda_food_act_labeling", "tw02_tfda_oil_guide_2026", "tw02_tfda_oil_sampling_2026", "tw02_tfda_oil_incident_portal"],
    },
    "TW-02-041": {
        "path": "locales/zh-TW/book/ch02/TW-02-041.md",
        "row_sha256": "0b6d362eb195df2917786848144841268c450378d1ee9e86a5148c8cc6836430",
        "source_ids": ["tw02_hpa_dietary_guideline_2018", "tw02_sfa_cochrane_2020", "tw02_sfa_risk_stratified_2026", "tw02_ala_cochrane_2020"],
    },
}
SOURCE_IDS = {source_id for item in ARTICLES.values() for source_id in item["source_ids"]}


def read(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def git_bytes(revision, path):
    result = subprocess.run(["git", "show", f"{revision}:{path}"], cwd=ROOT, capture_output=True)
    return result.stdout if result.returncode == 0 else None


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


class DietOilChiliTopicFidelityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.runtime = validate_runtime()
        cls.items = {row["id"]: row for row in cls.runtime["items"]}
        cls.sources = {row["id"]: row for row in cls.runtime["sources"]}
        cls.manifest = {row["id"]: row for row in read("localization/manifest.json")["entries"]}
        cls.reviews = {item_id: read(f"localization/reviews/{item_id}.json") for item_id in ARTICLES}
        cls.articles = {item_id: (ROOT / spec["path"]).read_bytes() for item_id, spec in ARTICLES.items()}
        cls.bodies = {key: value.decode("utf-8") for key, value in cls.articles.items()}
        cls.bundle = read(SOURCE_BUNDLE)
        cls.batch = read(BATCH)
        cls.coverage = read("localization/tw-edition/coverage.json")
        cls.register = read(REGISTER)

    def test_first_publication_preserves_prior_topics_and_recheck_history(self):
        self.assertEqual(self.batch["baseline_main_sha"], BASE)
        baseline_manifest = {row["id"]: row for row in json.loads(git_bytes(BASE, "localization/manifest.json"))["entries"]}
        baseline_chapter = json.loads(git_bytes(BASE, CHAPTER))
        current_chapter = read(CHAPTER)
        before_rows = {row[0]: row for row in baseline_chapter["entries"]}
        after_rows = {row[0]: row for row in current_chapter["entries"]}
        self.assertEqual(set(before_rows), set(after_rows))
        changed = {number for number in before_rows if before_rows[number] != after_rows[number]}
        self.assertEqual(changed, {33, 40, 41})

        for item_id, spec in ARTICLES.items():
            with self.subTest(item_id=item_id):
                number = int(item_id[-3:])
                old = baseline_manifest[item_id]
                self.assertEqual((old["status"], old["treatment"], old["target_path"], old["sources"]),
                                 ("pending", "unclassified", None, []))
                self.assertIsNone(git_bytes(BASE, spec["path"]))
                self.assertIsNone(git_bytes(BASE, f"localization/reviews/{item_id}.json"))
                structured_sha = sha(json.dumps(before_rows[number], ensure_ascii=False, separators=(",", ":")).encode())
                self.assertEqual(structured_sha, spec["row_sha256"])
                self.assertEqual(self.reviews[item_id]["prior_structured_draft_sha256"], structured_sha)
                batch_item = next(row for row in self.batch["items"] if row["id"] == item_id)
                self.assertEqual(batch_item["prior_structured_draft_sha256"], structured_sha)
                self.assertEqual(batch_item["prior_structured_source_refs"], before_rows[number][5].split())

        baseline_register = json.loads(git_bytes(BASE, REGISTER))
        self.assertEqual(self.register, baseline_register)

    def test_manifest_runtime_review_body_and_navigation_are_hash_bound(self):
        runtime_order = [row["id"] for row in self.runtime["items"]]
        baseline_runtime = json.loads(git_bytes(BASE, "localization/tw-edition/runtime.json"))
        baseline_runtime_ids = [row["id"] for row in baseline_runtime["items"]]
        baseline_runtime_id_set = set(baseline_runtime_ids)
        self.assertEqual(
            [item_id for item_id in runtime_order if item_id in baseline_runtime_id_set],
            baseline_runtime_ids,
        )
        self.assertTrue(set(ARTICLES).issubset(runtime_order))
        self.assertTrue(
            all(runtime_order.index(item_id) > max(runtime_order.index(old_id) for old_id in baseline_runtime_ids)
                for item_id in ARTICLES)
        )
        chapter_readme = (ROOT / "locales/zh-TW/book/ch02/README.md").read_text(encoding="utf-8")
        for item_id, spec in ARTICLES.items():
            with self.subTest(item_id=item_id):
                entry, item, review = self.manifest[item_id], self.items[item_id], self.reviews[item_id]
                body = self.bodies[item_id]
                digest = sha(self.articles[item_id])
                self.assertEqual((entry["status"], entry["treatment"], entry["verified_at"]),
                                 ("verified", "taiwan_independent_rewrite", DATE))
                self.assertEqual(entry["target_path"], spec["path"])
                self.assertEqual(entry["sources"], spec["source_ids"])
                self.assertEqual(item["body"], body)
                self.assertEqual(item["target_path"], spec["path"])
                self.assertEqual(item["source_ids"], spec["source_ids"])
                self.assertEqual((item["reviewed_at"], item["review_due_at"]), (DATE, DUE))
                self.assertEqual((review["reviewed_at"], review["review_due_at"]), (DATE, DUE))
                self.assertEqual(review["target_sha256"], digest)
                self.assertEqual(review["source_reviewed_sha256"], digest)
                self.assertEqual(review["source_bundle_path"], SOURCE_BUNDLE)
                self.assertEqual(review["source_bundle_sha256"], sha((ROOT / SOURCE_BUNDLE).read_bytes()))
                self.assertEqual(review["source_ids"], spec["source_ids"])
                self.assertTrue(review["professional_review"]["required"])
                self.assertFalse(review["professional_review"]["obtained"])
                self.assertTrue(review["unresolved_questions"])
                self.assertEqual(chapter_readme.count(f"{item_id}.md"), 1)
                self.assertNotRegex(body, r"(批次摘要|AI協助|本次.{0,12}(?:審查|再審|核對)|CI\s*(?:成功|通過)|PR\s*#\d+|待專業審閱|fork管理)")

        self.assertIn("TW-02-032.md", chapter_readme)
        self.assertIn("TW-02-034.md", chapter_readme)
        ids_in_readme = [int(value) for value in re.findall(r"TW-02-(\d{3})\.md", chapter_readme)]
        self.assertEqual(ids_in_readme, sorted(ids_in_readme))

    def test_sources_statistics_and_topic_fidelity_are_explicit(self):
        self.assertEqual(self.bundle["checked_at"], DATE)
        bundled = {row[0]: row for row in self.bundle["sources"]}
        self.assertEqual(set(bundled), SOURCE_IDS)
        self.assertEqual(set(self.batch["new_source_ids"]), SOURCE_IDS)
        self.assertTrue(SOURCE_IDS.isdisjoint({row["id"] for row in json.loads(git_bytes(BASE, "localization/tw-edition/runtime.json"))["sources"]}))
        self.assertEqual(set(self.sources) - {row["id"] for row in json.loads(git_bytes(BASE, "localization/tw-edition/runtime.json"))["sources"]},
                         source_bundle_ids_added_since(ROOT, BASE))
        for item_id, spec in ARTICLES.items():
            review = self.reviews[item_id]
            checks = {row["source_id"]: row for row in review["source_checks"]}
            urls = set(re.findall(r"\]\((https://[^)]+)\)", self.bodies[item_id]))
            self.assertEqual(set(checks), set(spec["source_ids"]), item_id)
            self.assertEqual(urls, {self.sources[source_id]["url"] for source_id in spec["source_ids"]}, item_id)
            for source_id in spec["source_ids"]:
                source, check = self.sources[source_id], checks[source_id]
                self.assertEqual(bundled[source_id], [source[key] for key in ("id", "title", "url", "supports")])
                self.assertEqual((check["title"], check["url"], check["accessed_at"]),
                                 (source["title"], source["url"], DATE))
                self.assertTrue(check["claim"] and check["supporting_passage"] and check["retrieval_method"])

            for stat in review["statistics_assessed"]:
                for field in ("value", "unit", "period", "geographic_scope", "population", "numerator",
                              "denominator", "denominator_definition", "event_definition", "data_type",
                              "limitations", "source_ids", "accessed_at"):
                    self.assertTrue(stat.get(field), (item_id, stat.get("topic"), field))
                self.assertLessEqual(stat["accessed_at"], DATE)
                self.assertTrue(set(stat["source_ids"]).issubset(set(spec["source_ids"])))

        chili_review = self.reviews["TW-02-033"]
        self.assertIn("觀察性研究", self.bodies["TW-02-033"])
        self.assertIn("沒有足夠資料替台灣居民訂出", self.bodies["TW-02-033"])
        self.assertIn("重疊", " ".join(chili_review["limits"]))
        self.assertEqual(chili_review["topic_fidelity_review"]["historical_claim_decisions"][0]["decision"],
                         "retain_as_observational_association_not_prescription")

        oil_body = self.bodies["TW-02-040"]
        self.assertIn("第 25 條", oil_body)
        self.assertIn("公告的特定品項", oil_body)
        self.assertIn("小量製作本身不代表不安全", oil_body)
        self.assertIn("658 件", oil_body)
        self.assertIn("不是對全台所有產品隨機抽樣", oil_body)
        self.assertEqual(self.reviews["TW-02-040"]["topic_fidelity_review"]["historical_claim_decisions"][0]["decision"],
                         "remove_as_non_taiwan_regulatory_identifier")

        fat_body = self.bodies["TW-02-041"]
        self.assertIn("0.83（95% 信賴區間 0.70 至 0.98", fat_body)
        self.assertIn("RR 0.75", fat_body)
        self.assertIn("不能直接證明特定品牌", fat_body)
        self.assertIn("32827219", fat_body)
        self.assertNotIn("32428300", fat_body)

    def test_coverage_and_batch_counts_match_the_actual_first_publication(self):
        self.assertEqual(self.coverage, audit_drafts())
        self.assertFalse(self.coverage["publication_ready"])
        self.assertEqual(self.coverage["publication_completed_entries"], publication_report()["publication_completed_entries"])
        self.assertFalse(any(row.startswith(tuple(ARTICLES)) for row in self.coverage["publication_blockers"]))

        baseline_coverage = json.loads(git_bytes(BASE, "localization/tw-edition/coverage.json"))
        baseline_runtime = json.loads(git_bytes(BASE, "localization/tw-edition/runtime.json"))
        baseline_manifest = json.loads(git_bytes(BASE, "localization/manifest.json"))
        baseline_register = json.loads(git_bytes(BASE, REGISTER))
        before, after = self.batch["counts_before"], self.batch["counts_after"]
        self.assertEqual(before["manifest_entries"], len(baseline_manifest["entries"]))
        self.assertEqual(before["verified_core_entries"], baseline_coverage["core_reviewed_entries"])
        self.assertEqual(before["runtime_items"], len(baseline_runtime["items"]))
        self.assertEqual(before["runtime_sources"], len(baseline_runtime["sources"]))
        self.assertEqual(before["source_registry"], baseline_coverage["registry_sources"])
        self.assertEqual(before["review_rechecks"], len(baseline_register["substantive_rechecks"]))
        self.assertEqual(before["coverage_json_files"], baseline_coverage["json_files_checked"])
        self.assertEqual(before["unresolved_source_ids"], len(baseline_coverage["unresolved_source_ids"]))
        self.assertEqual(before["unresolved_reference_occurrences"], baseline_coverage["unresolved_reference_occurrences"])
        self.assertEqual(before["publication_completed_entries"], baseline_coverage["publication_completed_entries"])
        self.assertEqual(before["publication_ready"], baseline_coverage["publication_ready"])

        self.assertEqual(after["manifest_entries"], before["manifest_entries"])
        self.assertEqual(after["verified_core_entries"], before["verified_core_entries"] + len(ARTICLES))
        self.assertEqual(after["runtime_items"], before["runtime_items"] + len(ARTICLES))
        self.assertEqual(after["runtime_sources"], before["runtime_sources"] + len(SOURCE_IDS))
        self.assertEqual(after["source_registry"], before["source_registry"] + len(SOURCE_IDS))
        self.assertEqual(after["review_rechecks"], before["review_rechecks"])
        self.assertEqual(after["coverage_json_files"], before["coverage_json_files"] + 5)
        self.assertLessEqual(after["unresolved_source_ids"], before["unresolved_source_ids"])
        self.assertLessEqual(after["unresolved_reference_occurrences"], before["unresolved_reference_occurrences"])
        self.assertEqual(after["publication_completed_entries"], before["publication_completed_entries"] + len(ARTICLES))
        self.assertFalse(after["publication_ready"])
        self.assertGreaterEqual(self.coverage["core_reviewed_entries"], after["verified_core_entries"])
        self.assertGreaterEqual(len(self.runtime["items"]), after["runtime_items"])
        self.assertGreaterEqual(len(self.runtime["sources"]), after["runtime_sources"])
        self.assertGreaterEqual(self.coverage["registry_sources"], after["source_registry"])
        self.assertGreaterEqual(self.coverage["json_files_checked"], after["coverage_json_files"])


if __name__ == "__main__":
    unittest.main()

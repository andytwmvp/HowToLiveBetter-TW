"""第五章金融與消費安全首次正式發布契約。"""
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

BASE = "c5c4a8f48cae4040a69edc3b7d9caa6ceac5d112"
DATE = "2026-11-21"
DUE = "2027-02-21"
REGISTER = "localization/retroactive-review-register-20261019.json"
CHAPTER = "localization/tw-edition/chapters/05.json"
SOURCE_BUNDLE = "localization/tw-edition/sources/ch05-fraud-prepaid-deposit-20261121.json"
BATCH = "localization/ch05-financial-consumer-safety-20261121.json"
ARTICLES = {
    "TW-05-006": {
        "path": "locales/zh-TW/book/ch05/TW-05-006.md",
        "row_sha256": "fc78901912cb30f7b085c304825d6d39a1e61f3d1d93e686cb3ca7485a5d4f55",
        "source_ids": [
            "tw05_npa_fraud_stats_2025",
            "tw05_cib_fake_investment",
            "tw05_anti_fraud_article28",
            "tw05_npa_recovery_scam_2026",
        ],
    },
    "TW-05-010": {
        "path": "locales/zh-TW/book/ch05/TW-05-010.md",
        "row_sha256": "e9d3575f3b6585a485209c75c0a8b4f802b7fc1a2bc0c4d82e04738a2d547201",
        "source_ids": ["tw05_cib_child_otp_2026", "tw05_npa_165_reporting_faq"],
    },
    "TW-05-022": {
        "path": "locales/zh-TW/book/ch05/TW-05-022.md",
        "row_sha256": "06c536778dee1a3be5b10c53a3b8820e515d7e6676dd3471c072fdcbd870339e",
        "source_ids": [
            "tw05_consumer_protection_act",
            "tw05_cpc_prepaid_transactions",
            "tw05_cpc_dispute_process",
            "tw05_cpc_1950",
        ],
    },
    "TW-05-042": {
        "path": "locales/zh-TW/book/ch05/TW-05-042.md",
        "row_sha256": "06e229c2d9230b8f3afaa8323e861df83a69fefe760d02bdec9d94ec60c0a5f3",
        "source_ids": [
            "tw05_cdic_deposit_faq",
            "tw05_insurance_agent_rule",
            "tw05_finconsumer_act",
            "tw05_foi_appeal_process",
        ],
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


class FinancialConsumerSafetyPublicationTests(unittest.TestCase):
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

    def test_first_publication_preserves_prior_topics_and_review_history(self):
        self.assertEqual(self.batch["baseline_main_sha"], BASE)
        baseline_manifest = {
            row["id"]: row
            for row in json.loads(git_bytes(BASE, "localization/manifest.json"))["entries"]
        }
        baseline_chapter = json.loads(git_bytes(BASE, CHAPTER))
        current_chapter = read(CHAPTER)
        before_rows = {row[0]: row for row in baseline_chapter["entries"]}
        after_rows = {row[0]: row for row in current_chapter["entries"]}
        self.assertEqual(set(before_rows), set(after_rows))
        self.assertEqual(
            {number for number in before_rows if before_rows[number] != after_rows[number]},
            {6, 10, 22, 42},
        )

        for item_id, spec in ARTICLES.items():
            with self.subTest(item_id=item_id):
                old = baseline_manifest[item_id]
                self.assertEqual(
                    (old["status"], old["treatment"], old["target_path"], old["sources"]),
                    ("pending", "unclassified", None, []),
                )
                self.assertIsNone(git_bytes(BASE, spec["path"]))
                self.assertIsNone(git_bytes(BASE, f"localization/reviews/{item_id}.json"))
                number = int(item_id[-3:])
                structured_sha = sha(
                    json.dumps(before_rows[number], ensure_ascii=False, separators=(",", ":")).encode()
                )
                self.assertEqual(structured_sha, spec["row_sha256"])
                review = self.reviews[item_id]
                batch_item = next(row for row in self.batch["items"] if row["id"] == item_id)
                self.assertEqual(review["prior_structured_draft_sha256"], structured_sha)
                self.assertEqual(batch_item["prior_structured_draft_sha256"], structured_sha)
                self.assertIsNone(review["prior_structured_draft_review"])
                self.assertEqual(batch_item["prior_structured_source_refs"], before_rows[number][5].split())

        self.assertEqual(self.register, json.loads(git_bytes(BASE, REGISTER)))

    def test_manifest_runtime_review_body_sources_and_navigation_are_hash_bound(self):
        baseline_runtime = json.loads(git_bytes(BASE, "localization/tw-edition/runtime.json"))
        baseline_runtime_ids = [row["id"] for row in baseline_runtime["items"]]
        baseline_runtime_id_set = set(baseline_runtime_ids)
        current_runtime_ids = [row["id"] for row in self.runtime["items"]]
        self.assertEqual(
            [item_id for item_id in current_runtime_ids if item_id in baseline_runtime_id_set],
            baseline_runtime_ids,
        )
        self.assertTrue(set(ARTICLES).issubset(current_runtime_ids))
        self.assertTrue(
            all(current_runtime_ids.index(item_id) > max(current_runtime_ids.index(old_id) for old_id in baseline_runtime_ids)
                for item_id in ARTICLES)
        )
        chapter_readme = (ROOT / "locales/zh-TW/book/ch05/README.md").read_text(encoding="utf-8")
        root_readme = (ROOT / "locales/zh-TW/README.md").read_text(encoding="utf-8")
        self.assertEqual(root_readme.count("[第5章：省下不必要支出，保護財務選擇](book/ch05/README.md)"), 1)
        for item_id, spec in ARTICLES.items():
            with self.subTest(item_id=item_id):
                entry, item, review = self.manifest[item_id], self.items[item_id], self.reviews[item_id]
                body = self.bodies[item_id]
                digest = sha(self.articles[item_id])
                self.assertEqual(
                    (entry["status"], entry["treatment"], entry["verified_at"]),
                    ("verified", "taiwan_independent_rewrite", DATE),
                )
                self.assertEqual(entry["target_path"], spec["path"])
                self.assertEqual(entry["sources"], spec["source_ids"])
                self.assertEqual(item["body"], body)
                self.assertEqual(item["target_path"], spec["path"])
                self.assertEqual(item["source_ids"], spec["source_ids"])
                self.assertEqual(item["review_status"], "source_checked")
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
                self.assertNotRegex(
                    body,
                    r"(批次摘要|AI協助|本次.{0,12}(?:審查|再審|核對)|CI\s*(?:成功|通過)|PR\s*#\d+|待專業審閱|fork管理)",
                )

        ids_in_readme = [int(value) for value in re.findall(r"TW-05-(\d{3})\.md", chapter_readme)]
        self.assertEqual(ids_in_readme, sorted(ids_in_readme))

    def test_sources_statistics_legal_dates_and_frequency_limits_are_explicit(self):
        self.assertEqual(self.bundle["checked_at"], DATE)
        bundled = {row[0]: row for row in self.bundle["sources"]}
        self.assertEqual(set(bundled), SOURCE_IDS)
        self.assertEqual(set(self.batch["new_source_ids"]), SOURCE_IDS)
        baseline_runtime = json.loads(git_bytes(BASE, "localization/tw-edition/runtime.json"))
        baseline_source_ids = {row["id"] for row in baseline_runtime["sources"]}
        self.assertTrue(SOURCE_IDS.isdisjoint(baseline_source_ids))
        self.assertEqual(
            set(self.sources) - baseline_source_ids,
            source_bundle_ids_added_since(ROOT, BASE),
        )

        for item_id, spec in ARTICLES.items():
            review = self.reviews[item_id]
            checks = {row["source_id"]: row for row in review["source_checks"]}
            urls = set(re.findall(r"\]\((https://[^)]+)\)", self.bodies[item_id]))
            self.assertEqual(set(checks), set(spec["source_ids"]), item_id)
            self.assertEqual(urls, {self.sources[source_id]["url"] for source_id in spec["source_ids"]}, item_id)
            for source_id in spec["source_ids"]:
                source, check = self.sources[source_id], checks[source_id]
                self.assertEqual(
                    bundled[source_id],
                    [source[key] for key in ("id", "title", "url", "supports")],
                )
                self.assertEqual((check["title"], check["url"], check["accessed_at"]),
                                 (source["title"], source["url"], DATE))
                self.assertTrue(check["claim"] and check["supporting_passage"] and check["retrieval_method"])

            for stat in review["statistics_assessed"]:
                for field in (
                    "value", "unit", "period", "geographic_scope", "population", "numerator",
                    "denominator", "denominator_definition", "event_definition", "data_type",
                    "limitations", "source_ids", "accessed_at",
                ):
                    self.assertTrue(stat.get(field), (item_id, stat.get("topic"), field))
                self.assertLessEqual(stat["accessed_at"], DATE)
                self.assertTrue(set(stat["source_ids"]).issubset(set(spec["source_ids"])))

        fraud = self.bodies["TW-05-006"]
        fraud_stat = self.reviews["TW-05-006"]["statistics_assessed"][0]
        self.assertIn("197,595 件", fraud)
        self.assertIn("58,675 件", fraud)
        self.assertIn("29.69%", fraud)
        self.assertIn("不是投資人的受害率", fraud)
        self.assertIn("不是人口率", fraud_stat["unit"])
        self.assertIn("197595", str(fraud_stat["value"]))

        child = self.bodies["TW-05-010"]
        child_stat = self.reviews["TW-05-010"]["statistics_assessed"][0]
        self.assertIn("不能當成兒少遇到此類詐騙的全國發生率", child)
        self.assertIn("非抽樣研究", child_stat["population"])
        self.assertIn("未提供", child_stat["denominator"])

        prepaid = self.bodies["TW-05-022"]
        legal_dates = self.reviews["TW-05-022"]["legal_date_assessment"]
        self.assertIn("不是所有預付款", prepaid)
        self.assertIn("消費者保護法第17條", str(legal_dates))
        financial = self.bodies["TW-05-042"]
        self.assertIn("30 日內", financial)
        self.assertIn("60 日內", financial)
        self.assertIn("期限屆滿之日起", financial)
        self.assertIn("2024-02-01", str(self.reviews["TW-05-042"]["legal_date_assessment"]))
        self.assertIn("第13條", str(self.reviews["TW-05-042"]["legal_date_assessment"]))

    def test_coverage_and_batch_counts_match_the_actual_publication(self):
        self.assertEqual(self.coverage, audit_drafts())
        self.assertFalse(self.coverage["publication_ready"])
        self.assertEqual(
            self.coverage["publication_completed_entries"],
            publication_report()["publication_completed_entries"],
        )
        self.assertFalse(any(row.startswith(tuple(ARTICLES)) for row in self.coverage["publication_blockers"]))

        baseline_coverage = json.loads(git_bytes(BASE, "localization/tw-edition/coverage.json"))
        baseline_runtime = json.loads(git_bytes(BASE, "localization/tw-edition/runtime.json"))
        baseline_manifest = json.loads(git_bytes(BASE, "localization/manifest.json"))
        baseline_register = json.loads(git_bytes(BASE, REGISTER))
        before, after = self.batch["counts_before"], self.batch["counts_after"]
        self.assertEqual(before["manifest_entries"], len(baseline_manifest["entries"]))
        self.assertEqual(before["verified_core_entries"], baseline_coverage["publication_completed_entries"])
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
        self.assertEqual(after["coverage_json_files"], before["coverage_json_files"] + len(ARTICLES) + 2)
        self.assertLessEqual(after["unresolved_source_ids"], before["unresolved_source_ids"])
        self.assertLessEqual(after["unresolved_reference_occurrences"], before["unresolved_reference_occurrences"])
        self.assertEqual(after["publication_completed_entries"], before["publication_completed_entries"] + len(ARTICLES))
        self.assertFalse(after["publication_ready"])


if __name__ == "__main__":
    unittest.main()

"""第2章活動與飲食研究主題再審：保留原題價值並交代外推限制。"""
import hashlib
import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools/tw"))

from ci_language_policy import audit_drafts
from retroactive_audit import documented_revision
from review_contract import validate_runtime


BASE = "4c458e0ef48db03bfa05b50af212b245b5e673a6"
DATE = "2026-11-17"
DUE = "2027-02-17"
REGISTER = "localization/retroactive-review-register-20261019.json"
BATCH = "localization/ch02-activity-food-topic-fidelity-recheck-20261117.json"
SOURCE_BUNDLE = "localization/tw-edition/sources/ch02-activity-food-topic-fidelity-recheck-20261117.json"
ITEMS = {
    "TW-02-011": {
        "title": "每天步數與每週活動量：找到適合自己的起點",
        "required_text": (
            "7,000步", "2,000步", "HR 0.53", "14項研究", "25,472名",
            "35.6%", "死亡機率降低47%",
        ),
    },
    "TW-02-014": {
        "title": "球拍運動與長期健康：如何解讀英國研究",
        "required_text": (
            "蘇格蘭與英格蘭", "80,306名", "2,917人", "54例全因死亡",
            "75,014人、1,909例心血管死亡", "2,883人、9例死亡", "未把桌球列入",
        ),
    },
    "TW-02-018": {
        "title": "加工肉與健康：風險證據和飲食建議怎麼看",
        "required_text": (
            "每天攝取50克", "相對風險約增加18%", "弱建議", "證據確定性為低",
            "不是台灣主管機關的飲食建議",
        ),
    },
    "TW-02-028": {
        "title": "超加工食品：研究證據與台灣日常選擇",
        "required_text": (
            "51項成人前瞻性世代研究", "8,819,894名", "HR 1.18", "9名",
            "813.5大卡", "1.1公斤", "不是全因死亡分析的單一分母",
        ),
    },
}


def read_json(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def git_bytes(revision, path):
    return subprocess.check_output(["git", "show", f"{revision}:{path}"], cwd=ROOT)


def added_revision(path):
    result = subprocess.run(
        ["git", "log", "--diff-filter=A", "--format=%H", "--", path],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.splitlines()
    return result[0] if result else None


def digest(data):
    return hashlib.sha256(data).hexdigest()


class ActivityFoodTopicFidelityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.batch_revision = added_revision(BATCH)

        def at_batch(path):
            if cls.batch_revision:
                return git_bytes(cls.batch_revision, path)
            return (ROOT / path).read_bytes()

        cls.runtime = validate_runtime()
        cls.items = {row["id"]: row for row in cls.runtime["items"]}
        cls.sources = {row["id"]: row for row in cls.runtime["sources"]}
        cls.coverage = read_json("localization/tw-edition/coverage.json")
        cls.register = read_json(REGISTER)
        cls.batch = json.loads(at_batch(BATCH))
        cls.snapshot_runtime = json.loads(at_batch("localization/tw-edition/runtime.json"))
        cls.snapshot_manifest = json.loads(at_batch("localization/manifest.json"))
        cls.snapshot_coverage = json.loads(at_batch("localization/tw-edition/coverage.json"))
        cls.snapshot_register = json.loads(at_batch(REGISTER))
        cls.bundle = json.loads(at_batch(SOURCE_BUNDLE))
        cls.source_bundle_bytes = at_batch(SOURCE_BUNDLE)
        cls.snapshot_items = {row["id"]: row for row in cls.snapshot_runtime["items"]}
        cls.snapshot_sources = {row["id"]: row for row in cls.snapshot_runtime["sources"]}
        cls.snapshot_manifest_items = {
            row["id"]: row for row in cls.snapshot_manifest["entries"]
        }
        cls.review_bytes = {
            item_id: at_batch(f"localization/reviews/{item_id}.json")
            for item_id in ITEMS
        }
        cls.reviews = {
            item_id: json.loads(cls.review_bytes[item_id]) for item_id in ITEMS
        }
        cls.articles = {
            item_id: at_batch(f"locales/zh-TW/book/ch02/{item_id}.md")
            for item_id in ITEMS
        }
        cls.rows = {
            item_id: next(
                row for row in reversed(cls.snapshot_register["substantive_rechecks"])
                if row["id"] == item_id and row["reviewed_at"] == DATE
            )
            for item_id in ITEMS
        }

    def test_review_hashes_and_append_only_history(self):
        self.assertEqual(self.batch["baseline_main_sha"], BASE)
        self.assertEqual(self.batch["reviewed_at"], DATE)
        self.assertEqual(self.batch["review_due_at"], DUE)

        baseline_register = json.loads(git_bytes(BASE, REGISTER))
        rows_before = baseline_register["substantive_rechecks"]
        rows_after = self.register["substantive_rechecks"]
        self.assertEqual(rows_after[:len(rows_before)], rows_before)
        appended = rows_after[len(rows_before):]
        expected_rows = [self.rows[item_id] for item_id in ITEMS]
        self.assertEqual(
            appended[:len(expected_rows)],
            expected_rows,
        )

        for item_id, article_bytes in self.articles.items():
            with self.subTest(item_id=item_id):
                article_path = f"locales/zh-TW/book/ch02/{item_id}.md"
                review_path = f"localization/reviews/{item_id}.json"
                row = self.rows[item_id]
                review = self.reviews[item_id]
                article_sha = digest(article_bytes)
                old_body = git_bytes(BASE, article_path)
                old_review = git_bytes(BASE, review_path)
                prior_revision = subprocess.check_output(
                    ["git", "log", "-1", "--format=%H", BASE, "--", article_path],
                    cwd=ROOT,
                    text=True,
                ).strip()

                self.assertEqual(row["prior_revision"], prior_revision)
                self.assertEqual(row["before_sha256"], digest(old_body))
                self.assertEqual(row["previous_body"], old_body.decode("utf-8"))
                self.assertEqual(row["prior_review_sha256"], digest(old_review))
                self.assertEqual(row["previous_review_snapshot"], json.loads(old_review))
                self.assertEqual(row["after_sha256"], article_sha)
                self.assertEqual(review["target_sha256"], article_sha)
                self.assertEqual(review["source_reviewed_sha256"], article_sha)
                self.assertEqual(row["review_sha256"], digest(self.review_bytes[item_id]))
                self.assertEqual(row["source_bundle_sha256"], digest(self.source_bundle_bytes))
                self.assertEqual(row["status"], "ai_source_rechecked_professional_pending")
                self.assertTrue(review["professional_review"]["required"])
                self.assertFalse(review["professional_review"]["obtained"])
                self.assertEqual(review["source_checks"], row["source_checks"])
                self.assertEqual(review["statistics_assessed"], row["statistics_assessed"])
                self.assertEqual(review["topic_fidelity_review"], row["topic_fidelity_review"])

    def test_runtime_revision_contract_retains_exact_limits_and_sources(self):
        old_runtime = json.loads(git_bytes(BASE, "localization/tw-edition/runtime.json"))
        old_items = {row["id"]: row for row in old_runtime["items"]}
        for item_id in ITEMS:
            with self.subTest(item_id=item_id):
                row = self.rows[item_id]
                reviewed_item = self.snapshot_items[item_id]
                self.assertEqual(reviewed_item["limits"], " ".join(row["limits"]))
                self.assertTrue(documented_revision(old_items[item_id], reviewed_item, row))

                import copy

                missing_limit = copy.deepcopy(row)
                missing_limit["limits"] = missing_limit["limits"][:-1]
                self.assertFalse(documented_revision(old_items[item_id], reviewed_item, missing_limit))

                extra_runtime_limit = dict(reviewed_item, limits=reviewed_item["limits"] + " Unsupported claim.")
                self.assertFalse(documented_revision(old_items[item_id], extra_runtime_limit, row))

                unsupported_decision = copy.deepcopy(row)
                unsupported_decision["topic_fidelity_review"]["question_change"]["decision"] = "restore_everything"
                self.assertFalse(documented_revision(old_items[item_id], reviewed_item, unsupported_decision))

                missing_rationale = copy.deepcopy(row)
                missing_rationale["topic_fidelity_review"]["question_change"].pop("rationale", None)
                self.assertFalse(documented_revision(old_items[item_id], reviewed_item, missing_rationale))

    def test_restored_research_preserves_taiwan_advice_and_population_limits(self):
        self.assertEqual({row["id"] for row in self.batch["items"]}, set(ITEMS))
        batch_items = {row["id"]: row for row in self.batch["items"]}
        for item_id, contract in ITEMS.items():
            with self.subTest(item_id=item_id):
                body = self.snapshot_items[item_id]["body"]
                self.assertEqual(body.encode("utf-8"), self.articles[item_id])
                self.assertEqual(batch_items[item_id]["title"], contract["title"])
                self.assertEqual(self.snapshot_manifest_items[item_id]["status"], "verified")
                self.assertEqual(self.snapshot_manifest_items[item_id]["verified_at"], DATE)
                self.assertEqual(self.snapshot_manifest_items[item_id]["sources"], self.snapshot_items[item_id]["source_ids"])
                self.assertEqual(self.snapshot_items[item_id]["title"], contract["title"])
                for required_text in contract["required_text"]:
                    self.assertIn(required_text, body)

                report_item = batch_items[item_id]
                review = self.reviews[item_id]
                self.assertEqual(review["topic_fidelity_review"]["decision"], report_item["topic_fidelity_review"]["decision"])
                self.assertIn("restore_research_context", review["topic_fidelity_review"]["decision"])
                self.assertTrue(review["professional_review"]["required"])
                self.assertFalse(review["professional_review"]["obtained"])

                for statistic in review["statistics_assessed"]:
                    for key in (
                        "value", "unit", "period", "geographic_scope", "population", "numerator",
                        "denominator", "denominator_definition", "event_definition", "data_type",
                        "limitations", "source_ids", "accessed_at",
                    ):
                        self.assertTrue(statistic.get(key), (item_id, statistic.get("topic"), key))
                    self.assertLessEqual(statistic["accessed_at"], DATE)

    def test_sources_runtime_manifest_and_historical_count_snapshots(self):
        old_runtime = json.loads(git_bytes(BASE, "localization/tw-edition/runtime.json"))
        old_manifest = json.loads(git_bytes(BASE, "localization/manifest.json"))
        old_coverage = json.loads(git_bytes(BASE, "localization/tw-edition/coverage.json"))
        old_register = json.loads(git_bytes(BASE, REGISTER))
        old_runtime_sources = {row["id"] for row in old_runtime["sources"]}
        new_source_ids = set(self.batch["new_source_ids"])
        bundled_ids = {row[0] for row in self.bundle["sources"]}

        self.assertEqual(self.bundle["checked_at"], DATE)
        self.assertEqual(new_source_ids, bundled_ids)
        self.assertEqual(
            {row["id"] for row in self.snapshot_runtime["sources"]} - old_runtime_sources,
            new_source_ids,
        )
        self.assertTrue(old_runtime_sources.issubset({row["id"] for row in self.runtime["sources"]}))
        self.assertTrue(new_source_ids.issubset({row["id"] for row in self.runtime["sources"]}))
        self.assertEqual(self.coverage, audit_drafts())

        rechecked_ids = set(ITEMS)
        before = self.batch["counts_before"]
        after = self.batch["counts_after"]
        self.assertEqual(before["manifest_entries"], len(old_manifest["entries"]))
        self.assertEqual(before["runtime_items"], len(old_runtime["items"]))
        self.assertEqual(before["runtime_sources"], len(old_runtime["sources"]))
        self.assertEqual(before["source_registry"], old_coverage["registry_sources"])
        self.assertEqual(before["coverage_json_files"], old_coverage["json_files_checked"])
        self.assertEqual(before["review_rechecks"], len(old_register["substantive_rechecks"]))
        self.assertEqual(after["manifest_entries"], before["manifest_entries"])
        self.assertEqual(after["verified_core_entries"], before["verified_core_entries"])
        self.assertEqual(after["publication_completed_entries"], before["publication_completed_entries"])
        self.assertEqual(after["runtime_items"], before["runtime_items"])
        self.assertEqual(after["runtime_sources"], before["runtime_sources"] + len(new_source_ids))
        self.assertEqual(after["source_registry"], before["source_registry"] + len(new_source_ids))
        self.assertEqual(after["coverage_json_files"], before["coverage_json_files"] + 2)
        self.assertEqual(after["review_rechecks"], before["review_rechecks"] + len(rechecked_ids))
        self.assertFalse(before["publication_ready"])
        self.assertFalse(after["publication_ready"])

        snapshot_register_sources = {row["id"] for row in self.snapshot_runtime["sources"]}
        snapshot_after_coverage = self.snapshot_coverage
        self.assertEqual(len(self.snapshot_manifest["entries"]), after["manifest_entries"])
        self.assertEqual(len(self.snapshot_runtime["items"]), after["runtime_items"])
        self.assertEqual(len(snapshot_register_sources), after["runtime_sources"])
        self.assertEqual(snapshot_after_coverage["registry_sources"], after["source_registry"])
        self.assertEqual(snapshot_after_coverage["json_files_checked"], after["coverage_json_files"])
        self.assertEqual(
            len(self.snapshot_register["substantive_rechecks"]),
            after["review_rechecks"],
        )
        self.assertGreaterEqual(self.coverage["registry_sources"], after["source_registry"])
        self.assertGreaterEqual(len(self.register["substantive_rechecks"]), after["review_rechecks"])
        for item_id in ITEMS:
            with self.subTest(item_id=item_id):
                item = self.snapshot_items[item_id]
                review = self.reviews[item_id]
                row = self.rows[item_id]
                source_ids = item["source_ids"]
                source_checks = {check["source_id"]: check for check in review["source_checks"]}
                self.assertEqual(self.snapshot_manifest_items[item_id]["sources"], source_ids)
                self.assertEqual(review["source_ids"], source_ids)
                self.assertEqual(row["source_ids"], source_ids)
                self.assertEqual(set(source_checks), set(source_ids))

                article = self.articles[item_id].decode("utf-8")
                body_urls = {
                    line.split("](", 1)[1][:-1]
                    for line in article.splitlines()
                    if "](" in line and line.endswith(")") and "https://" in line
                }
                self.assertEqual(body_urls, {self.snapshot_sources[source_id]["url"] for source_id in source_ids})
                for source_id in source_ids:
                    with self.subTest(source_id=source_id):
                        self.assertEqual(source_checks[source_id]["url"], self.snapshot_sources[source_id]["url"])
                        self.assertEqual(source_checks[source_id]["title"], self.snapshot_sources[source_id]["title"])
                        self.assertLessEqual(source_checks[source_id]["accessed_at"], DATE)


if __name__ == "__main__":
    unittest.main()

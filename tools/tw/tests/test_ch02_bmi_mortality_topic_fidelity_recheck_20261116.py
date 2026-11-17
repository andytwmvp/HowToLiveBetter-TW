"""TW-02-032逐題補回有界線的BMI死亡率研究並保留台灣分類。"""
import hashlib
import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools/tw"))

from ci_language_policy import audit_drafts
from review_contract import validate_runtime
from retroactive_audit import documented_revision
from source_bundle_test_support import source_bundle_ids_added_since


BASE = "930f3332fcb94b041cac194e29bf4286d85f3ee9"
DATE = "2026-11-16"
DUE = "2027-02-16"
ITEM_ID = "TW-02-032"
ARTICLE = "locales/zh-TW/book/ch02/TW-02-032.md"
REVIEW = f"localization/reviews/{ITEM_ID}.json"
REGISTER = "localization/retroactive-review-register-20261019.json"
BATCH = "localization/ch02-bmi-mortality-topic-fidelity-recheck-20261116.json"
SOURCE_BUNDLE = "localization/tw-edition/sources/ch02-bmi-mortality-topic-fidelity-recheck-20261116.json"


def read_json(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def git_bytes(revision, path):
    return subprocess.check_output(["git", "show", f"{revision}:{path}"], cwd=ROOT)


def digest(data):
    return hashlib.sha256(data).hexdigest()


class BmiMortalityTopicFidelityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.runtime = validate_runtime()
        cls.items = {row["id"]: row for row in cls.runtime["items"]}
        cls.sources = {row["id"]: row for row in cls.runtime["sources"]}
        cls.manifest = {
            row["id"]: row for row in read_json("localization/manifest.json")["entries"]
        }
        cls.coverage = read_json("localization/tw-edition/coverage.json")
        cls.register = read_json(REGISTER)
        cls.review = read_json(REVIEW)
        cls.batch = read_json(BATCH)
        cls.bundle = read_json(SOURCE_BUNDLE)
        cls.article_bytes = (ROOT / ARTICLE).read_bytes()
        cls.article = cls.article_bytes.decode("utf-8")
        cls.sha = digest(cls.article_bytes)
        cls.row = next(
            row for row in reversed(cls.register["substantive_rechecks"])
            if row["id"] == ITEM_ID and row["reviewed_at"] == DATE
        )

    def test_review_hashes_and_history_are_append_only(self):
        self.assertEqual(self.batch["baseline_main_sha"], BASE)
        self.assertEqual(self.batch["reviewed_at"], DATE)
        self.assertEqual(self.batch["review_due_at"], DUE)
        old_body = git_bytes(BASE, ARTICLE)
        old_review = git_bytes(BASE, REVIEW)
        self.assertEqual(self.row["prior_revision"], subprocess.check_output(
            ["git", "log", "-1", "--format=%H", BASE, "--", ARTICLE],
            cwd=ROOT,
            text=True,
        ).strip())
        self.assertEqual(self.row["before_sha256"], digest(old_body))
        self.assertEqual(self.row["previous_body"], old_body.decode("utf-8"))
        self.assertEqual(self.row["prior_review_sha256"], digest(old_review))
        self.assertEqual(self.row["previous_review_snapshot"], json.loads(old_review))
        self.assertEqual(self.row["after_sha256"], self.sha)
        self.assertEqual(self.review["target_sha256"], self.sha)
        self.assertEqual(self.review["source_reviewed_sha256"], self.sha)
        self.assertEqual(self.row["review_sha256"], digest((ROOT / REVIEW).read_bytes()))
        self.assertEqual(self.row["source_bundle_sha256"], digest((ROOT / SOURCE_BUNDLE).read_bytes()))
        self.assertEqual(self.review["source_bundle_sha256"], self.row["source_bundle_sha256"])
        self.assertEqual(self.row["status"], "ai_source_rechecked_professional_pending")
        self.assertTrue(self.review["professional_review"]["required"])
        self.assertFalse(self.review["professional_review"]["obtained"])

        baseline_register = json.loads(git_bytes(BASE, REGISTER))
        rows_before = baseline_register["substantive_rechecks"]
        self.assertEqual(self.register["substantive_rechecks"][:len(rows_before)], rows_before)
        appended = self.register["substantive_rechecks"][len(rows_before):]
        self.assertEqual(
            [row for row in appended if row["id"] == ITEM_ID and row["reviewed_at"] == DATE],
            [self.row],
        )
        self.assertEqual(self.review["source_checks"], self.row["source_checks"])
        self.assertEqual(self.review["statistics_assessed"], self.row["statistics_assessed"])
        self.assertEqual(self.review["topic_fidelity_review"], self.row["topic_fidelity_review"])

    def test_recheck_limits_match_exactly_without_accepting_missing_or_extra_text(self):
        old_runtime = json.loads(git_bytes(BASE, "localization/tw-edition/runtime.json"))
        old_item = next(row for row in old_runtime["items"] if row["id"] == ITEM_ID)
        current_item = self.items[ITEM_ID]
        self.assertEqual(current_item["limits"], " ".join(self.row["limits"]))
        self.assertTrue(documented_revision(old_item, current_item, self.row))

        import copy

        missing_limit = copy.deepcopy(self.row)
        missing_limit["limits"] = missing_limit["limits"][:-1]
        self.assertFalse(documented_revision(old_item, current_item, missing_limit))

        extra_runtime_limit = dict(current_item, limits=current_item["limits"] + " Extra unsupported claim.")
        self.assertFalse(documented_revision(old_item, extra_runtime_limit, self.row))

        shuffled_sources = dict(
            current_item,
            source_ids=[current_item["source_ids"][0], current_item["source_ids"][-1],
                        *current_item["source_ids"][1:-1]],
        )
        self.assertFalse(documented_revision(old_item, shuffled_sources, self.row))

    def test_restored_research_keeps_taiwan_scope_and_denominators_clear(self):
        body = self.items[ITEM_ID]["body"]
        self.assertEqual(body, self.article)
        self.assertEqual(self.manifest[ITEM_ID]["status"], "verified")
        self.assertEqual(self.manifest[ITEM_ID]["verified_at"], DATE)
        self.assertEqual(self.manifest[ITEM_ID]["sources"], self.items[ITEM_ID]["source_ids"])
        self.assertEqual(self.items[ITEM_ID]["question"], self.batch["item"]["current_question"])
        self.assertIn("民國108至113年（2019至2024年）", body)
        self.assertNotIn("2020至2024年", body)
        self.assertIn("463,002名成人", body)
        self.assertIn("15,531人死亡", body)
        self.assertIn("MJ健康管理機構", body)
        self.assertIn("未曾吸菸、入組時沒有慢性病且存活超過5年", body)
        self.assertIn("385,879人死亡", body)
        self.assertIn("1,074,385人、100,784人死亡", body)
        self.assertIn("全因死亡危險比（HR）1.39（95%信賴區間1.34至1.44）", body)
        self.assertIn("I²=85%", body)
        self.assertIn("不能證明減到特定數字會延壽", body)
        self.assertNotIn("每個人應把BMI維持在20至25", body)
        self.assertNotIn("本次未取得出版社全文", self.items[ITEM_ID]["limits"])
        self.assertNotIn("尚未取得家庭醫學", self.items[ITEM_ID]["limits"])
        self.assertTrue(any("出版社全文本次無法取得" in value for value in self.review["unresolved_questions"]))

        stats = self.review["statistics_assessed"]
        self.assertEqual(len(stats), 4)
        self.assertEqual(stats[0]["value"], "51.3%")
        self.assertIn("2019至2024年", stats[0]["period"])
        self.assertEqual(stats[1]["value"]["participants"], 463002)
        self.assertEqual(stats[1]["value"]["all_cause_deaths"], 15531)
        self.assertEqual(stats[2]["value"]["east_asian_participants"], 1074385)
        self.assertEqual(stats[2]["value"]["east_asian_all_cause_deaths"], 100784)
        self.assertEqual(stats[3]["value"]["hazard_ratio_overweight_25_to_under_30_vs_18_5_to_under_25"], 0.94)
        for row in stats:
            for key in (
                "value", "unit", "period", "geographic_scope", "population", "numerator",
                "denominator", "event_definition", "data_type", "limitations", "source_ids",
                "accessed_at",
            ):
                self.assertTrue(row.get(key), (row.get("topic"), key))

        decisions = self.review["topic_fidelity_review"]["historical_claim_decisions"]
        self.assertEqual(decisions[0]["decision"], "do_not_restore_as_individual_target_or_causal_prescription")
        self.assertEqual(self.review["topic_fidelity_review"]["question_change"]["decision"], "realign_with_restored_core_topic")
        self.assertFalse(self.coverage["publication_ready"])

    def test_sources_manifest_runtime_coverage_and_counts_match(self):
        item = self.items[ITEM_ID]
        entry = self.manifest[ITEM_ID]
        source_ids = item["source_ids"]
        self.assertEqual(entry["sources"], source_ids)
        self.assertEqual(self.review["source_ids"], source_ids)
        self.assertEqual(self.row["source_ids"], source_ids)
        checks = {row["source_id"]: row for row in self.review["source_checks"]}
        self.assertEqual(set(checks), set(source_ids))
        self.assertEqual(self.row["new_source_ids"], self.batch["new_source_ids"])
        self.assertEqual([row[0] for row in self.bundle["sources"]], self.batch["new_source_ids"])
        self.assertEqual(self.bundle["checked_at"], DATE)

        body_urls = {
            line.split("](", 1)[1][:-1]
            for line in self.article.splitlines()
            if "](" in line and line.endswith(")") and "https://" in line
        }
        self.assertEqual(body_urls, {self.sources[source_id]["url"] for source_id in source_ids})
        for source_id in source_ids:
            source = self.sources[source_id]
            self.assertEqual(checks[source_id]["url"], source["url"])
            self.assertEqual(checks[source_id]["title"], source["title"])
            self.assertLessEqual(checks[source_id]["accessed_at"], DATE)

        old_runtime = json.loads(git_bytes(BASE, "localization/tw-edition/runtime.json"))
        old_source_ids = {row["id"] for row in old_runtime["sources"]}
        newly_added = {row["id"] for row in self.runtime["sources"]} - old_source_ids
        self.assertEqual(newly_added, source_bundle_ids_added_since(ROOT, BASE))
        self.assertTrue(set(self.batch["new_source_ids"]).issubset(newly_added))
        self.assertGreaterEqual(self.runtime["updated_at"], DATE)
        self.assertEqual(self.coverage, audit_drafts())

        before = self.batch["counts_before"]
        after = self.batch["counts_after"]
        baseline_coverage = json.loads(git_bytes(BASE, "localization/tw-edition/coverage.json"))
        baseline_manifest = json.loads(git_bytes(BASE, "localization/manifest.json"))
        self.assertEqual(before["runtime_sources"], len(old_runtime["sources"]))
        self.assertEqual(before["source_registry"], baseline_coverage["registry_sources"])
        self.assertEqual(before["coverage_json_files"], baseline_coverage["json_files_checked"])
        self.assertEqual(before["review_rechecks"], len(json.loads(git_bytes(BASE, REGISTER))["substantive_rechecks"]))
        self.assertEqual(after["runtime_sources"], before["runtime_sources"] + len(self.batch["new_source_ids"]))
        self.assertEqual(after["source_registry"], before["source_registry"] + len(self.batch["new_source_ids"]))
        self.assertEqual(after["coverage_json_files"], before["coverage_json_files"] + 2)
        self.assertEqual(after["review_rechecks"], before["review_rechecks"] + 1)
        self.assertEqual(after["verified_core_entries"], sum(row["status"] == "verified" for row in baseline_manifest["entries"]))
        self.assertEqual(after["publication_completed_entries"], after["verified_core_entries"])
        self.assertGreaterEqual(
            self.coverage["publication_completed_entries"],
            after["publication_completed_entries"],
        )
        self.assertGreaterEqual(
            self.coverage["core_reviewed_entries"],
            after["verified_core_entries"],
        )
        self.assertFalse(after["publication_ready"])


if __name__ == "__main__":
    unittest.main()

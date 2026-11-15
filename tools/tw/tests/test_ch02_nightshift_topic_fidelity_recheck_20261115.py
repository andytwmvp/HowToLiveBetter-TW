"""TW-02-039逐題恢復夜班心血管研究，保留研究及台灣統計限制。"""
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


BASE = "ebcc73397a206c2d4bc9e8dc4dab52189511a604"
DATE = "2026-11-15"
DUE = "2027-02-15"
ITEM_ID = "TW-02-039"
ARTICLE = "locales/zh-TW/book/ch02/TW-02-039.md"
BATCH_PATH = "localization/ch02-nightshift-topic-fidelity-recheck-20261115.json"
SOURCE_PATH = "localization/tw-edition/sources/ch02-nightshift-topic-fidelity-recheck-20261115.json"
REGISTER_PATH = "localization/retroactive-review-register-20261019.json"
REVIEW_PATH = f"localization/reviews/{ITEM_ID}.json"


def read(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def git_bytes(revision, path):
    return subprocess.check_output(["git", "show", f"{revision}:{path}"], cwd=ROOT)


def sha(data):
    return hashlib.sha256(data).hexdigest()


class NightshiftTopicFidelityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.runtime = validate_runtime()
        cls.items = {row["id"]: row for row in cls.runtime["items"]}
        cls.sources = {row["id"]: row for row in cls.runtime["sources"]}
        cls.manifest = {row["id"]: row for row in read("localization/manifest.json")["entries"]}
        cls.review = read(REVIEW_PATH)
        cls.batch = read(BATCH_PATH)
        cls.register = read(REGISTER_PATH)
        cls.coverage = read("localization/tw-edition/coverage.json")
        cls.bundle = read(SOURCE_PATH)
        cls.item = cls.items[ITEM_ID]
        cls.body_bytes = (ROOT / ARTICLE).read_bytes()
        cls.body = cls.body_bytes.decode("utf-8")
        cls.digest = sha(cls.body_bytes)
        cls.record = next(
            row for row in reversed(cls.register["substantive_rechecks"])
            if row["id"] == ITEM_ID and row["reviewed_at"] == DATE
        )

    def test_baseline_and_append_only_history_are_hash_bound(self):
        self.assertEqual(self.batch["baseline_main_sha"], BASE)
        self.assertEqual(self.batch["reviewed_at"], DATE)
        old_body = git_bytes(BASE, ARTICLE)
        old_review = git_bytes(BASE, REVIEW_PATH)
        self.assertEqual(self.record["prior_revision"], subprocess.check_output(
            ["git", "log", "-1", "--format=%H", BASE, "--", ARTICLE],
            cwd=ROOT,
            text=True,
        ).strip())
        self.assertEqual(self.record["before_sha256"], sha(old_body))
        self.assertEqual(self.record["previous_body"], old_body.decode("utf-8"))
        self.assertEqual(self.record["prior_review_sha256"], sha(old_review))
        self.assertEqual(self.record["prior_reviewed_at"], json.loads(old_review)["reviewed_at"])
        self.assertEqual(self.record["after_sha256"], self.digest)
        self.assertEqual(self.review["target_sha256"], self.digest)
        self.assertEqual(self.review["source_reviewed_sha256"], self.digest)
        self.assertEqual(self.record["review_sha256"], sha((ROOT / REVIEW_PATH).read_bytes()))
        self.assertEqual(self.record["source_bundle_sha256"], sha((ROOT / SOURCE_PATH).read_bytes()))
        self.assertEqual(self.review["review_due_at"], DUE)
        self.assertEqual(self.record["status"], "ai_source_rechecked_professional_pending")
        self.assertFalse(self.review["professional_review"]["obtained"])
        question_change = self.record["topic_fidelity_review"]["question_change"]
        self.assertEqual(question_change, self.review["topic_fidelity_review"]["question_change"])
        self.assertEqual(question_change, self.batch["item"]["topic_fidelity_question_change"])
        old_runtime = json.loads(git_bytes(BASE, "localization/tw-edition/runtime.json"))
        old_item = next(row for row in old_runtime["items"] if row["id"] == ITEM_ID)
        self.assertEqual(question_change["previous_question"], old_item["question"])
        self.assertEqual(question_change["current_question"], self.item["question"])
        baseline_register = json.loads(git_bytes(BASE, REGISTER_PATH))
        self.assertEqual(
            len(self.register["substantive_rechecks"]),
            len(baseline_register["substantive_rechecks"]) + 1,
        )

    def test_core_topic_is_restored_without_overstating_transfer_or_interventions(self):
        body = self.item["body"]
        self.assertEqual(self.manifest[ITEM_ID]["status"], "verified")
        self.assertEqual(self.item["title"], "夜班工作與心血管風險：看懂研究，安排健康管理")
        self.assertEqual(body, self.body)
        self.assertIn("2,891,280人", body)
        self.assertIn("638,255人", body)
        self.assertIn("相對風險（RR）估計為1.13", body)
        self.assertIn("死亡的RR估計為1.27", body)
        self.assertIn("每增加5年夜班暴露", body)
        self.assertIn("沒有台灣世代研究", body)
        self.assertIn("心血管疾病事件證據確定性為極低，死亡證據為低", body)
        self.assertIn("不能證明夜班單獨造成每個人的疾病", body)
        self.assertIn("沒有測試「轉職或調班」是否能降低", body)
        self.assertIn("不應把「越久就必須離職」當成個人醫療指令", body)
        self.assertIn("夜班津貼、收入、家庭照顧和通勤安排", body)
        self.assertIn("不能直接推算某一位台灣勞工會不會罹病", body)
        self.assertNotIn("7000到12000勒克斯", body)
        self.assertNotIn("乳腺癌", body)
        self.assertNotRegex(body, r"(批次摘要|本次.{0,12}(?:審查|再審|核對)|AI協助|PR\s*#|CI\s*(?:成功|通過))")

        decisions = self.review["topic_fidelity_review"]["historical_claim_decisions"]
        self.assertEqual(decisions[0]["decision"], "restore_with_scope_and_uncertainty")
        self.assertEqual(decisions[1]["decision"], "do_not_restore_as_universal_directive")
        self.assertEqual(decisions[2]["decision"], "not_restored_to_this_reader_body")
        self.assertTrue(all(
            row["disposition"] == "claim_removed_from_scope"
            and row["replacement_ids"] == []
            and re.fullmatch(r"[0-9a-f]{64}", row["prior_source_sha256"])
            for row in self.record["retired_sources"]
        ))
        self.assertIn("TW-19-010.md", body)
        self.assertIn("TW-19-012.md", body)

    def test_taiwan_survey_research_denominators_and_legal_dates_are_explicit(self):
        body = self.body
        self.assertIn("8.5%", body)
        self.assertIn("有效樣本4,029份", body)
        self.assertIn("114年5月", body)
        self.assertIn("原始人數、加權分母或信賴區間", body)
        self.assertIn("第2條所列「長期夜間工作」定義自2026年7月1日施行", body)
        self.assertIn("第18條規定的特定健康檢查則自2028年1月1日施行", body)

        stats = self.review["statistics_assessed"]
        self.assertEqual(len(stats), 4)
        self.assertEqual(stats[0]["value"], "8.5%")
        self.assertEqual(stats[1]["value"]["participants"], 2891280)
        self.assertEqual(stats[1]["value"]["relative_risk"], 1.13)
        self.assertEqual(stats[2]["value"]["participants"], 638255)
        self.assertEqual(stats[2]["value"]["relative_risk"], 1.27)
        for row in stats:
            for key in (
                "value", "unit", "period", "geographic_scope", "population", "numerator",
                "denominator", "event_definition", "data_type", "limitations", "source_ids",
            ):
                self.assertIn(key, row)
                self.assertTrue(row[key], (row.get("topic"), key))

        health_rule = self.sources["tw02_moj_labor_health_nightwork_2026"]
        self.assertEqual(health_rule["accessed_at"], DATE)
        self.assertIn("第2條長期夜間工作定義", health_rule["supports"])
        self.assertIn("自2026-07-01生效", health_rule["supports"])
        self.assertIn("第18條長期夜間工作特定健康檢查自2028-01-01生效", health_rule["supports"])
        self.assertIsNone(next((x for x in self.coverage["publication_blockers"] if x.startswith(f"{ITEM_ID}:")), None))

    def test_runtime_manifest_review_source_registry_and_reader_navigation_match(self):
        entry = self.manifest[ITEM_ID]
        self.assertEqual(entry["verified_at"], DATE)
        self.assertEqual(entry["sources"], self.item["source_ids"])
        self.assertEqual(self.item["body"], self.body)
        self.assertEqual((self.item["reviewed_at"], self.item["review_due_at"]), (DATE, DUE))
        self.assertEqual(self.review["source_ids"], self.item["source_ids"])
        self.assertEqual(self.review["source_checks"], self.record["source_checks"])
        self.assertEqual(self.review["statistics_assessed"], self.record["statistics_assessed"])
        self.assertEqual(self.review["target_path"], ARTICLE)
        self.assertEqual(self.record["source_ids"], self.item["source_ids"])
        self.assertEqual(self.record["previous_source_ids"], self.batch["item"]["previous_source_ids"])
        self.assertEqual(self.record["new_source_ids"], self.batch["new_source_ids"])
        self.assertEqual(self.batch["item"]["before_sha256"], self.record["before_sha256"])
        self.assertEqual(self.batch["item"]["after_sha256"], self.digest)

        urls = set(re.findall(r"\]\((https://[^)]+)\)", self.body))
        self.assertEqual(urls, {self.sources[sid]["url"] for sid in self.item["source_ids"]})
        source_checks = {row["source_id"]: row for row in self.review["source_checks"]}
        self.assertEqual(set(source_checks), set(self.item["source_ids"]))
        for sid in self.item["source_ids"]:
            self.assertLessEqual(self.sources[sid]["accessed_at"], DATE)
            self.assertEqual(source_checks[sid]["url"], self.sources[sid]["url"])

        self.assertEqual(self.bundle["checked_at"], DATE)
        self.assertEqual([row[0] for row in self.bundle["sources"]], self.batch["new_source_ids"])
        self.assertEqual(self.batch["updated_source_ids"], ["tw02_moj_labor_health_nightwork_2026"])
        chapter = (ROOT / "locales/zh-TW/book/ch02/README.md").read_text(encoding="utf-8")
        self.assertIn("夜班工作與心血管風險：看懂研究，安排健康管理](TW-02-039.md)", chapter)
        self.assertEqual(self.coverage, audit_drafts())
        self.assertFalse(self.coverage["publication_ready"])

        old_chapter = json.loads(git_bytes(BASE, "localization/tw-edition/chapters/02.json"))
        current_chapter = read("localization/tw-edition/chapters/02.json")
        old_row = next(row for row in old_chapter["entries"] if row[0] == 39)
        current_row = next(row for row in current_chapter["entries"] if row[0] == 39)
        self.assertEqual(current_row, old_row)

        baseline_runtime = json.loads(git_bytes(BASE, "localization/tw-edition/runtime.json"))
        baseline_coverage = json.loads(git_bytes(BASE, "localization/tw-edition/coverage.json"))
        baseline_register = json.loads(git_bytes(BASE, REGISTER_PATH))
        self.assertEqual(
            self.batch["counts_before"],
            {
                "verified_core": baseline_coverage["core_reviewed_entries"],
                "runtime_items": len(baseline_runtime["items"]),
                "runtime_sources": len(baseline_runtime["sources"]),
                "source_registry": baseline_coverage["registry_sources"],
                "review_rechecks": len(baseline_register["substantive_rechecks"]),
            },
        )

        previous_batch = read("localization/topic-fidelity-stream-licensing-recheck-20261115.json")
        previous = previous_batch["counts_after"]
        self.assertEqual(
            self.batch["counts_before"],
            {
                "verified_core": previous["verified_core_entries"],
                "runtime_items": previous["runtime_items"],
                "runtime_sources": previous["runtime_sources"],
                "source_registry": previous["source_registry"],
                "review_rechecks": previous["review_rechecks"],
            },
        )
        self.assertEqual(
            self.batch["counts_after"],
            {
                "verified_core": self.coverage["core_reviewed_entries"],
                "runtime_items": len(self.runtime["items"]),
                "runtime_sources": len(self.runtime["sources"]),
                "source_registry": self.coverage["registry_sources"],
                "review_rechecks": len(self.register["substantive_rechecks"]),
            },
        )
        self.assertEqual(self.batch["counts_after"]["verified_core"], self.batch["counts_before"]["verified_core"])
        self.assertEqual(self.batch["counts_after"]["runtime_items"], self.batch["counts_before"]["runtime_items"])
        self.assertEqual(self.batch["counts_after"]["runtime_sources"], self.batch["counts_before"]["runtime_sources"] + len(self.batch["new_source_ids"]))
        self.assertEqual(self.batch["counts_after"]["source_registry"], self.batch["counts_before"]["source_registry"] + len(self.batch["new_source_ids"]))
        self.assertEqual(self.batch["counts_after"]["review_rechecks"], self.batch["counts_before"]["review_rechecks"] + 1)


if __name__ == "__main__":
    unittest.main()

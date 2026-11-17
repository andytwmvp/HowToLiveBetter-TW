"""第2章室內燃燒主題忠實度與研究情境回歸測試。"""
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

BASE = "213cf4f0afc0be4b0d264ffe583676564bd51cae"
DATE = "2026-11-17"
DUE = "2027-02-17"
ITEM_ID = "TW-02-029"
ARTICLE = "locales/zh-TW/book/ch02/TW-02-029.md"
REVIEW = f"localization/reviews/{ITEM_ID}.json"
REGISTER = "localization/retroactive-review-register-20261019.json"
BATCH = "localization/ch02-co-fuel-topic-fidelity-recheck-20261117.json"
BUNDLE = "localization/tw-edition/sources/ch02-co-fuel-topic-fidelity-recheck-20261117.json"
NEW_SOURCE_IDS = {
    "tw02_jama_solid_fuel_china_mortality_2018",
    "tw02_taiwan_pm_exposure_cooking_2021",
    "tw02_moeaea_energy_consumption_2026",
}


def read_json(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def git_bytes(revision, path):
    return subprocess.check_output(["git", "show", f"{revision}:{path}"], cwd=ROOT)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def added_revision(path):
    revisions = subprocess.run(
        ["git", "log", "--diff-filter=A", "--format=%H", "--", path],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.splitlines()
    return revisions[0] if revisions else None


class CoFuelTopicFidelityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.batch_revision = added_revision(BATCH)

        def at_batch(path):
            if cls.batch_revision:
                return git_bytes(cls.batch_revision, path)
            return (ROOT / path).read_bytes()

        cls.article_bytes = (ROOT / ARTICLE).read_bytes()
        cls.article = cls.article_bytes.decode("utf-8")
        cls.review_bytes = (ROOT / REVIEW).read_bytes()
        cls.review = json.loads(cls.review_bytes)
        cls.batch_bytes = at_batch(BATCH)
        cls.batch = json.loads(cls.batch_bytes)
        cls.bundle_bytes = at_batch(BUNDLE)
        cls.bundle = json.loads(cls.bundle_bytes)
        cls.runtime = validate_runtime()
        cls.current_item = next(x for x in cls.runtime["items"] if x["id"] == ITEM_ID)
        cls.current_sources = {x["id"]: x for x in cls.runtime["sources"]}
        cls.snapshot_runtime = json.loads(at_batch("localization/tw-edition/runtime.json"))
        cls.snapshot_manifest = json.loads(at_batch("localization/manifest.json"))
        cls.snapshot_coverage = json.loads(at_batch("localization/tw-edition/coverage.json"))
        cls.snapshot_register = json.loads(at_batch(REGISTER))
        cls.current_register = read_json(REGISTER)
        cls.snapshot_item = next(x for x in cls.snapshot_runtime["items"] if x["id"] == ITEM_ID)
        cls.snapshot_manifest_item = next(
            x for x in cls.snapshot_manifest["entries"] if x["id"] == ITEM_ID
        )
        cls.history = next(
            x for x in reversed(cls.snapshot_register["substantive_rechecks"])
            if x["id"] == ITEM_ID and x["reviewed_at"] == DATE
        )
        cls.current_history = next(
            x for x in reversed(cls.current_register["substantive_rechecks"])
            if x["id"] == ITEM_ID and x["reviewed_at"] == DATE
        )
        cls.batch_item = next(x for x in cls.batch["items"] if x["id"] == ITEM_ID)

    def test_review_history_is_append_only_and_hash_linked(self):
        self.assertEqual(self.batch["baseline_main_sha"], BASE)
        self.assertEqual(self.batch["reviewed_at"], DATE)
        self.assertEqual(self.batch["review_due_at"], DUE)

        prior_body = git_bytes(BASE, ARTICLE)
        prior_review_bytes = git_bytes(BASE, REVIEW)
        prior_review = json.loads(prior_review_bytes)
        prior_runtime = json.loads(git_bytes(BASE, "localization/tw-edition/runtime.json"))
        prior_item = next(x for x in prior_runtime["items"] if x["id"] == ITEM_ID)
        baseline_register = json.loads(git_bytes(BASE, REGISTER))["substantive_rechecks"]
        current_register = self.current_register["substantive_rechecks"]

        self.assertEqual(current_register[:len(baseline_register)], baseline_register)
        self.assertEqual(self.history["previous_body"].encode("utf-8"), prior_body)
        self.assertEqual(self.history["previous_review_snapshot"], prior_review)
        self.assertEqual(self.history["before_sha256"], digest(prior_body))
        self.assertEqual(self.history["prior_review_sha256"], digest(prior_review_bytes))
        self.assertEqual(self.history["previous_title"], prior_item["title"])
        self.assertEqual(self.history["previous_question"], prior_item["question"])
        self.assertEqual(self.history["after_sha256"], digest(self.article_bytes))
        self.assertEqual(self.review["target_sha256"], digest(self.article_bytes))
        self.assertEqual(self.review["source_reviewed_sha256"], digest(self.article_bytes))
        self.assertEqual(self.history["review_sha256"], digest(self.review_bytes))
        self.assertEqual(self.batch_item["review_sha256"], digest(self.review_bytes))
        self.assertEqual(self.history["source_bundle_sha256"], digest(self.bundle_bytes))
        self.assertEqual(self.batch_item["source_bundle_sha256"], digest(self.bundle_bytes))
        self.assertEqual(self.review["source_bundle_sha256"], digest(self.bundle_bytes))
        self.assertEqual(self.history, self.current_history)
        self.assertEqual(self.history["status"], "ai_source_rechecked_professional_pending")
        self.assertTrue(self.review["professional_review"]["required"])
        self.assertFalse(self.review["professional_review"]["obtained"])
        self.assertEqual(self.review["source_checks"], self.history["source_checks"])
        self.assertEqual(self.review["statistics_assessed"], self.history["statistics_assessed"])
        self.assertEqual(self.review["topic_fidelity_review"], self.history["topic_fidelity_review"])

    def test_original_research_question_and_taiwan_case_context_are_preserved(self):
        required = (
            "271,217名", "15,468人死亡", "5,519人死於心血管疾病",
            "338（249至427）", "135（77至193）", "392（297至487）", "175（118至231）",
            "150,992人、比較組26,559人", "73.3及76.5", "麵包店工作約145分鐘", "183.8",
            "不能據此判斷哪種燃料較安全", "目前未找到可代表全臺家戶",
        )
        for phrase in required:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, self.article)

        self.assertIn("先離開至戶外安全處，再撥119", self.article)
        self.assertIn("不要進入疑似有毒氣體的空間救人", self.article)
        self.assertNotIn("使用固體燃料與未使用固體燃料的烹調事件", self.article)
        self.assertEqual(self.current_item["body"].encode("utf-8"), self.article_bytes)
        self.assertEqual(self.current_item["title"], "室內燃燒與健康：一氧化碳安全及固體燃料研究")
        self.assertEqual(self.snapshot_item["source_ids"], self.review["source_ids"])
        self.assertEqual(self.snapshot_manifest_item["sources"], self.review["source_ids"])
        self.assertEqual(self.snapshot_manifest_item["verified_at"], DATE)
        self.assertTrue(self.review["topic_fidelity_review"]["reader_content_decision"])
        self.assertTrue(self.review["professional_review"]["required"])
        self.assertFalse(self.review["professional_review"]["obtained"])

        for statistic in self.review["statistics_assessed"]:
            for field in (
                "value", "unit", "period", "geographic_scope", "population", "numerator",
                "denominator", "denominator_definition", "event_definition", "data_type",
                "limitations", "source_ids", "accessed_at",
            ):
                self.assertTrue(statistic.get(field), (statistic.get("topic"), field))
            self.assertLessEqual(statistic["accessed_at"], DATE)

    def test_fuel_research_data_remains_consistent_across_exports(self):
        source_ids = set(self.review["source_ids"])
        checks_by_id = {x["source_id"]: x for x in self.review["source_checks"]}
        source_map = self.current_sources
        bundled_ids = {row[0] for row in self.bundle["sources"]}
        self.assertEqual(set(self.current_item["source_ids"]), source_ids)
        self.assertEqual(set(self.snapshot_manifest_item["sources"]), source_ids)
        self.assertTrue(source_ids.issubset(set(source_map)))
        self.assertEqual(source_ids, set(checks_by_id))
        self.assertEqual(self.bundle["checked_at"], DATE)
        self.assertEqual(bundled_ids, NEW_SOURCE_IDS)
        self.assertEqual(set(self.batch["new_source_ids"]), NEW_SOURCE_IDS)
        self.assertEqual(NEW_SOURCE_IDS, set(self.batch["new_source_ids"]))
        self.assertIn("一家住家式烤鴨店", source_map["tw02_taiwan_pm_exposure_cooking_2021"]["supports"])
        self.assertIn("住宅部門604萬公噸油當量", source_map["tw02_moeaea_energy_consumption_2026"]["supports"])

        chapter = read_json("localization/tw-edition/chapters/02.json")
        chapter_row = next(x for x in chapter["entries"] if x[0] == 29)
        self.assertEqual(chapter_row[1], self.current_item["title"])
        self.assertEqual(set(chapter_row[5].split()), source_ids)
        readme = (ROOT / "locales/zh-TW/book/ch02/README.md").read_text(encoding="utf-8")
        self.assertIn(self.current_item["title"], readme)
        self.assertEqual(read_json("localization/tw-edition/coverage.json"), audit_drafts())

        prior_runtime = json.loads(git_bytes(BASE, "localization/tw-edition/runtime.json"))
        prior_item = next(x for x in prior_runtime["items"] if x["id"] == ITEM_ID)
        self.assertTrue(documented_revision(prior_item, self.snapshot_item, self.history))

    def test_counts_record_only_real_additions_and_preserve_publication_gate(self):
        old_manifest = json.loads(git_bytes(BASE, "localization/manifest.json"))
        old_runtime = json.loads(git_bytes(BASE, "localization/tw-edition/runtime.json"))
        old_coverage = json.loads(git_bytes(BASE, "localization/tw-edition/coverage.json"))
        old_register = json.loads(git_bytes(BASE, REGISTER))
        before, after = self.batch["counts_before"], self.batch["counts_after"]

        self.assertEqual(before["manifest_entries"], len(old_manifest["entries"]))
        self.assertEqual(before["runtime_items"], len(old_runtime["items"]))
        self.assertEqual(before["runtime_sources"], len(old_runtime["sources"]))
        self.assertEqual(before["source_registry"], old_coverage["registry_sources"])
        self.assertEqual(before["coverage_json_files"], old_coverage["json_files_checked"])
        self.assertEqual(before["review_rechecks"], len(old_register["substantive_rechecks"]))
        self.assertEqual(after["runtime_sources"], before["runtime_sources"] + 3)
        self.assertEqual(after["source_registry"], before["source_registry"] + 3)
        self.assertEqual(after["coverage_json_files"], before["coverage_json_files"] + 2)
        self.assertEqual(after["review_rechecks"], before["review_rechecks"] + 1)
        self.assertEqual(after["runtime_items"], before["runtime_items"])
        self.assertEqual(after["verified_core_entries"], before["verified_core_entries"])
        self.assertEqual(after["publication_completed_entries"], before["publication_completed_entries"])
        self.assertFalse(before["publication_ready"])
        self.assertFalse(after["publication_ready"])
        self.assertEqual(len(self.snapshot_register["substantive_rechecks"]), after["review_rechecks"])
        self.assertEqual(len(self.snapshot_runtime["sources"]), after["runtime_sources"])
        self.assertEqual(self.snapshot_coverage["registry_sources"], after["source_registry"])
        self.assertEqual(self.snapshot_coverage["json_files_checked"], after["coverage_json_files"])


if __name__ == "__main__":
    unittest.main()

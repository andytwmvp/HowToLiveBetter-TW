"""TW-02-022／023逐題恢復有價值研究並維持台灣內容邊界。"""
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


BASE = "96b871f6f87b3c15fd673bcf7ec9e47a63bc2a65"
DATE = "2026-11-16"
DUE = "2027-02-16"
REGISTER = "localization/retroactive-review-register-20261019.json"
BATCH = "localization/ch02-nut-meat-topic-fidelity-recheck-20261116.json"
SOURCE_BUNDLE = "localization/tw-edition/sources/ch02-nut-meat-topic-fidelity-recheck-20261116.json"
ITEMS = {
    "TW-02-022": "locales/zh-TW/book/ch02/TW-02-022.md",
    "TW-02-023": "locales/zh-TW/book/ch02/TW-02-023.md",
}
NEW_SOURCES = {
    "tw02_hpa_cvd_prevention_guideline_nuts_2020",
    "tw02_bao_nut_mortality_2013",
    "tw02_liu_nut_mortality_meta_2026",
    "tw02_zhong_meat_mortality_2020",
    "tw02_nielsen_meat_substitution_2022",
}


def read_json(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def git_bytes(revision, path):
    return subprocess.check_output(["git", "show", f"{revision}:{path}"], cwd=ROOT)


def digest(data):
    return hashlib.sha256(data).hexdigest()


class NutMeatTopicFidelityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.runtime = validate_runtime()
        cls.items = {row["id"]: row for row in cls.runtime["items"]}
        cls.sources = {row["id"]: row for row in cls.runtime["sources"]}
        cls.manifest = {row["id"]: row for row in read_json("localization/manifest.json")["entries"]}
        cls.coverage = read_json("localization/tw-edition/coverage.json")
        cls.register = read_json(REGISTER)
        cls.batch = read_json(BATCH)
        cls.bundle = read_json(SOURCE_BUNDLE)
        cls.articles = {item_id: (ROOT / path).read_bytes() for item_id, path in ITEMS.items()}
        cls.rows = {
            item_id: next(row for row in reversed(cls.register["substantive_rechecks"])
                          if row["id"] == item_id and row["reviewed_at"] == DATE)
            for item_id in ITEMS
        }
        cls.reviews = {item_id: read_json(f"localization/reviews/{item_id}.json") for item_id in ITEMS}
        cls.batch_items = {row["id"]: row for row in cls.batch["items"]}

    def test_review_hashes_and_register_history_are_append_only(self):
        self.assertEqual(self.batch["baseline_main_sha"], BASE)
        self.assertEqual(self.batch["reviewed_at"], DATE)
        self.assertEqual(self.batch["review_due_at"], DUE)
        baseline_register = json.loads(git_bytes(BASE, REGISTER))
        rows_before = baseline_register["substantive_rechecks"]
        self.assertEqual(self.register["substantive_rechecks"][:len(rows_before)], rows_before)

        for item_id, article_path in ITEMS.items():
            row = self.rows[item_id]
            review_path = f"localization/reviews/{item_id}.json"
            old_body = git_bytes(BASE, article_path)
            old_review = git_bytes(BASE, review_path)
            review = self.reviews[item_id]
            self.assertEqual(row["prior_revision"], subprocess.check_output(
                ["git", "log", "-1", "--format=%H", BASE, "--", article_path],
                cwd=ROOT, text=True,
            ).strip())
            self.assertEqual(row["before_sha256"], digest(old_body))
            self.assertEqual(row["previous_body"], old_body.decode("utf-8"))
            self.assertEqual(row["prior_review_sha256"], digest(old_review))
            self.assertEqual(row["previous_review_snapshot"], json.loads(old_review))
            self.assertEqual(row["after_sha256"], digest(self.articles[item_id]))
            self.assertEqual(review["target_sha256"], digest(self.articles[item_id]))
            self.assertEqual(review["source_reviewed_sha256"], digest(self.articles[item_id]))
            self.assertEqual(row["review_sha256"], digest((ROOT / review_path).read_bytes()))
            self.assertEqual(review["source_bundle_sha256"], digest((ROOT / SOURCE_BUNDLE).read_bytes()))
            self.assertEqual(row["source_bundle_sha256"], review["source_bundle_sha256"])
            self.assertEqual(row["source_checks"], review["source_checks"])
            self.assertEqual(row["statistics_assessed"], review["statistics_assessed"])
            self.assertEqual(row["topic_fidelity_review"], review["topic_fidelity_review"])
            self.assertEqual(row["status"], "ai_source_rechecked_professional_pending")
            self.assertTrue(review["professional_review"]["required"])
            self.assertFalse(review["professional_review"]["obtained"])

        appended = self.register["substantive_rechecks"][len(rows_before):]
        self.assertEqual(
            {row["id"] for row in appended if row["reviewed_at"] == DATE}, set(ITEMS)
        )
        for item_id in ITEMS:
            self.assertEqual(self.reviews[item_id]["source_checks"], self.rows[item_id]["source_checks"])

    def test_taiwan_guideline_restores_nut_research_question_with_limits(self):
        item_id = "TW-02-022"
        body = self.articles[item_id].decode("utf-8")
        item = self.items[item_id]
        review = self.reviews[item_id]
        self.assertEqual(item["body"], body)
        self.assertEqual(self.manifest[item_id]["status"], "verified")
        self.assertEqual(self.manifest[item_id]["verified_at"], DATE)
        self.assertEqual(self.manifest[item_id]["sources"], item["source_ids"])
        self.assertIn("2020年《心血管疾病預防照護指引》", body)
        self.assertIn("沒有指定某一種堅果或預防疾病所需的克數", body)
        self.assertIn("3,038,853人年", body)
        self.assertIn("27,429人死亡", body)
        self.assertIn("HR）為0.80（95%信賴區間0.73至0.86", body)
        self.assertIn("63個前瞻性世代研究", body)
        self.assertIn("劑量反應呈非線性", body)
        self.assertIn("不是個人死亡機率下降20%", body)
        self.assertNotIn("2026-11-16安全再審", body)
        self.assertNotIn("AI來源核對", body)
        self.assertNotIn("待專業審閱", body)
        self.assertFalse(self.coverage["publication_ready"])

        check = next(row for row in review["source_checks"]
                     if row["source_id"] == "tw02_hpa_cvd_prevention_guideline_nuts_2020")
        self.assertIn("第160頁", check["supporting_passage"])
        self.assertIn("官方PDF直連本輪回應逾時", check["retrieval_method"])
        guideline = self.sources[check["source_id"]]
        self.assertIsNone(guideline["published_at"])
        self.assertIn("2020年4月出版", guideline["supports"])
        self.assertEqual(guideline["accessed_at"], DATE)
        self.assertEqual(guideline["url"], check["url"])

        stats = review["statistics_assessed"]
        self.assertEqual(len(stats), 2)
        self.assertEqual(stats[0]["value"]["participants"], 118962)
        self.assertEqual(stats[0]["value"]["person_years"], 3038853)
        self.assertEqual(stats[0]["value"]["all_cause_deaths"], 27429)
        self.assertIn("每週7次以上及從未攝取組的各自分母", stats[0]["denominator"])
        self.assertEqual(stats[1]["value"]["prospective_cohort_studies"], 63)
        self.assertIn("共同分母", stats[1]["denominator"])

    def test_meat_replacement_research_keeps_two_designs_separate(self):
        item_id = "TW-02-023"
        body = self.articles[item_id].decode("utf-8")
        item = self.items[item_id]
        review = self.reviews[item_id]
        self.assertEqual(item["body"], body)
        self.assertEqual(self.manifest[item_id]["sources"], item["source_ids"])
        self.assertIn("29,682名成人", body)
        self.assertIn("沒有直接測試把同份量紅肉換成魚或禽肉", body)
        self.assertIn("57,053名50至64歲成人", body)
        self.assertIn("觀察資料的替代模型", body)
        self.assertIn("沒有台灣資料可精確估算", body)
        self.assertEqual(len(review["statistics_assessed"]), 2)
        self.assertEqual(review["statistics_assessed"][0]["value"]["all_cause_deaths"], 8875)
        self.assertEqual(review["statistics_assessed"][0]["value"]["incident_cvd_events"], 6963)
        self.assertEqual(review["statistics_assessed"][1]["value"]["all_cause_deaths"], 8840)
        self.assertIn("加工肉", body)
        self.assertIn("未加工紅肉", body)
        self.assertIn("蛋白質需求", body)

    def test_runtime_manifest_sources_and_limits_are_exact(self):
        baseline_runtime = json.loads(git_bytes(BASE, "localization/tw-edition/runtime.json"))
        baseline_source_ids = {row["id"] for row in baseline_runtime["sources"]}
        current_source_ids = set(self.sources)
        self.assertEqual(set(self.batch["new_source_ids"]), NEW_SOURCES)
        self.assertEqual({row[0] for row in self.bundle["sources"]}, NEW_SOURCES)
        self.assertTrue(NEW_SOURCES.isdisjoint(baseline_source_ids))
        self.assertTrue(NEW_SOURCES.issubset(current_source_ids))
        self.assertEqual(self.bundle["checked_at"], DATE)

        for item_id in ITEMS:
            item = self.items[item_id]
            review = self.reviews[item_id]
            row = self.rows[item_id]
            manifest = self.manifest[item_id]
            batch_item = self.batch_items[item_id]
            self.assertEqual(item["source_ids"], review["source_ids"])
            self.assertEqual(item["source_ids"], row["source_ids"])
            self.assertEqual(item["source_ids"], manifest["sources"])
            self.assertEqual(item["source_ids"], batch_item["source_ids"])
            self.assertEqual(item["limits"], " ".join(review["limits"]))
            self.assertTrue(documented_revision(
                next(x for x in baseline_runtime["items"] if x["id"] == item_id),
                item,
                row,
            ))
            check_ids = {check["source_id"] for check in review["source_checks"]}
            self.assertEqual(check_ids, set(item["source_ids"]))
            self.assertTrue(check_ids.issubset(self.sources))
            self.assertEqual(batch_item["review_sha256"], row["review_sha256"])
            for source_id in item["source_ids"]:
                self.assertIn(source_id, self.sources)

        audit = audit_drafts()
        self.assertEqual(audit, self.coverage)
        self.assertGreaterEqual(audit["json_files_checked"], self.batch["counts_after"]["coverage_json_files"])
        self.assertGreaterEqual(len(self.runtime["items"]), self.batch["counts_after"]["runtime_items"])
        self.assertGreaterEqual(len(self.runtime["sources"]), self.batch["counts_after"]["runtime_sources"])
        self.assertGreaterEqual(audit["registry_sources"], self.batch["counts_after"]["source_registry"])
        self.assertEqual(self.batch["counts_after"]["review_rechecks"],
                         self.batch["counts_before"]["review_rechecks"] + 2)
        self.assertGreaterEqual(
            len(self.register["substantive_rechecks"]),
            self.batch["counts_after"]["review_rechecks"],
        )
        self.assertFalse(self.batch["counts_after"]["publication_ready"])


if __name__ == "__main__":
    unittest.main()

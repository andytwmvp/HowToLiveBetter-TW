"""TW-02-026保留有讀者價值的咖啡健康研究，並限制因果推論。"""
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


BASE = "93b22b66bf16ba0ccef10919e826e586ce6abb12"
DATE = "2026-11-15"
DUE = "2027-02-15"
ITEM_ID = "TW-02-026"
ARTICLE = f"locales/zh-TW/book/ch02/{ITEM_ID}.md"
BATCH_PATH = "localization/ch02-coffee-topic-fidelity-recheck-20261115.json"
SOURCE_PATH = "localization/tw-edition/sources/ch02-coffee-topic-fidelity-recheck-20261115.json"
REGISTER_PATH = "localization/retroactive-review-register-20261019.json"
REVIEW_PATH = f"localization/reviews/{ITEM_ID}.json"


def read(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def git_bytes(revision, path):
    return subprocess.check_output(["git", "show", f"{revision}:{path}"], cwd=ROOT)


def sha(data):
    return hashlib.sha256(data).hexdigest()


class CoffeeTopicFidelityTests(unittest.TestCase):
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
            ["git", "log", "-1", "--format=%H", BASE, "--", ARTICLE], cwd=ROOT, text=True
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
        old_register = json.loads(git_bytes(BASE, REGISTER_PATH))
        self.assertEqual(
            len(self.register["substantive_rechecks"]),
            len(old_register["substantive_rechecks"]) + 1,
        )

    def test_reader_keeps_relevant_research_without_turning_it_into_a_prescription(self):
        self.assertEqual(self.manifest[ITEM_ID]["status"], "verified")
        self.assertEqual(self.item["title"], "咖啡因看總量：咖啡與長期健康研究怎麼看")
        self.assertEqual(self.item["body"], self.body)
        self.assertIn("全因死亡的彙整相對風險為0.83（95%信賴區間0.79至0.88", self.body)
        self.assertIn("日本八個人口世代研究合併分析納入313,381人", self.body)
        self.assertIn("另一個日本12個社區的世代研究納入9,946人", self.body)
        self.assertIn("沒有發現咖啡攝取與全因死亡有顯著關聯", self.body)
        self.assertIn("台灣也有以基隆、竹南、彰化和臺東社區篩檢資料", self.body)
        self.assertIn("不把模型推估值寫成喝咖啡能多活幾年", self.body)
        self.assertIn("上午型相較不喝咖啡的全因死亡危險比為0.84", self.body)
        self.assertIn("不能證明把咖啡改到上午就會延壽", self.body)
        self.assertIn("復發為47/100人與64/100人", self.body)
        self.assertIn("不能推成咖啡可預防或治療心房顫動", self.body)
        self.assertIn("成人每日咖啡因不宜超過300毫克", self.body)
        self.assertIn("台灣官方資料對孕期建議並不一致", self.body)
        self.assertNotRegex(self.body, r"(批次摘要|本次.{0,12}(?:審查|再審|核對)|AI協助|PR\s*#|CI\s*(?:成功|通過))")

        decisions = self.review["topic_fidelity_review"]["historical_claim_decisions"]
        self.assertEqual(decisions[1]["decision"], "bounded_reader_restoration_with_corrected_relative_estimate")
        self.assertEqual(decisions[3]["decision"], "bounded_restoration_from_randomized_trial_for_selected_patients_only")
        self.assertEqual(decisions[4]["decision"], "not_restored_as_a_longevity_rule")
        self.assertTrue(self.review["professional_review"]["required"])

    def test_statistics_show_populations_denominators_and_limits(self):
        stats = self.review["statistics_assessed"]
        self.assertEqual(len(stats), 6)
        self.assertEqual(stats[0]["value"]["relative_risk"], 0.83)
        self.assertEqual(stats[0]["value"]["95_confidence_interval"], [0.79, 0.88])
        self.assertEqual(stats[1]["value"]["participants"], 313381)
        self.assertEqual(stats[1]["value"]["all_cause_deaths"], 52943)
        self.assertEqual(stats[2]["value"]["participants"], 9946)
        self.assertEqual(stats[3]["denominator"], "可公開摘要未列咖啡分析的有效樣本分母；全文需進一步查閱，本次國圖紀錄遭圖形驗證阻擋")
        self.assertEqual(stats[4]["value"]["group_events"], {
            "noncoffee": "1484/19593", "morning": "1872/14643", "all_day": "939/6489"
        })
        self.assertEqual(stats[5]["value"]["coffee_group_recurrence"], "47/100")
        for row in stats:
            for key in (
                "value", "unit", "period", "geographic_scope", "population", "numerator",
                "denominator", "event_definition", "data_type", "limitations", "source_ids",
            ):
                self.assertIn(key, row)
                self.assertTrue(row[key], (row.get("topic"), key))
        self.assertIn("未能檢視全文", self.review["unresolved_questions"][1])

    def test_runtime_manifest_sources_coverage_and_chapter_index_match(self):
        entry = self.manifest[ITEM_ID]
        self.assertEqual(entry["verified_at"], DATE)
        self.assertEqual(entry["sources"], self.item["source_ids"])
        self.assertEqual(self.item["body"], self.body)
        self.assertEqual((self.item["reviewed_at"], self.item["review_due_at"]), (DATE, DUE))
        self.assertEqual(self.review["source_ids"], self.item["source_ids"])
        self.assertEqual(self.record["source_checks"], self.review["source_checks"])
        self.assertEqual(self.record["statistics_assessed"], self.review["statistics_assessed"])
        self.assertEqual(self.record["source_ids"], self.item["source_ids"])
        self.assertEqual(self.item["title"], self.record["title"])

        urls = set(re.findall(r"\]\((https://[^)]+)\)", self.body))
        self.assertEqual(urls, {self.sources[source_id]["url"] for source_id in self.item["source_ids"]})
        checks = {row["source_id"]: row for row in self.review["source_checks"]}
        self.assertEqual(set(checks), set(self.item["source_ids"]))
        for source_id in self.item["source_ids"]:
            self.assertEqual(checks[source_id]["url"], self.sources[source_id]["url"])
            self.assertLessEqual(checks[source_id]["accessed_at"], DATE)

        self.assertEqual(self.bundle["checked_at"], DATE)
        self.assertEqual([row[0] for row in self.bundle["sources"]], self.batch["new_source_ids"])
        self.assertEqual(self.batch["updated_source_ids"], [])
        index = (ROOT / "locales/zh-TW/book/ch02/README.md").read_text(encoding="utf-8")
        self.assertIn("咖啡因看總量：咖啡與長期健康研究怎麼看](TW-02-026.md)", index)
        self.assertEqual(self.coverage, audit_drafts())
        self.assertFalse(self.coverage["publication_ready"])

        old_runtime = json.loads(git_bytes(BASE, "localization/tw-edition/runtime.json"))
        old_coverage = json.loads(git_bytes(BASE, "localization/tw-edition/coverage.json"))
        old_register = json.loads(git_bytes(BASE, REGISTER_PATH))
        self.assertEqual(self.batch["counts_before"]["verified_core_entries"], old_coverage["core_reviewed_entries"])
        self.assertEqual(self.batch["counts_before"]["runtime_items"], len(old_runtime["items"]))
        self.assertEqual(self.batch["counts_before"]["runtime_sources"], len(old_runtime["sources"]))
        self.assertEqual(self.batch["counts_before"]["review_rechecks"], len(old_register["substantive_rechecks"]))
        after = self.batch["counts_after"]
        self.assertEqual(after["verified_core_entries"], old_coverage["core_reviewed_entries"])
        self.assertEqual(after["runtime_items"], len(old_runtime["items"]))
        self.assertEqual(after["runtime_sources"], len(old_runtime["sources"]) + len(self.batch["new_source_ids"]))
        self.assertEqual(after["source_registry"], old_coverage["registry_sources"] + len(self.batch["new_source_ids"]))
        self.assertEqual(after["coverage_json_files"], old_coverage["json_files_checked"] + 2)
        self.assertEqual(after["review_rechecks"], len(old_register["substantive_rechecks"]) + 1)
        self.assertEqual(self.coverage["core_reviewed_entries"], self.coverage["publication_completed_entries"])

        old_chapter = json.loads(git_bytes(BASE, "localization/tw-edition/chapters/02.json"))
        current_chapter = read("localization/tw-edition/chapters/02.json")
        self.assertEqual(
            next(row for row in current_chapter["entries"] if row[0] == 26),
            next(row for row in old_chapter["entries"] if row[0] == 26),
        )


if __name__ == "__main__":
    unittest.main()

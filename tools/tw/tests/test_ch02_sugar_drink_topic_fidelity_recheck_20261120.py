"""含糖飲料歷史主題回補的來源、統計界線與正式閱讀資料契約。"""
import hashlib
import json
import re
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from review_contract import ROOT, validate_runtime

BASELINE = "f1c1579dbab76b12fc72a4243f9bbf3f40b2ad3f"
ITEM_ID = "TW-02-007"
REVIEW_DATE = "2026-11-20"
TARGET = "locales/zh-TW/book/ch02/TW-02-007.md"
BATCH = "localization/ch02-sugar-drink-topic-fidelity-recheck-20261120.json"
SOURCE_BUNDLE = "localization/tw-edition/sources/ch02-sugar-drink-topic-fidelity-recheck-20261120.json"
NEW_SOURCE_IDS = {
    "tw02_malik_us_mortality_2019",
    "tw02_mullee_epic_mortality_2019",
    "tw02_chen_asb_mortality_meta_2024",
    "tw02_mcglynn_lncsb_replacement_rct_2022",
    "tw02_who_nss_guideline_2023",
    "tw02_nahsit_ssb_analysis_2017_2020_2026",
    "tw02_tfda_nutrition_label_rules_2024",
}


def read_json(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def base_json(path):
    return json.loads(subprocess.check_output(
        ["git", "show", f"{BASELINE}:{path}"], cwd=ROOT, text=True
    ))


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


class SugarDrinkTopicFidelityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.runtime = validate_runtime()
        cls.items = {row["id"]: row for row in cls.runtime["items"]}
        cls.sources = {row["id"]: row for row in cls.runtime["sources"]}
        cls.manifest = {row["id"]: row for row in read_json("localization/manifest.json")["entries"]}
        cls.review = read_json("localization/reviews/TW-02-007.json")
        cls.register = read_json("localization/retroactive-review-register-20261019.json")
        cls.batch = read_json(BATCH)
        cls.bundle = read_json(SOURCE_BUNDLE)
        cls.article = (ROOT / TARGET).read_text(encoding="utf-8")
        cls.article_sha = digest((ROOT / TARGET).read_bytes())
        cls.item_rechecks = [row for row in cls.register["substantive_rechecks"] if row["id"] == ITEM_ID]
        cls.batch_recheck = next(row for row in cls.item_rechecks if row["reviewed_at"] == REVIEW_DATE)
        cls.latest_recheck = cls.item_rechecks[-1]

    def test_original_topic_and_previous_review_are_retained_append_only(self):
        base_register = base_json("localization/retroactive-review-register-20261019.json")
        current_rows = self.register["substantive_rechecks"]
        base_rows = base_register["substantive_rechecks"]
        self.assertEqual(current_rows[:len(base_rows)], base_rows)

        base_body = subprocess.check_output(["git", "show", f"{BASELINE}:{TARGET}"], cwd=ROOT)
        base_review_raw = subprocess.check_output(
            ["git", "show", f"{BASELINE}:localization/reviews/TW-02-007.json"], cwd=ROOT
        )
        base_manifest = base_json("localization/manifest.json")
        old_manifest_item = next(row for row in base_manifest["entries"] if row["id"] == ITEM_ID)
        self.assertEqual(self.batch_recheck["before_sha256"], digest(base_body))
        self.assertEqual(self.batch_recheck["previous_body"].encode("utf-8"), base_body)
        self.assertEqual(self.batch_recheck["prior_review_sha256"], digest(base_review_raw))
        self.assertEqual(self.batch_recheck["previous_source_ids"], old_manifest_item["sources"])
        self.assertEqual(self.batch_recheck["source_ids"][:3], self.batch_recheck["previous_source_ids"])
        self.assertTrue(NEW_SOURCE_IDS.issubset(set(self.batch_recheck["source_ids"])))
        self.assertEqual(self.batch_recheck["source_bundle_sha256"], digest((ROOT / SOURCE_BUNDLE).read_bytes()))
        self.assertEqual(self.batch_recheck["review_sha256"], digest((ROOT / "localization/reviews/TW-02-007.json").read_bytes()))
        self.assertEqual(self.batch_recheck["status"], "ai_source_rechecked_professional_pending")
        self.assertFalse(self.batch_recheck["professional_review"]["obtained"])
        self.assertEqual(self.latest_recheck["topic_fidelity_review"], self.review["topic_fidelity_review"])

    def test_body_runtime_manifest_review_and_sources_match(self):
        item = self.items[ITEM_ID]
        manifest = self.manifest[ITEM_ID]
        self.assertEqual(item["body"], self.article)
        self.assertEqual(self.article_sha, self.latest_recheck["after_sha256"])
        self.assertEqual(item["source_ids"], manifest["sources"])
        self.assertEqual(item["source_ids"], self.review["source_ids"])
        self.assertEqual(self.review["target_sha256"], self.article_sha)
        self.assertEqual(self.review["source_reviewed_sha256"], self.article_sha)
        self.assertEqual(self.review["reviewed_at"], self.latest_recheck["reviewed_at"])
        self.assertEqual(self.review["review_due_at"], self.latest_recheck["review_due_at"])
        self.assertEqual(self.review["source_checks"], self.latest_recheck["source_checks"])
        self.assertEqual(self.review["statistics_assessed"], self.latest_recheck["statistics_assessed"])
        self.assertEqual(self.latest_recheck["limits"], self.review["limits"])
        self.assertEqual(self.items[ITEM_ID]["limits"], " ".join(self.latest_recheck["limits"]))

        body_urls = set(re.findall(r"\]\((https?://[^)]+)\)", self.article))
        source_urls = {self.sources[sid]["url"] for sid in item["source_ids"]}
        self.assertEqual(body_urls, source_urls)
        self.assertEqual({row["source_id"] for row in self.review["source_checks"]}, set(item["source_ids"]))

        bundle_rows = {row[0]: row for row in self.bundle["sources"]}
        for source_id in NEW_SOURCE_IDS:
            with self.subTest(source_id=source_id):
                _, title, url, supports = bundle_rows[source_id]
                runtime_source = self.sources[source_id]
                self.assertEqual((runtime_source["title"], runtime_source["url"], runtime_source["supports"]),
                                 (title, url, supports))
                self.assertLessEqual(runtime_source["accessed_at"], self.review["reviewed_at"])

    def test_statistics_distinguish_study_types_and_missing_denominators(self):
        required = {
            "period", "geographic_scope", "population", "numerator", "denominator",
            "event_definition", "data_type", "limitations", "source_ids", "accessed_at",
        }
        stats = self.review["statistics_assessed"]
        self.assertGreaterEqual(len(stats), 7)
        for stat in stats:
            with self.subTest(topic=stat["topic"]):
                self.assertTrue(required.issubset(stat))
                self.assertTrue(all(stat[key] for key in required))
                self.assertTrue(set(stat["source_ids"]).issubset(set(self.review["source_ids"])))

        body = self.items[ITEM_ID]["body"]
        for phrase in (
            "不是個人死亡機率", "未另列此替換分析的合併樣本分母與死亡件數",
            "最高與最低攝取組比較實際納入10項研究",
            "未另列此子分析的合併總人數及死亡件數",
            "不能當成目前飲用率", "沒有使用抽樣權重", "不能當成全台人口的現況或盛行率",
        ):
            self.assertIn(phrase, body)
        self.assertIn("隨機試驗", body)
        self.assertIn("觀察性世代研究", body)

    def test_reader_copy_and_chapter_navigation_are_clean_and_current(self):
        self.assertNotRegex(
            self.article,
            r"(批次摘要|AI協助|本次.{0,12}(?:審查|再審|核對)|CI\s*(?:成功|通過)|PR\s*#\d+|專業審閱仍待|待專業審閱|fork管理)",
        )
        chapter = read_json("localization/tw-edition/chapters/02.json")
        row = next(row for row in chapter["entries"] if row[0] == 7)
        self.assertEqual(row[1], self.items[ITEM_ID]["title"])
        self.assertEqual(row[5].split(), self.items[ITEM_ID]["source_ids"])
        readme = (ROOT / "locales/zh-TW/book/ch02/README.md").read_text(encoding="utf-8")
        self.assertIn(f"[{self.items[ITEM_ID]['title']}](TW-02-007.md)", readme)


if __name__ == "__main__":
    unittest.main()

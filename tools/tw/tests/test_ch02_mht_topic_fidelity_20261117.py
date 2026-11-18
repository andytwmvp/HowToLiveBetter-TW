"""TW-02-043 Taiwan menopause treatment, topic fidelity, source and review contract."""
import hashlib
import json
import re
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools/tw"))
sys.path.insert(0, str(ROOT / "tools/tw/tests"))

from body_structure_test_support import body_structure_issues
from ci_language_policy import audit_drafts
from review_contract import publication_report, validate_runtime

BASE = "b2d80a276c27652bb55e4637234176cf777898dc"
DATE = "2026-11-17"
DUE = "2027-02-17"
ITEM_ID = "TW-02-043"
ARTICLE = "locales/zh-TW/book/ch02/TW-02-043.md"
REVIEW_PATH = f"localization/reviews/{ITEM_ID}.json"
BATCH_PATH = "localization/ch02-mht-topic-fidelity-20261117.json"
SOURCE_PATH = "localization/tw-edition/sources/ch02-mht-topic-fidelity-20261117.json"
REGISTER_PATH = "localization/retroactive-review-register-20261019.json"
SOURCE_IDS = {
    "tw02_hpa_menopause_health_2026",
    "tw02_tms_mht_consensus_2025",
    "tw02_shyu_menopause_symptoms_taiwan_2005",
    "tw02_fang_hotflash_taiwan_meta_2024",
    "tw02_ims_menopause_recommendations_2026",
    "tw02_uspstf_mht_primary_prevention_2022",
    "tw02_whi_mortality_mht_2017",
}


def read(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def git_show(revision, path):
    result = subprocess.run(
        ["git", "show", f"{revision}:{path}"],
        cwd=ROOT,
        capture_output=True,
    )
    return result.stdout if result.returncode == 0 else None


def digest(data):
    return hashlib.sha256(data).hexdigest()


class MenopauseTopicFidelityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.runtime = validate_runtime()
        cls.items = {row["id"]: row for row in cls.runtime["items"]}
        cls.sources = {row["id"]: row for row in cls.runtime["sources"]}
        cls.manifest = {row["id"]: row for row in read("localization/manifest.json")["entries"]}
        cls.review = read(REVIEW_PATH)
        cls.batch = read(BATCH_PATH)
        cls.batch_item = cls.batch["items"][0]
        cls.bundle = read(SOURCE_PATH)
        cls.coverage = read("localization/tw-edition/coverage.json")
        cls.register = read(REGISTER_PATH)
        cls.article_bytes = (ROOT / ARTICLE).read_bytes()
        cls.body = cls.article_bytes.decode("utf-8")
        cls.item = cls.items[ITEM_ID]

    def test_baseline_first_publication_and_prior_draft_are_traceable(self):
        base_manifest = json.loads(git_show(BASE, "localization/manifest.json"))
        base_item = next(row for row in base_manifest["entries"] if row["id"] == ITEM_ID)
        self.assertEqual(self.batch["baseline_main_sha"], BASE)
        self.assertEqual(base_item["status"], "pending")
        self.assertIsNone(base_item["target_path"])
        self.assertIsNone(git_show(BASE, ARTICLE))
        self.assertIsNone(git_show(BASE, REVIEW_PATH))
        self.assertIsNone(self.batch_item["before_sha256"])
        self.assertEqual(self.batch_item["after_sha256"], digest(self.article_bytes))
        self.assertEqual(self.review["target_sha256"], digest(self.article_bytes))
        self.assertEqual(self.review["source_reviewed_sha256"], digest(self.article_bytes))
        self.assertEqual(self.batch_item["prior_chapter_draft_sha256"], self.review["prior_chapter_draft_sha256"])
        self.assertIsNone(self.review["prior_structured_draft_sha256"])
        self.assertEqual(self.batch_item["prior_structured_source_refs"], ["menopause", "tfda"])
        base_register = json.loads(git_show(BASE, REGISTER_PATH))
        base_rechecks = base_register["substantive_rechecks"]
        current_rechecks = self.register["substantive_rechecks"]
        self.assertEqual(current_rechecks[:len(base_rechecks)], base_rechecks)
        co_recheck = next(
            row for row in current_rechecks[len(base_rechecks):]
            if row["id"] == "TW-02-029" and row["reviewed_at"] == "2026-11-17"
        )
        self.assertEqual(
            co_recheck["after_sha256"],
            hashlib.sha256(self.items["TW-02-029"]["body"].encode("utf-8")).hexdigest(),
        )
        self.assertFalse(any(
            row["id"] == ITEM_ID and row["reviewed_at"] == DATE
            for row in self.register["substantive_rechecks"]
        ))
        base_chapter = json.loads(git_show(BASE, "localization/tw-edition/chapters/02.json"))
        current_chapter = read("localization/tw-edition/chapters/02.json")
        self.assertEqual(
            next(row for row in current_chapter["entries"] if row[0] == 43),
            next(row for row in base_chapter["entries"] if row[0] == 43),
        )

    def test_official_article_manifest_runtime_review_and_reader_navigation_match(self):
        entry = self.manifest[ITEM_ID]
        self.assertEqual(entry["status"], "verified")
        self.assertEqual(entry["verified_at"], DATE)
        self.assertEqual(entry["target_path"], ARTICLE)
        self.assertEqual(entry["sources"], self.item["source_ids"])
        self.assertEqual(self.item["source_ids"], self.review["source_ids"])
        self.assertEqual(self.item["body"], self.body)
        self.assertEqual(self.item["target_path"], ARTICLE)
        self.assertEqual((self.item["reviewed_at"], self.item["review_due_at"]), (DATE, DUE))
        self.assertEqual((self.review["reviewed_at"], self.review["review_due_at"]), (DATE, DUE))
        self.assertEqual(self.batch_item["after_sha256"], digest(self.article_bytes))
        self.assertEqual(self.batch_item["source_bundle_sha256"], digest((ROOT / SOURCE_PATH).read_bytes()))
        self.assertEqual(set(self.item["source_ids"]), SOURCE_IDS)
        self.assertEqual(self.coverage, audit_drafts())
        self.assertFalse(self.coverage["publication_ready"])
        self.assertFalse(publication_report()["publication_ready"])
        self.assertFalse(any(row.startswith(f"{ITEM_ID}:") for row in self.coverage["publication_blockers"]))
        chapter_readme = (ROOT / "locales/zh-TW/book/ch02/README.md").read_text(encoding="utf-8")
        self.assertEqual(chapter_readme.count("TW-02-043.md"), 1)
        self.assertIn("更年期熱潮紅、夜間盜汗影響生活時，可評估荷爾蒙治療", chapter_readme)

    def test_registered_sources_and_body_citations_are_consistent(self):
        self.assertEqual(self.bundle["checked_at"], DATE)
        bundled = {row[0]: row for row in self.bundle["sources"]}
        self.assertEqual(set(bundled), SOURCE_IDS)
        checks = {row["source_id"]: row for row in self.review["source_checks"]}
        self.assertEqual(set(checks), SOURCE_IDS)
        urls = set(re.findall(r"\]\((https://[^)]+)\)", self.body))
        self.assertEqual(urls, {self.sources[sid]["url"] for sid in SOURCE_IDS})
        for source_id in SOURCE_IDS:
            source = self.sources[source_id]
            check = checks[source_id]
            self.assertEqual(check["url"], source["url"])
            self.assertEqual(check["title"], source["title"])
            self.assertEqual(bundled[source_id][1:3], [source["title"], source["url"]])
            self.assertLessEqual(source["accessed_at"], DATE)
            self.assertEqual(check["accessed_at"], DATE)
        unregistered = dict(self.item)
        unregistered["source_ids"] = self.item["source_ids"] + ["missing_source_id"]
        issues = body_structure_issues(
            unregistered,
            known_source_ids=set(self.sources),
        )
        self.assertTrue(any("來源登錄缺少 ID" in issue for issue in issues))
        self.assertEqual(
            set(self.batch["new_source_ids"]),
            SOURCE_IDS,
        )

    def test_topic_fidelity_clinical_scope_and_taiwan_statistics_are_explicit(self):
        self.assertIn("2025年臨床聲明", self.body)
        self.assertIn("未滿60歲或停經未滿10年", self.body)
        self.assertIn("單為預防冠心病而使用屬仿單外使用", self.body)
        self.assertIn("不適用於為了處理熱潮紅等更年期症狀", self.body)
        self.assertIn("HR是兩組追蹤期間全因死亡的相對估計", self.body)
        self.assertIn("HR為0.99（95%信賴區間0.94至1.03）", self.body)
        self.assertIn("50至59歲組在治療介入期間的全因死亡HR為0.69", self.body)
        self.assertIn("18年累計追蹤為0.89（95%信賴區間0.79至1.01）", self.body)
        self.assertIn("不能解讀為荷爾蒙治療能延壽", self.body)
        self.assertIn("846人（19.1%）", self.body)
        self.assertIn("不宜當成目前全台熱潮紅或夜間盜汗盛行率", self.body)
        self.assertNotRegex(self.body, r"(批次摘要|AI協助|本次.{0,12}(?:審查|再審|核對)|CI\s*(?:成功|通過)|PR\s*#\d+|待專業審閱|fork管理)")

        self.assertTrue(self.review["professional_review"]["required"])
        self.assertFalse(self.review["professional_review"]["obtained"])
        self.assertIn("未取得獨立相關專業審閱", self.review["reviewer"])
        self.assertIn("國健署頁面「約三成」未附年份", self.review["frequency_assessment"])
        self.assertIn("目前未找到可代表全國", self.review["frequency_assessment"])

        stats = {row["topic"]: row for row in self.review["statistics_assessed"]}
        for statistic in stats.values():
            for key in (
                "value", "unit", "period", "geographic_scope", "population",
                "numerator", "denominator", "denominator_definition", "event_definition",
                "data_type", "limitations", "source_ids", "accessed_at",
            ):
                self.assertTrue(statistic.get(key), (statistic["topic"], key))
            self.assertLessEqual(statistic["accessed_at"], DATE)
        self.assertIn("2005年", stats["台灣女性自述更年期症狀（歷史調查）"]["period"])
        self.assertEqual(stats["台灣女性自述更年期症狀（歷史調查）"]["denominator"], "4,437名女性受訪者")
        taiwan_meta = stats["台灣熱潮紅盛行率的跨研究統合估計（非全國代表性調查）"]
        self.assertEqual(taiwan_meta["value"]["random_effects_prevalence"], "37.23%")
        self.assertEqual(taiwan_meta["value"]["95_CI"], [21.4, 54.59])
        self.assertEqual(taiwan_meta["value"]["studies"], 7)
        self.assertEqual(taiwan_meta["value"]["events"], 11293)
        self.assertEqual(taiwan_meta["value"]["participants"], 23754)
        self.assertEqual(taiwan_meta["value"]["overall_hot_flash_I2"], "99.51%")
        self.assertIn("不可當作目前全台盛行率", taiwan_meta["limitations"])
        whi = stats["WHI荷爾蒙試驗全因死亡"]["value"]
        self.assertEqual(whi["participants"], 27347)
        self.assertEqual(whi["deaths"], 7489)
        self.assertEqual(whi["overall_HR"], 0.99)
        self.assertEqual(whi["age_50_59_18y_95_CI"], [0.79, 1.01])

    def test_batch_counts_and_publication_boundary_remain_auditable(self):
        before = self.batch["counts_before"]
        after = self.batch["counts_after"]
        base_runtime = json.loads(git_show(BASE, "localization/tw-edition/runtime.json"))
        base_coverage = json.loads(git_show(BASE, "localization/tw-edition/coverage.json"))
        base_manifest = json.loads(git_show(BASE, "localization/manifest.json"))
        base_register = json.loads(git_show(BASE, REGISTER_PATH))
        self.assertEqual(before["manifest_entries"], len(base_manifest["entries"]))
        self.assertEqual(before["verified_core_entries"], base_coverage["core_reviewed_entries"])
        self.assertEqual(before["runtime_items"], len(base_runtime["items"]))
        self.assertEqual(before["runtime_sources"], len(base_runtime["sources"]))
        self.assertEqual(before["source_registry"], base_coverage["registry_sources"])
        self.assertEqual(before["coverage_json_files"], base_coverage["json_files_checked"])
        self.assertEqual(before["review_rechecks"], len(base_register["substantive_rechecks"]))
        self.assertEqual(after["verified_core_entries"], before["verified_core_entries"] + 1)
        self.assertEqual(after["publication_completed_entries"], before["publication_completed_entries"] + 1)
        self.assertFalse(after["publication_ready"])
        self.assertEqual(after["runtime_items"], before["runtime_items"] + 1)
        self.assertEqual(after["runtime_sources"], before["runtime_sources"] + len(SOURCE_IDS))
        self.assertEqual(after["source_registry"], before["source_registry"] + len(SOURCE_IDS))
        self.assertEqual(after["review_rechecks"], before["review_rechecks"])
        self.assertEqual(after["coverage_json_files"], before["coverage_json_files"] + 3)
        current_verified_core = sum(row["status"] == "verified" for row in self.manifest.values())
        self.assertEqual(self.coverage["core_reviewed_entries"], current_verified_core)
        self.assertGreaterEqual(current_verified_core, after["verified_core_entries"])
        base_rechecks = base_register["substantive_rechecks"]
        later_source_ids = {
            source_id
            for row in self.register["substantive_rechecks"][len(base_rechecks):]
            for source_id in row.get("new_source_ids", [])
        }
        self.assertGreaterEqual(
            self.coverage["registry_sources"],
            after["source_registry"] + len(later_source_ids),
        )
        self.assertEqual(
            self.coverage["registry_sources"],
            audit_drafts()["registry_sources"],
        )
        self.assertFalse(self.review["professional_review"]["obtained"])


if __name__ == "__main__":
    unittest.main()

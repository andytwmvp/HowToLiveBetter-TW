"""第2章主題保真度：保留可用的跨國研究，不以不相關在地題目取代。"""
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

BASE = "fa47b5ad2a8c05a04d40c5e51b401f18baaeddfb"
BATCH = "localization/ch02-topic-fidelity-recheck-20261112.json"
REGISTER = "localization/retroactive-review-register-20261019.json"


def read(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def git_bytes(revision, path):
    return subprocess.check_output(["git", "show", f"{revision}:{path}"], cwd=ROOT)


def sha(data):
    return hashlib.sha256(data).hexdigest()


class Chapter2TopicFidelityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.runtime = validate_runtime()
        cls.items = {x["id"]: x for x in cls.runtime["items"]}
        cls.sources = {x["id"]: x for x in cls.runtime["sources"]}
        cls.manifest = {x["id"]: x for x in read("localization/manifest.json")["entries"]}
        cls.batch = read(BATCH)
        cls.register = read(REGISTER)

    def test_topic_rechecks_are_append_only_and_hash_bound(self):
        for item_id in ("TW-02-025", "TW-02-047"):
            with self.subTest(item_id=item_id):
                path = f"locales/zh-TW/book/ch02/{item_id}.md"
                before = git_bytes(BASE, path)
                prior_review_path = f"localization/reviews/{item_id}.json"
                prior_review = git_bytes(BASE, prior_review_path)
                review = read(prior_review_path)
                body = (ROOT / path).read_bytes()
                record = next(
                    x for x in self.register["substantive_rechecks"]
                    if x["id"] == item_id and x["reviewed_at"] == "2026-11-12"
                )
                self.assertEqual(record["prior_revision"], subprocess.check_output(
                    ["git", "log", "-1", "--format=%H", BASE, "--", path], cwd=ROOT, text=True
                ).strip())
                self.assertEqual(record["before_sha256"], sha(before))
                self.assertEqual(record["previous_body"], before.decode("utf-8"))
                self.assertEqual(record["prior_review_sha256"], sha(prior_review))
                self.assertEqual(record["prior_reviewed_at"], json.loads(prior_review)["reviewed_at"])
                self.assertEqual(record["after_sha256"], sha(body))
                self.assertEqual(review["target_sha256"], sha(body))
                self.assertEqual(review["source_reviewed_sha256"], sha(body))
                self.assertEqual(review["review_due_at"], "2027-02-12")
                self.assertEqual(record["status"], "ai_source_rechecked_professional_pending")
                self.assertTrue(record["topic_fidelity_assessment"])
                self.assertTrue(record["source_checks"])
                self.assertFalse(review["professional_review"]["obtained"])

    def test_japanese_tea_research_is_restored_with_scope_and_limits(self):
        item = self.items["TW-02-025"]
        body = item["body"]
        self.assertIn("日本八個世代研究", body)
        self.assertIn("313,381人", body)
        self.assertIn("52,943人死亡", body)
        self.assertIn("HR）男性為0.90", body)
        self.assertIn("女性為0.82", body)
        self.assertIn("觀察性關聯", body)
        self.assertIn("不能證明", body)
        self.assertIn("每天至少5杯", body)
        self.assertIn("tw02_jphc_green_tea_mortality_2019", item["source_ids"])
        self.assertEqual(item["source_ids"], self.manifest["TW-02-025"]["sources"])
        self.assertIn("日本八個人口世代", self.sources["tw02_jphc_green_tea_mortality_2019"]["title"])
        self.assertNotRegex(body, r"本批|本次再審|AI協助|PR\s*#|CI\s*(?:通過|成功)")

    def test_bathing_article_keeps_research_and_separates_taiwan_safety_data(self):
        item = self.items["TW-02-036"]
        body = item["body"]
        self.assertEqual(self.manifest["TW-02-036"]["status"], "verified")
        self.assertEqual(item["source_ids"], self.manifest["TW-02-036"]["sources"])
        self.assertIn("日式入浴回顧", body)
        self.assertIn("13,786名65歲以上", body)
        self.assertIn("1,203人（8.7%）", body)
        self.assertIn("健康老化", body)
        self.assertIn("頻率主要由參與者自陳", body)
        self.assertIn("30,076名", body)
        self.assertIn("538,373人年", body)
        self.assertIn("2,097起新發心血管事件", body)
        self.assertIn("HR為0.72", body)
        self.assertIn("不是死亡或壽命", body)
        self.assertIn("25.2人", body)
        self.assertIn("7,776名", body)
        self.assertIn("7,363人", body)
        self.assertIn("495人", body)
        self.assertIn("沒有交代比率的加權方式或有效分母", body)
        self.assertIn("台灣目前沒有足以估算浴缸溺水或泡澡相關心血管事件個人機率的全國統計", body)
        self.assertTrue(read("localization/reviews/TW-02-036.json")["professional_review"]["required"])
        stats = read("localization/reviews/TW-02-036.json")["statistics_assessed"]
        self.assertEqual(len(stats), 5)
        for stat in stats:
            for key in ("value", "unit", "period", "geographic_scope", "population", "numerator", "denominator", "event_definition", "data_type", "limitations"):
                self.assertIn(key, stat)
                if key != "denominator":
                    self.assertTrue(stat[key], key)
        self.assertEqual(stats[0]["source_ids"], ["tw02_jages_bath_frequency_disability_2019"])
        self.assertIsNone(stats[2]["denominator"])
        self.assertIn("未提供浴缸使用者", stats[2]["denominator_definition"])
        self.assertIn("不是浴室", stats[3]["limitations"])

    def test_freshwater_fish_topic_is_discoverable_without_overstating_frequency(self):
        item = self.items["TW-02-047"]
        body = item["body"]
        self.assertEqual(item["title"], "食安基本步驟與生淡水魚的中華肝吸蟲風險")
        self.assertIn("## 生淡水魚與中華肝吸蟲", body)
        self.assertIn("最後更新於2019年", body)
        self.assertIn("沒有提供足以估算目前台灣病例頻率的資料", body)
        self.assertEqual(item["source_ids"], self.manifest["TW-02-047"]["sources"])
        readme = (ROOT / "locales/zh-TW/book/ch02/README.md").read_text(encoding="utf-8")
        for item_id in ("TW-02-025", "TW-02-036", "TW-02-047"):
            self.assertIn(f"{item_id}.md)", readme)
        self.assertIn("日本研究有觀察到死亡率關聯", readme)
        self.assertIn("中華肝吸蟲風險", readme)

    def test_runtime_registry_and_coverage_are_consistent(self):
        source_ids = [x["id"] for x in self.runtime["sources"]]
        self.assertEqual(len(source_ids), len(set(source_ids)))
        for item_id in ("TW-02-025", "TW-02-036", "TW-02-047"):
            item = self.items[item_id]
            self.assertEqual(item["body"], (ROOT / item["target_path"]).read_text(encoding="utf-8"))
            self.assertTrue(set(item["source_ids"]).issubset(self.sources))
            self.assertTrue(set(item["source_ids"]).issubset(self.manifest[item_id]["sources"]))
            urls = set(re.findall(r"\]\((https://[^)]+)\)", item["body"]))
            registered = {self.sources[sid]["url"] for sid in item["source_ids"]}
            self.assertEqual(urls, registered)
        coverage = read("localization/tw-edition/coverage.json")
        self.assertEqual(coverage, audit_drafts())
        self.assertFalse(coverage["publication_ready"])
        self.assertEqual(len(self.batch["new_source_ids"]), 8)
        self.assertEqual(len(read("localization/tw-edition/sources/ch02-topic-fidelity-recheck-20261112.json")["sources"]), 8)
        # counts_after is the immutable snapshot at this chapter 2 batch. Later
        # cross-chapter work may add sources and review rows; reconcile the old
        # snapshot to its recorded main baseline and let the live audit validate
        # today's aggregate state.
        baseline_runtime = json.loads(subprocess.check_output(
            ["git", "show", f"{self.batch['baseline_main_sha']}:localization/tw-edition/runtime.json"],
            cwd=ROOT, text=True,
        ))
        baseline_coverage = json.loads(subprocess.check_output(
            ["git", "show", f"{self.batch['baseline_main_sha']}:localization/tw-edition/coverage.json"],
            cwd=ROOT, text=True,
        ))
        baseline_register = json.loads(subprocess.check_output(
            ["git", "show", f"{self.batch['baseline_main_sha']}:localization/retroactive-review-register-20261019.json"],
            cwd=ROOT, text=True,
        ))
        self.assertEqual(self.batch["counts_after"]["runtime_items"], len(baseline_runtime["items"]) + 1)
        self.assertEqual(
            self.batch["counts_after"]["runtime_sources"],
            len(baseline_runtime["sources"]) + len(self.batch["new_source_ids"]),
        )
        self.assertEqual(
            self.batch["counts_after"]["source_registry"],
            baseline_coverage["registry_sources"] + len(self.batch["new_source_ids"]),
        )
        self.assertEqual(
            self.batch["counts_after"]["review_rechecks"],
            len(baseline_register["substantive_rechecks"]) + 2,
        )
        self.assertGreaterEqual(len(self.runtime["items"]), self.batch["counts_after"]["runtime_items"])
        self.assertGreaterEqual(len(self.runtime["sources"]), self.batch["counts_after"]["runtime_sources"])
        self.assertGreaterEqual(coverage["registry_sources"], self.batch["counts_after"]["source_registry"])
        self.assertGreaterEqual(len(self.register["substantive_rechecks"]), self.batch["counts_after"]["review_rechecks"])


if __name__ == "__main__":
    unittest.main()

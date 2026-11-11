"""第2章活動量、肌力、久坐及加工肉新正文的內容與來源契約。"""
import hashlib
import json
import re
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ci_language_policy import audit_drafts
from review_contract import ROOT, publication_report, validate_runtime


BASE = "50479aa917c4fc2ac1910e87f8fdf84f1a9f4640"
BATCH_PATH = "localization/ch02-movement-nutrition-20261109.json"
SOURCE_PATH = "localization/tw-edition/sources/ch02-movement-nutrition-20261109.json"
ITEM_IDS = tuple(f"TW-02-{number:03}" for number in range(14, 19))
NEW_SOURCE_IDS = {
    "tw02_bjsm_racquet_cohort_2016",
    "tw02_who_physical_activity_2026",
    "tw02_who_activity_guideline_2020",
    "tw02_stamatakis_vilpa_2022",
    "tw02_bjsm_strength_meta_2022",
    "tw02_hpa_nhis_activity_sitting_2021",
    "tw02_diaz_sedentary_cohort_2017",
    "tw02_ekelund_sitting_meta_2016",
    "tw02_hpa_protein_food_guide_2026",
    "tw02_iarc_processed_meat_qa_2015",
    "tw02_who_processed_meat_2026",
}


def read_json(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


class Chapter2MovementNutritionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.runtime = validate_runtime()
        cls.items = {item["id"]: item for item in cls.runtime["items"]}
        cls.sources = {source["id"]: source for source in cls.runtime["sources"]}
        cls.manifest = {
            row["id"]: row for row in read_json("localization/manifest.json")["entries"]
        }
        cls.reviews = {
            item_id: read_json(f"localization/reviews/{item_id}.json")
            for item_id in ITEM_IDS
        }
        cls.batch = read_json(BATCH_PATH)
        cls.batch_items = {row["id"]: row for row in cls.batch["items"]}
        cls.register = read_json("localization/retroactive-review-register-20261019.json")
        base_register = json.loads(
            subprocess.check_output(
                ["git", "show", f"{BASE}:localization/retroactive-review-register-20261019.json"],
                cwd=ROOT,
                text=True,
            )
        )
        cls.later_rechecks = cls.register["substantive_rechecks"][
            len(base_register["substantive_rechecks"]):
        ]
        cls.base_runtime = json.loads(
            subprocess.check_output(
                ["git", "show", f"{BASE}:localization/tw-edition/runtime.json"],
                cwd=ROOT,
                text=True,
            )
        )

    def test_items_match_reader_copy_sources_reviews_and_manifest(self):
        self.assertEqual(self.batch["baseline_main_sha"], BASE)
        self.assertEqual(self.batch["reviewed_at"], "2026-11-09")
        self.assertEqual(self.batch["review_due_at"], "2027-02-09")
        self.assertEqual(set(self.batch_items), set(ITEM_IDS))
        self.assertEqual(set(self.batch["new_source_ids"]), NEW_SOURCE_IDS)

        for item_id in ITEM_IDS:
            with self.subTest(item_id=item_id):
                item = self.items[item_id]
                record = self.batch_items[item_id]
                review = self.reviews[item_id]
                entry = self.manifest[item_id]
                body_path = ROOT / entry["target_path"]
                body_bytes = body_path.read_bytes()
                body = body_bytes.decode("utf-8")
                digest = hashlib.sha256(body_bytes).hexdigest()

                self.assertEqual(item["body"], body)
                self.assertEqual(item["target_path"], entry["target_path"])
                self.assertEqual(item["review_status"], "source_checked")
                self.assertEqual(item["reviewed_at"], "2026-11-09")
                self.assertEqual(item["review_due_at"], "2027-02-09")
                self.assertEqual(entry["status"], "verified")
                self.assertEqual(entry["verified_at"], "2026-11-09")
                self.assertEqual(entry["sources"], item["source_ids"])
                self.assertEqual(record["source_ids"], item["source_ids"])
                self.assertEqual(review["source_ids"], item["source_ids"])
                self.assertEqual(record["after_sha256"], digest)
                self.assertEqual(review["target_sha256"], digest)
                self.assertEqual(review["source_reviewed_sha256"], digest)
                self.assertEqual(record["source_checks"], review["source_checks"])
                self.assertEqual(record["statistics_assessed"], review["statistics_assessed"])
                self.assertTrue(review["professional_review"]["required"])
                self.assertFalse(review["professional_review"]["obtained"])

                body_urls = set(re.findall(r"\]\((https?://[^)]+)\)", body))
                source_urls = {self.sources[source_id]["url"] for source_id in item["source_ids"]}
                checked_urls = {check["url"] for check in review["source_checks"]}
                self.assertEqual(body_urls, source_urls)
                self.assertEqual(checked_urls, source_urls)
                self.assertNotRegex(
                    body,
                    r"(?:批次摘要|AI.{0,8}(?:查核|審閱)|本次.{0,12}(?:審查|再審|核對)|CI\s*(?:成功|通過)|PR\s*#\d+|待專業審閱)",
                )
                self.assertTrue(record["frequency_assessment"])
                for statistic in record["statistics_assessed"]:
                    for field in (
                        "period", "geographic_scope", "population", "numerator",
                        "denominator", "event_definition", "data_type", "limitations",
                    ):
                        self.assertTrue(statistic[field], (item_id, statistic["topic"], field))

    def test_statistics_and_taiwan_safety_context_are_not_overgeneralized(self):
        articles = {item_id: self.items[item_id]["body"] for item_id in ITEM_IDS}
        self.assertIn("蘇格蘭與英格蘭", articles["TW-02-014"])
        self.assertIn("不能證明是球拍運動造成差異", articles["TW-02-014"])
        self.assertIn("沒有要求每次活動必須至少10分鐘", articles["TW-02-015"])
        self.assertIn("不要為了運動追公車", articles["TW-02-015"])
        self.assertIn("不建議把趕車或猛爬樓梯當成處方", articles["TW-02-015"])
        self.assertIn("不是每個人的最佳訓練量", articles["TW-02-016"])
        self.assertIn("GRADE證據確定性為極低", articles["TW-02-016"])
        self.assertIn("仍要看職務和安全", articles["TW-02-017"])
        self.assertIn("50.7%", articles["TW-02-017"])
        self.assertIn("每日總坐著時間至少6小時", articles["TW-02-017"])
        self.assertIn("加權樣本為19,928人", articles["TW-02-017"])
        self.assertIn("相對風險約增加18%", articles["TW-02-018"])
        self.assertIn("不是偶爾吃一份就有18%的罹癌機率", articles["TW-02-018"])
        self.assertIn("IARC第1類代表人體致癌證據充分", articles["TW-02-018"])
        self.assertIn("WHO於2026年9月23日更新", articles["TW-02-018"])

    def test_sources_are_additive_and_unrelated_structured_drafts_are_preserved(self):
        base_sources = {row["id"]: row for row in self.base_runtime["sources"]}
        base_items = {row["id"]: row for row in self.base_runtime["items"]}
        for source_id, old in base_sources.items():
            self.assertEqual(self.sources[source_id], old)
        for item_id, old in base_items.items():
            current = self.items[item_id]
            if current == old:
                continue
            rechecks = [row for row in self.later_rechecks if row["id"] == item_id]
            self.assertTrue(rechecks, f"{item_id} changed without a later recorded recheck")
            old_sha = hashlib.sha256(old["body"].encode("utf-8")).hexdigest()
            current_sha = hashlib.sha256(current["body"].encode("utf-8")).hexdigest()
            self.assertEqual(rechecks[0]["before_sha256"], old_sha)
            for previous, following in zip(rechecks, rechecks[1:]):
                self.assertEqual(following["before_sha256"], previous["after_sha256"])
            self.assertEqual(rechecks[-1]["after_sha256"], current_sha)

        source_bundle = read_json(SOURCE_PATH)["sources"]
        self.assertEqual({row[0] for row in source_bundle}, NEW_SOURCE_IDS)
        for row in source_bundle:
            source = self.sources[row[0]]
            self.assertEqual(
                row,
                [source[key] for key in ("id", "title", "url", "supports")],
            )

        draft = subprocess.check_output(
            ["git", "show", f"{BASE}:localization/tw-edition/chapters/02.json"], cwd=ROOT
        )
        old_chapter = json.loads(draft)
        current_chapter = json.loads(
            (ROOT / "localization/tw-edition/chapters/02.json").read_bytes()
        )
        old_rows = {row[0]: row for row in old_chapter["entries"]}
        current_rows = {row[0]: row for row in current_chapter["entries"]}
        self.assertEqual(set(current_rows), set(old_rows))
        for number, old_row in old_rows.items():
            if number not in {25, 36, 47}:
                self.assertEqual(current_rows[number], old_row)
        self.assertIn("日本研究有觀察到死亡率關聯", current_rows[25][1])
        self.assertIn("日本研究探討心血管與健康老化", current_rows[36][1])
        self.assertIn("生淡水魚的中華肝吸蟲風險", current_rows[47][1])
        self.assertIn("喝茶、泡澡等健康研究", current_chapter["intro"])

    def test_coverage_counts_and_publication_gate_remain_accurate(self):
        coverage = read_json("localization/tw-edition/coverage.json")
        self.assertEqual(coverage, audit_drafts())
        report = publication_report()
        after = self.batch["counts_after"]
        self.assertGreaterEqual(coverage["publication_completed_entries"], after["core_reviewed"])
        self.assertEqual(coverage["core_reviewed_entries"], report["publication_completed_entries"])
        self.assertFalse(coverage["publication_ready"])
        self.assertEqual(len(self.runtime["items"]), coverage["publication_completed_entries"] + 11)
        self.assertGreaterEqual(len(self.runtime["sources"]), after["runtime_sources"])
        self.assertGreaterEqual(coverage["registry_sources"], after["source_registry"])
        self.assertGreaterEqual(coverage["json_files_checked"], after["json_files_checked"])


if __name__ == "__main__":
    unittest.main()

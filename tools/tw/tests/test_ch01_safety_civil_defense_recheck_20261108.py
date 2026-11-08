"""第1章野菇／道路安全及家庭防災指引的高風險實質再審契約。"""
import hashlib
import json
import re
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ci_language_policy import audit_drafts
from retroactive_audit import validate_recheck_history
from review_contract import ROOT, validate_runtime


BASE = "333667bb54ad11631baf61bf206509850840701a"
BATCH_PATH = "localization/ch01-safety-civil-defense-recheck-20261108.json"
SOURCE_PATH = "localization/tw-edition/sources/ch01-safety-civil-defense-recheck-20261108.json"
ITEM_IDS = ("TW-01-005", "TW-01-009", "TW-NAV-010")
NEW_SOURCE_IDS = {
    "ch01_vghtpe_poison_hotline_20261108",
    "ch01_motc_dui_2026janaug",
    "ch01_road_act_31_1_effective_dates_2026",
    "nav_ntpc_pet_disaster_202510",
}


def read_json(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


class Chapter01SafetyCivilDefenseRecheckTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.runtime = validate_runtime()
        cls.items = {item["id"]: item for item in cls.runtime["items"]}
        cls.sources = {source["id"]: source for source in cls.runtime["sources"]}
        cls.manifest = {
            item["id"]: item for item in read_json("localization/manifest.json")["entries"]
        }
        cls.reviews = {
            item_id: read_json(f"localization/reviews/{item_id}.json")
            for item_id in ITEM_IDS
        }
        cls.register = read_json("localization/retroactive-review-register-20261019.json")
        cls.batch = read_json(BATCH_PATH)
        cls.batch_items = {item["id"]: item for item in cls.batch["items"]}
        cls.base_runtime = json.loads(
            subprocess.check_output(
                ["git", "show", f"{BASE}:localization/tw-edition/runtime.json"],
                cwd=ROOT,
                text=True,
            )
        )
        cls.base_reviews = {
            item_id: json.loads(
                subprocess.check_output(
                    ["git", "show", f"{BASE}:localization/reviews/{item_id}.json"],
                    cwd=ROOT,
                    text=True,
                )
            )
            for item_id in ITEM_IDS
        }

    def test_batch_matches_reader_runtime_manifest_review_and_history(self):
        self.assertEqual(self.batch["baseline_main_sha"], BASE)
        self.assertEqual(self.batch["reviewed_at"], "2026-11-08")
        self.assertEqual(self.batch["review_due_at"], "2027-02-08")
        self.assertEqual(set(self.batch_items), set(ITEM_IDS))
        self.assertEqual(set(self.batch["scope"]["new_source_ids"]), NEW_SOURCE_IDS)
        self.assertEqual(self.batch["scope"]["new_core_ids"], [])
        self.assertTrue(self.batch["professional_review"]["required"])
        self.assertFalse(self.batch["professional_review"]["obtained"])

        for item_id in ITEM_IDS:
            with self.subTest(item_id=item_id):
                item = self.items[item_id]
                record = self.batch_items[item_id]
                review = self.reviews[item_id]
                body = (ROOT / item["target_path"]).read_text(encoding="utf-8")
                body_sha = hashlib.sha256(body.encode("utf-8")).hexdigest()
                history = [
                    row for row in self.register["substantive_rechecks"]
                    if row["id"] == item_id and row["reviewed_at"] == "2026-11-08"
                ]

                self.assertEqual(history, [record])
                self.assertEqual(record["prior_revision"], BASE)
                self.assertEqual(record["status"], "ai_source_rechecked_professional_pending")
                self.assertEqual(record["after_sha256"], body_sha)
                self.assertEqual(item["body"], body)
                self.assertEqual(review["target_sha256"], body_sha)
                self.assertEqual(review["source_reviewed_sha256"], body_sha)
                self.assertEqual(review["source_checks"], record["source_checks"])
                self.assertEqual(item["reviewed_at"], "2026-11-08")
                self.assertEqual(item["review_due_at"], "2027-02-08")
                self.assertEqual(review["reviewed_at"], "2026-11-08")
                self.assertEqual(review["review_due_at"], "2027-02-08")
                self.assertEqual(record["previous_body"], self.base_item(item_id)["body"])
                self.assertEqual(record["before_sha256"], hashlib.sha256(record["previous_body"].encode()).hexdigest())
                self.assertEqual(
                    record["prior_review_sha256"],
                    hashlib.sha256(
                        subprocess.check_output(
                            ["git", "show", f"{BASE}:localization/reviews/{item_id}.json"],
                            cwd=ROOT,
                        )
                    ).hexdigest(),
                )

                body_urls = set(re.findall(r"\]\((https?://[^)]+)\)", body))
                source_urls = {self.sources[source_id]["url"] for source_id in item["source_ids"]}
                review_urls = {check["url"] for check in review["source_checks"]}
                self.assertEqual(body_urls, source_urls)
                self.assertEqual(review_urls, source_urls)
                self.assertEqual(record["source_ids"], item["source_ids"])

                if not item_id.startswith("TW-NAV-"):
                    self.assertEqual(self.manifest[item_id]["sources"], item["source_ids"])
                    self.assertEqual(self.manifest[item_id]["verified_at"], "2026-11-08")
                    self.assertEqual(self.manifest[item_id]["status"], "verified")
                self.assertNotRegex(
                    body,
                    r"(?:批次摘要|本次.{0,12}(?:AI|審查|再審|核對)|CI\s*(?:成功|通過)|PR\s*#\d+|非律師|非醫師)",
                )
                self.assertTrue(record["limits"])
                self.assertTrue(record["statistics_assessed"])
                for statistic in record["statistics_assessed"]:
                    for field in (
                        "period", "geographic_scope", "population", "numerator",
                        "denominator", "event_definition", "data_type", "limitations",
                    ):
                        self.assertTrue(statistic[field], (item_id, statistic["topic"], field))
                validate_recheck_history(ROOT, record, item)

    def base_item(self, item_id):
        return next(item for item in self.base_runtime["items"] if item["id"] == item_id)

    def test_new_sources_and_preserved_old_source_objects(self):
        old_sources = {source["id"]: source for source in self.base_runtime["sources"]}
        for source_id, source in old_sources.items():
            self.assertEqual(self.sources[source_id], source)
        catalog = read_json(SOURCE_PATH)["sources"]
        self.assertEqual({row[0] for row in catalog}, NEW_SOURCE_IDS)
        for row in catalog:
            self.assertEqual(
                row,
                [self.sources[row[0]][key] for key in ("id", "title", "url", "supports")],
            )

    def test_updated_phone_traffic_statistics_and_pet_preparedness(self):
        mushroom = self.items["TW-01-005"]["body"]
        driving = self.items["TW-01-009"]["body"]
        guide = self.items["TW-NAV-010"]["body"]

        self.assertIn("02-2871-7121", mushroom)
        self.assertIn("02-2875-7525", mushroom)
        self.assertIn("分機85500", mushroom)
        self.assertIn("全年無休、24小時免費諮詢", mushroom)
        self.assertIn("頁面未說明是否免費", self.items["TW-01-005"]["limits"])

        for phrase in ("2026年1至8月", "76人", "5,169人", "37,158件", "19,853件", "2026年8月17日"):
            self.assertIn(phrase, driving)
        self.assertIn("第31-1條", driving)
        self.assertIn("2026年1月14日公布修正", driving)
        self.assertIn("自3月31日起施行", driving)
        self.assertIn("多項自10月31日起施行", driving)

        self.assertIn("新北市動保處建議", guide)
        self.assertIn("3至5天份食物", guide)
        self.assertIn("飲水量依動物需要及撤離時間另行估算", guide)
        for internal_text in ("CC BY", "本專案不複製", "臺灣改寫與來源重核", "PR #", "CI成功"):
            self.assertNotIn(internal_text, guide)
        self.assertNotIn("黑熊學院", guide)
        self.assertNotIn("日本內閣府", guide)

        review = self.reviews["TW-NAV-010"]
        self.assertEqual(len(review["external_reference_assessments"]), 2)
        self.assertIn("第34頁", review["external_copyright_assessment"]["checked_location"])
        self.assertIn("只存於機器", review["external_copyright_assessment"]["finding"])

    def test_coverage_counts_match_live_audit_without_publication_claim(self):
        coverage = read_json("localization/tw-edition/coverage.json")
        self.assertEqual(coverage, audit_drafts())
        self.assertEqual(coverage["core_reviewed_entries"], 292)
        self.assertEqual(len(self.runtime["items"]), 303)
        self.assertEqual(len(self.runtime["sources"]), 1186)
        self.assertEqual(coverage["registry_sources"], 1269)
        self.assertEqual(len(self.register["substantive_rechecks"]), 379)
        self.assertFalse(coverage["publication_ready"])


if __name__ == "__main__":
    unittest.main()

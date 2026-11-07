"""第2章戒菸、二手菸及電子煙六篇首次正式台灣內容契約。"""
import hashlib
import json
import re
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from review_contract import ROOT, validate_runtime

BASE = "f20b9fc962c471779378f569c5baf3cff2d4c070"
DATE = "2026-11-07"
DUE = "2027-02-07"
BATCH_PATH = "localization/ch02-smoking-services-20261107.json"
SOURCE_PATH = "localization/tw-edition/sources/ch02-smoking-services-20261107.json"
ITEM_IDS = tuple(f"TW-02-{n:03}" for n in range(1, 7))
EXPECTED_SOURCES = {
    "tw02_hpa_adult_survey_20261107",
    "tw02_hpa_adult_sample_20261107",
    "tw02_hpa_adult_definitions_20261107",
    "tw02_hpa_secondhand_ventilation_20261107",
    "tw02_hpa_cessation_resources_20261107",
    "tw02_hpa_cessation_treatment_20261107",
    "tw02_hpa_cessation_fees_20261107",
    "tw02_hpa_cessation_guideline_20261107",
    "tw02_hpa_cessation_locator_20261107",
    "tw02_pubmed_abrupt_gradual_trial_2016",
    "tw02_ucl_abrupt_gradual_fulltext_2016",
    "tw02_moj_tobacco_hazards_act_20261107",
    "tw02_mohw_ecig_amendment_20261107",
    "tw02_ly_ecig_amendment_20261107",
    "tw02_hpa_ecig_return_20261107",
    "tw02_hpa_youth_ecig_20261107",
    "tw02_hpa_youth_method_20261107",
    "tw02_hpa_htp_review_20261107",
}


def read_json(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


class ChapterTwoSmokingServicesTests(unittest.TestCase):
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
        cls.batch = read_json(BATCH_PATH)
        cls.batch_items = {item["id"]: item for item in cls.batch["items"]}
        cls.coverage = read_json("localization/tw-edition/coverage.json")
        cls.chapter_readme = (ROOT / "locales/zh-TW/book/ch02/README.md").read_text(encoding="utf-8")
        cls.register = read_json("localization/retroactive-review-register-20261019.json")

    def test_batch_has_six_verified_first_publications_with_hash_and_source_parity(self):
        self.assertEqual(self.batch["baseline_main_sha"], BASE)
        self.assertEqual(self.batch["reviewed_at"], DATE)
        self.assertEqual(self.batch["review_due_at"], DUE)
        self.assertEqual(set(self.batch_items), set(ITEM_IDS))
        self.assertEqual(set(self.batch["new_source_ids"]), EXPECTED_SOURCES)
        self.assertEqual(self.batch["professional_review"], {
            "required": True,
            "obtained": False,
            "scope": ["醫療與成癮治療", "公共衛生與流行病學", "菸害防制法"],
        })

        for item_id in ITEM_IDS:
            with self.subTest(item_id=item_id):
                item = self.items[item_id]
                manifest = self.manifest[item_id]
                batch = self.batch_items[item_id]
                review = self.reviews[item_id]
                raw = (ROOT / item["target_path"]).read_bytes()
                body = raw.decode("utf-8")
                digest = hashlib.sha256(raw).hexdigest()
                self.assertEqual(manifest["status"], "verified")
                self.assertEqual(manifest["verified_at"], DATE)
                self.assertEqual(manifest["sources"], item["source_ids"])
                self.assertEqual(manifest["target_path"], item["target_path"])
                self.assertEqual(item["body"], body)
                self.assertEqual(item["review_status"], "source_checked")
                self.assertEqual(item["reviewed_at"], DATE)
                self.assertEqual(item["review_due_at"], DUE)
                self.assertEqual(review["target_sha256"], digest)
                self.assertEqual(review["source_reviewed_sha256"], digest)
                self.assertEqual(batch["after_sha256"], digest)
                self.assertEqual(batch["status"], "ai_source_checked_professional_pending")
                self.assertEqual(batch["source_ids"], item["source_ids"])
                self.assertEqual(review["source_ids"], item["source_ids"])
                self.assertEqual(review["source_checks"], batch["source_checks"])
                self.assertEqual(review["reviewed_at"], DATE)
                self.assertEqual(review["review_due_at"], DUE)

                body_urls = set(re.findall(r"\]\((https?://[^)]+)\)", body))
                source_urls = {self.sources[sid]["url"] for sid in item["source_ids"]}
                review_urls = {check["url"] for check in review["source_checks"]}
                self.assertEqual(body_urls, source_urls)
                self.assertEqual(review_urls, source_urls)
                self.assertEqual(
                    {check["source_id"] for check in review["source_checks"]},
                    set(item["source_ids"]),
                )
                self.assertNotRegex(
                    body,
                    r"(批次摘要|未宣稱閱讀|本次.{0,12}(?:AI|審查|再審|核對)|CI\s*(?:成功|通過)|PR\s*#\d+|專業審閱仍待|fork管理)",
                )

    def test_source_registry_bundle_and_reader_navigation_are_synchronized(self):
        rows = read_json(SOURCE_PATH)["sources"]
        self.assertEqual({row[0] for row in rows}, EXPECTED_SOURCES)
        for sid, title, url, supports in rows:
            source = self.sources[sid]
            self.assertEqual((source["title"], source["url"], source["supports"]), (title, url, supports))
            self.assertEqual(source["accessed_at"], DATE)
            self.assertTrue(supports)
        for item_id in ITEM_IDS:
            self.assertIn(f"{item_id}.md)", self.chapter_readme)
        self.assertTrue(set(ITEM_IDS).isdisjoint({row["id"] for row in self.register["substantive_rechecks"]}))
        self.assertFalse(self.coverage["publication_ready"])

    def test_claims_and_frequency_limits_are_visible_and_not_confused(self):
        bodies = {item_id: self.items[item_id]["body"] for item_id in ITEM_IDS}
        self.assertIn("12.8%", bodies["TW-02-001"])
        self.assertIn("不是戒菸成功率", bodies["TW-02-001"])
        self.assertIn("35.6%", bodies["TW-02-002"])
        self.assertIn("不是全台有二手菸的家庭比例", bodies["TW-02-002"])
        self.assertIn("尼古丁依賴度量表4分", bodies["TW-02-003"])
        self.assertIn("掛號費", bodies["TW-02-003"])
        self.assertIn("15.5%", bodies["TW-02-004"])
        self.assertIn("22.0%", bodies["TW-02-004"])
        self.assertIn("53/342", bodies["TW-02-004"])
        self.assertIn("78/355", bodies["TW-02-004"])
        self.assertIn("英國", bodies["TW-02-004"])
        self.assertIn("0800-636-363", bodies["TW-02-005"])
        self.assertIn("週一至週六上午9點到晚上9點", bodies["TW-02-005"])
        self.assertIn("第15條", bodies["TW-02-006"])
        self.assertIn("新臺幣2,000元以上、1萬元以下", bodies["TW-02-006"])
        self.assertIn("草案不能當成已公布施行的法律", bodies["TW-02-006"])
        self.assertIn("加熱菸則按", bodies["TW-02-006"])
        self.assertIn("國中生為2.1%、高中職學生為5.1%", bodies["TW-02-006"])
        reader_limits = self.items["TW-02-006"]["limits"]
        self.assertIn("青少年統計僅涵蓋在學樣本", reader_limits)
        self.assertNotRegex(reader_limits, r"資料庫整編|本次|本輪|AI|專業審閱")

        for item_id, record in self.batch_items.items():
            for statistic in record["statistics_assessed"]:
                for key in (
                    "period", "geographic_scope", "population", "numerator", "denominator",
                    "event_definition", "data_type", "limitations", "source_ids",
                ):
                    self.assertTrue(statistic[key], (item_id, statistic["topic"], key))

    def test_before_after_counts_derive_from_the_live_baseline_and_coverage(self):
        def base_json(path):
            return json.loads(subprocess.check_output(
                ["git", "show", f"{BASE}:{path}"], cwd=ROOT, text=True
            ))

        base_manifest = base_json("localization/manifest.json")
        base_runtime = base_json("localization/tw-edition/runtime.json")
        base_coverage = base_json("localization/tw-edition/coverage.json")
        base_register = base_json("localization/retroactive-review-register-20261019.json")
        baseline_item_ids = [item["id"] for item in base_runtime["items"]]
        baseline_item_set = set(baseline_item_ids)
        self.assertEqual(
            baseline_item_ids,
            [item["id"] for item in self.runtime["items"] if item["id"] in baseline_item_set],
        )
        baseline_source_ids = [source["id"] for source in base_runtime["sources"]]
        baseline_source_set = set(baseline_source_ids)
        self.assertEqual(
            baseline_source_ids,
            [source["id"] for source in self.runtime["sources"] if source["id"] in baseline_source_set],
        )
        before = self.batch["counts_before"]
        after = self.batch["counts_after"]
        self.assertEqual(before["core_reviewed"], sum(e["status"] == "verified" for e in base_manifest["entries"]))
        self.assertEqual(before["runtime_items"], len(base_runtime["items"]))
        self.assertEqual(before["runtime_sources"], len(base_runtime["sources"]))
        self.assertEqual(before["source_registry"], base_coverage["registry_sources"])
        self.assertEqual(before["json_files_checked"], base_coverage["json_files_checked"])
        self.assertEqual(before["core_reviewed"], base_coverage["publication_completed_entries"])
        self.assertEqual(before["substantive_rechecks"], len(base_register["substantive_rechecks"]))
        self.assertGreaterEqual(self.coverage["core_reviewed_entries"], after["core_reviewed"])
        self.assertGreaterEqual(len(self.runtime["items"]), after["runtime_items"])
        self.assertGreaterEqual(len(self.runtime["sources"]), after["runtime_sources"])
        self.assertGreaterEqual(self.coverage["registry_sources"], after["source_registry"])
        self.assertGreaterEqual(self.coverage["json_files_checked"], after["json_files_checked"])
        self.assertGreaterEqual(len(self.register["substantive_rechecks"]), after["substantive_rechecks"])
        self.assertEqual(after["core_reviewed"], before["core_reviewed"] + len(ITEM_IDS))
        self.assertEqual(after["runtime_items"], before["runtime_items"] + len(ITEM_IDS))
        self.assertEqual(after["runtime_sources"], before["runtime_sources"] + len(EXPECTED_SOURCES))
        self.assertEqual(after["source_registry"], before["source_registry"] + len(EXPECTED_SOURCES))
        self.assertEqual(after["json_files_checked"], before["json_files_checked"] + 8)
        self.assertEqual(after["substantive_rechecks"], before["substantive_rechecks"])


if __name__ == "__main__":
    unittest.main()

"""2026-10-28 跨領域法規、風險頻率與臺灣情境歷史實質再審。"""
import hashlib
import json
import sys
import subprocess
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ci_language_policy import audit_drafts
from retroactive_audit import assert_preserved_or_rechecked, validate_recheck_history
from review_contract import ROOT, publication_report, validate_runtime


BASE = "3f2636d3a01ef38a3764323f3f1ba7666de92801"
IDS = ("TW-01-035", "TW-21-005", "TW-21-006", "TW-21-012", "TW-21-013")
NEW_SOURCES = {
    "ch21_mofa_overseas_job_20261028",
    "ch21_nia_trafficking_report_2025",
    "ch21_boca_emergency_center_20260707",
    "ch21_tfda_controlled_meds_20260520",
    "ch21_tfda_foreign_meds_20251215",
}


def read(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


class CrossBorderRecheckTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.runtime = validate_runtime()
        cls.items = {item["id"]: item for item in cls.runtime["items"]}
        cls.sources = {source["id"]: source for source in cls.runtime["sources"]}
        cls.manifest = {
            item["id"]: item for item in read("localization/manifest.json")["entries"]
        }
        cls.register = read("localization/retroactive-review-register-20261019.json")
        cls.records = {
            item["id"]: item for item in cls.register["substantive_rechecks"]
        }
        cls.batch = read("localization/ch21-cross-border-recheck-20261028.json")

    def test_runtime_bodies_sources_manifest_and_history_are_synchronized(self):
        self.assertEqual(self.batch["base_main_sha"], BASE)
        for key in IDS:
            with self.subTest(id=key):
                item = self.items[key]
                review = read(f"localization/reviews/{key}.json")
                record = self.records[key]
                body = (ROOT / item["target_path"]).read_text(encoding="utf-8")
                digest = hashlib.sha256(body.encode("utf-8")).hexdigest()
                self.assertEqual(body, item["body"])
                self.assertEqual(review["target_sha256"], digest)
                self.assertEqual(record["after_sha256"], digest)
                self.assertNotEqual(record["before_sha256"], record["after_sha256"])
                self.assertEqual(review["reviewed_at"], "2026-10-28")
                self.assertEqual(review["review_due_at"], "2027-01-31")
                self.assertEqual(record["source_checks"], review["source_checks"])
                self.assertEqual(record["limits"], review["limits"])
                self.assertTrue(record["previous_review_claims"])
                self.assertTrue(record["taiwan_context_assessment"]["independent_of_frequency"])
                self.assertTrue(all(self.sources[source_id]["url"] in body
                                    for source_id in item["source_ids"]))
                self.assertEqual(
                    self.manifest[key]["sources"],
                    [self.sources[source_id]["url"] for source_id in item["source_ids"]],
                )
                self.assertEqual(
                    {source["url"] for source in review["source_checks"]},
                    {self.sources[source_id]["url"] for source_id in item["source_ids"]},
                )
                validate_recheck_history(ROOT, record, item)

    def test_append_only_register_supports_repeated_substantive_rechecks(self):
        original = json.loads(subprocess.check_output(
            ["git", "show", "aebcc50e73df8bef92bfb8f884dde9e94b4e972e:localization/tw-edition/runtime.json"],
            cwd=ROOT, text=True,
        ))
        old = next(item for item in original["items"] if item["id"] == "TW-01-035")
        assert_preserved_or_rechecked(self, old, self.items["TW-01-035"])
        self.assertEqual(
            sum(record["id"] == "TW-01-035" for record in self.register["substantive_rechecks"]),
            2,
        )

    def test_recovered_20261024_histories_match_immutable_mainline_records(self):
        source_revision = "68742d9226d6f750175936d4c2040a4cc4570ec2"
        historical = json.loads(subprocess.check_output(
            ["git", "show", f"{source_revision}:localization/retroactive-review-register-20261019.json"],
            cwd=ROOT, text=True,
        ))
        repaired_ids = {"TW-16-006", "TW-17-002", "TW-17-004", "TW-24-001"}
        self.assertEqual({row["id"] for row in self.batch["historical_chain_repairs"]}, repaired_ids)
        for key in repaired_ids:
            with self.subTest(id=key):
                original = next(row for row in historical["substantive_rechecks"]
                                if row["id"] == key)
                rows = sorted((row for row in self.register["substantive_rechecks"]
                               if row["id"] == key), key=lambda row: row["reviewed_at"])
                self.assertEqual(rows[0], original)
                self.assertEqual([row["reviewed_at"] for row in rows], ["2026-10-24", "2026-10-25"])
                before = json.loads(subprocess.check_output(
                    ["git", "show", f"{original['prior_revision']}:localization/tw-edition/runtime.json"],
                    cwd=ROOT, text=True,
                ))
                old = next(item for item in before["items"] if item["id"] == key)
                assert_preserved_or_rechecked(self, old, self.items[key])

    def test_frequency_evidence_keeps_population_and_law_separate(self):
        job = self.items["TW-21-005"]["body"]
        self.assertIn("337名", job)
        self.assertIn("不是確診人口販運人數", job)
        self.assertIn("沒有海外求職者或旅客暴露母數", job)
        self.assertIn("0800-085-095", job)
        self.assertIn("+886-800-085-095", job)
        self.assertIn("不要因此把所有海外工作、特定地區或特定族群一概當成犯罪", job)
        stat = self.records["TW-21-005"]["statistics_assessed"][0]
        self.assertEqual(stat["value"], {"returnees_issued_entry_care_notices": 337})
        self.assertIsNone(stat["denominator"])
        self.assertIn("非抽樣調查", stat["data_type"])
        self.assertTrue(any("不能估個人發生機率" in value for value in stat["limitations"]))
        self.assertTrue(self.records["TW-21-005"]["taiwan_context_assessment"]["legal_status"])

        cash = self.items["TW-21-006"]["body"]
        for phrase in ("美金1萬元", "新臺幣10萬元", "人民幣2萬元", "申報後外幣不限額"):
            self.assertIn(phrase, cash)
        self.assertTrue(any("不能以門檻" in value for value in self.records["TW-21-006"]["statistics_assessed"][0]["limitations"]))

    def test_taiwan_organ_trade_prohibition_is_not_reduced_to_frequency(self):
        item = self.items["TW-01-035"]
        body = item["body"]
        for phrase in ("第12條", "無償", "第16條", "刑事責任", "不以案件多寡為條件"):
            self.assertIn(phrase, body)
        review = read("localization/reviews/TW-01-035.json")
        assessment = review["taiwan_context_assessment"]
        self.assertTrue(assessment["independent_of_frequency"])
        self.assertIn("無償", assessment["legal_status"])
        self.assertIn("刑事責任", assessment["legal_status"])
        source_id = "ch01_organ_law_tw_20261028"
        self.assertIn(source_id, item["source_ids"])
        self.assertIn("第12條", self.sources[source_id]["supports"])
        stat = self.records["TW-01-035"]["statistics_assessed"][0]
        self.assertIsNone(stat["value"])
        self.assertIsNone(stat["denominator"])
        self.assertIn("不影響法定無償要求", stat["data_type"])

    def test_taiwan_medicine_process_and_quarantine_context_are_specific(self):
        meds = self.items["TW-21-012"]["body"]
        for phrase in ("第一級至第三級管制藥品", "約需7個工作天", "最多6個月用量", "不自行停藥"):
            self.assertIn(phrase, meds)
        med_sources = self.items["TW-21-012"]["source_ids"]
        self.assertIn("ch21_tfda_controlled_meds_20260520", med_sources)
        self.assertIn("ch21_tfda_foreign_meds_20251215", med_sources)

        quarantine = self.items["TW-21-013"]["body"]
        for phrase in ("新鮮果實", "附土", "來源地", "不合格可能存關退運或銷毀", "免稅不是免檢疫"):
            self.assertIn(phrase, quarantine)
        self.assertIn("未找到可配對的全國旅客暴露人次與違規分子", quarantine)
        self.assertNotIn("乳製品一律禁止", quarantine)
        self.assertNotIn("所有熟食一律禁止", quarantine)

    def test_ice_draft_is_replaced_by_the_verified_taiwan_mountain_analogue(self):
        row = read("localization/tw-edition/chapters/01.json")["entries"][40]
        joined = " ".join(str(value) for value in row)
        self.assertIn("高山天候", joined)
        self.assertIn("119", joined)
        self.assertNotIn("海外結冰水面", joined)
        self.assertNotIn("冰厚", joined)

    def test_sources_and_current_counts_match_the_batch_evidence(self):
        catalog = read("localization/tw-edition/sources/ch21-cross-border-recheck-20261028.json")
        self.assertEqual({row[0] for row in catalog["sources"]}, NEW_SOURCES)
        self.assertTrue(NEW_SOURCES.issubset(self.sources))
        self.assertEqual(self.batch["scope"]["new_core_ids"], [])
        self.assertEqual(self.batch["scope"]["historical_ids"], list(IDS))

        coverage = read("localization/tw-edition/coverage.json")
        live = audit_drafts()
        after = self.batch["counts_after"]
        self.assertEqual(coverage, live)
        self.assertEqual(coverage["core_reviewed_entries"], after["core_reviewed"])
        self.assertEqual(coverage["registry_sources"], after["registry_sources"])
        self.assertEqual(len(self.runtime["items"]), after["runtime_items"])
        self.assertEqual(len(self.runtime["sources"]), after["runtime_sources"])
        self.assertEqual(len(self.register["substantive_rechecks"]), after["substantive_rechecks"])
        self.assertFalse(self.batch["publication_ready"])
        self.assertFalse(publication_report()["publication_ready"])


if __name__ == "__main__":
    unittest.main()

"""回歸驗證第13章急症歷史再審的內容、來源與追溯紀錄。"""
import hashlib
import json
import re
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from review_contract import ROOT, publication_report, validate_runtime
from retroactive_audit import validate_recheck_history


BASE = "58bdcaa0906c01e1a663c3dc41bf4e75fa911bc3"
BATCH_PATH = "localization/ch13-p0-emergency-recheck-20261103.json"
SOURCE_PATH = "localization/tw-edition/sources/ch13-p0-emergency-recheck-20261103.json"
ITEM_IDS = ("TW-13-015", "TW-13-016", "TW-13-020", "TW-13-045")


def read_json(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


class Chapter13EmergencyP0RecheckTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.runtime = validate_runtime()
        cls.runtime_items = {item["id"]: item for item in cls.runtime["items"]}
        cls.runtime_sources = {source["id"]: source for source in cls.runtime["sources"]}
        cls.manifest = read_json("localization/manifest.json")
        cls.manifest_items = {item["id"]: item for item in cls.manifest["entries"]}
        cls.reviews = {
            item_id: read_json(f"localization/reviews/{item_id}.json")
            for item_id in ITEM_IDS
        }
        cls.register = read_json("localization/retroactive-review-register-20261019.json")
        cls.batch = read_json(BATCH_PATH)
        cls.batch_items = {item["id"]: item for item in cls.batch["items"]}
        cls.evidence_sources = read_json(SOURCE_PATH)["sources"]

    def test_batch_records_append_actual_body_and_review_hash_edges(self):
        self.assertEqual(self.batch["baseline_main_sha"], BASE)
        self.assertEqual(self.batch["reviewed_at"], "2026-11-03")
        self.assertEqual(self.batch["review_due_at"], "2027-02-03")
        self.assertEqual(set(self.batch_items), set(ITEM_IDS))
        self.assertEqual(self.batch["professional_review"]["obtained"], False)
        self.assertTrue(self.batch["professional_review"]["required"])

        evidence_by_id = {source[0]: source for source in self.evidence_sources}
        self.assertEqual(set(evidence_by_id), set(self.batch["new_source_ids"]))
        for source_id, row in evidence_by_id.items():
            runtime_source = self.runtime_sources[source_id]
            self.assertEqual(row, [
                runtime_source["id"], runtime_source["title"],
                runtime_source["url"], runtime_source["supports"],
            ])

        for item_id in ITEM_IDS:
            with self.subTest(item_id=item_id):
                item = self.runtime_items[item_id]
                review = self.reviews[item_id]
                record = self.batch_items[item_id]
                history = [
                    row for row in self.register["substantive_rechecks"]
                    if row["id"] == item_id and row["reviewed_at"] == self.batch["reviewed_at"]
                ]
                self.assertEqual(len(history), 1)
                self.assertEqual(history[0], record)
                self.assertEqual(record["status"], "ai_source_rechecked_professional_pending")
                self.assertEqual(record["review_due_at"], self.batch["review_due_at"])
                self.assertEqual(review["reviewed_at"], record["reviewed_at"])
                self.assertEqual(review["review_due_at"], record["review_due_at"])

                body_path = ROOT / item["target_path"]
                body = body_path.read_text(encoding="utf-8")
                body_sha = hashlib.sha256(body_path.read_bytes()).hexdigest()
                self.assertEqual(body, item["body"])
                self.assertEqual(body_sha, record["after_sha256"])
                self.assertEqual(body_sha, review["target_sha256"])
                self.assertEqual(self.manifest_items[item_id]["target_path"], item["target_path"])
                self.assertEqual(self.manifest_items[item_id]["status"], "verified")

                current_source_ids = set(item["source_ids"])
                review_urls = {source["url"] for source in review["source_checks"]}
                runtime_urls = {self.runtime_sources[source_id]["url"] for source_id in current_source_ids}
                body_urls = set(re.findall(r"\]\((https?://[^)]+)\)", body))
                self.assertEqual(review_urls, runtime_urls)
                self.assertEqual(body_urls, runtime_urls)
                self.assertEqual(set(record["source_ids"]), current_source_ids)
                self.assertEqual(review.get("reader_copy_cleanup"), None)
                self.assertNotRegex(
                    body,
                    r"(?:批次摘要|PR\s*#\d+|CI\s*(?:成功|通過)|(?:本次|本輪).{0,16}(?:AI|審查|再審|核對))",
                )

                validate_recheck_history(ROOT, record, item)

    def test_retired_sources_are_preserved_and_unmeasured_frequency_stays_explicit(self):
        baseline = json.loads(
            subprocess.check_output(
                ["git", "show", f"{BASE}:localization/tw-edition/runtime.json"],
                cwd=ROOT,
                text=True,
            )
        )
        current_sources = self.runtime_sources
        old_sources = {source["id"]: source for source in baseline["sources"]}
        for item_id in ITEM_IDS:
            record = self.batch_items[item_id]
            for retired in record["retired_sources"]:
                source_id = retired["id"]
                self.assertEqual(current_sources[source_id], old_sources[source_id])
            self.assertRegex(record["frequency_assessment"], r"(?:不能估算|不能換算|不據此估算|不估算)")
            self.assertIn("分母", record["frequency_assessment"])
            self.assertRegex(record["frequency_assessment"], r"(?:沒有提供|未列出|未提供|沒有全國)")

    def test_allergy_product_cost_and_guideline_pagination_are_scoped(self):
        body = self.runtime_items["TW-13-015"]["body"]
        self.assertIn("艾筆腎上腺素注射筆0.3毫克／次", body)
        self.assertIn("列為處方藥", body)
        self.assertIn("沒有列出目前供貨、價格或健保給付資訊", body)
        self.assertIn("台灣全國嚴重過敏反應發生率", self.batch_items["TW-13-015"]["frequency_assessment"])
        self.assertEqual(
            set(self.runtime_items["TW-13-015"]["source_ids"]),
            {
                "ch13_ana_taaaci_2024",
                "ch13_ana_nfa_20260430",
                "ch13_ana_cch_anaphylaxis_20221026",
                "ch13_ana_viatris_epipen_20261103",
            },
        )
        taaaci = next(
            row for row in self.reviews["TW-13-015"]["source_checks"]
            if "taaaci.org.tw" in row["url"]
        )
        self.assertIn("印刷頁碼第7至8頁", taaaci["supporting_passage"])
        self.assertIn("PDF實體第11至12頁", taaaci["supporting_passage"])
        self.assertIn("印刷第31頁", taaaci["supporting_passage"])
        self.assertIn("PDF實體第35頁", taaaci["supporting_passage"])

    def test_seizure_rescue_triggers_do_not_treat_ordinary_ictal_unresponsiveness_as_threshold(self):
        body = self.runtime_items["TW-13-016"]["body"]
        for phrase in (
            "抽搐超過五分鐘",
            "連續抽搐兩次以上",
            "發作時受傷",
            "呼吸不正常時，立即撥119",
            "原因不明的第一次發作",
        ):
            self.assertIn(phrase, body)
        self.assertNotIn("患者失去反應，立即撥119", body)
        self.assertIn("這本身不等於新增一項求援門檻", body)

    def test_batch_source_counts_match_runtime_registry_and_file_inventory(self):
        self.assertEqual(len(self.batch["new_source_ids"]), 10)
        self.assertEqual(self.batch["counts_after"]["runtime_sources"], len(self.runtime["sources"]))
        self.assertEqual(self.batch["counts_after"]["registry_sources"], read_json("localization/tw-edition/coverage.json")["registry_sources"])
        self.assertEqual(self.batch["counts_after"]["json_files"], read_json("localization/tw-edition/coverage.json")["json_files_checked"])
        self.assertEqual(self.batch["counts_after"]["runtime_sources"], 1052)
        self.assertEqual(self.batch["counts_after"]["registry_sources"], 1135)
        self.assertEqual(self.batch["counts_after"]["json_files"], 538)

    def test_emergency_guidance_keeps_taiwan_specific_safety_boundaries(self):
        bodies = {item_id: self.runtime_items[item_id]["body"] for item_id in ITEM_IDS}
        self.assertIn("立即撥119", bodies["TW-13-015"])
        self.assertIn("腎上腺素自動注射器", bodies["TW-13-015"])
        self.assertIn("不是所有人都等五分鐘", bodies["TW-13-016"])
        self.assertIn("不要強行壓制四肢", bodies["TW-13-016"])
        self.assertIn("02-2871-7121", bodies["TW-13-020"])
        self.assertIn("禁止自行催吐", bodies["TW-13-020"])
        self.assertIn("即使看起來沒有症狀", bodies["TW-13-045"])
        self.assertIn("不催吐", bodies["TW-13-045"])
        self.assertIn("一歲以下不適用", bodies["TW-13-045"])
        self.assertIn("不能取代緊急胃鏡移除", bodies["TW-13-045"])
        self.assertFalse(publication_report()["publication_ready"])


if __name__ == "__main__":
    unittest.main()

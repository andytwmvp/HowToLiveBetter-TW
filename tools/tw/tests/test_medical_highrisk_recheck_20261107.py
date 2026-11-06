"""四篇高風險醫療內容的臺灣證據、歷史與閱讀出口契約。"""
import hashlib
import json
import re
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from retroactive_audit import validate_recheck_history
from review_contract import ROOT, validate_runtime

BASE = "e4935103417fec6f09305b15a3a42e3ed4a92e3d"
DATE = "2026-11-07"
DUE = "2027-02-07"
BATCH = "localization/medical-highrisk-recheck-20261107.json"
SOURCE_INDEX = "localization/tw-edition/sources/medical-highrisk-recheck-20261107.json"
IDS = ("TW-16-008", "TW-24-013", "TW-16-011", "TW-16-007")


def read_json(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


class MedicalHighRiskRecheckTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.runtime = validate_runtime()
        cls.items = {item["id"]: item for item in cls.runtime["items"]}
        cls.sources = {source["id"]: source for source in cls.runtime["sources"]}
        cls.manifest = {item["id"]: item for item in read_json("localization/manifest.json")["entries"]}
        cls.reviews = {key: read_json(f"localization/reviews/{key}.json") for key in IDS}
        cls.register = read_json("localization/retroactive-review-register-20261019.json")
        cls.batch = read_json(BATCH)
        cls.batch_items = {item["id"]: item for item in cls.batch["items"]}
        cls.base_runtime = json.loads(subprocess.check_output(
            ["git", "show", f"{BASE}:localization/tw-edition/runtime.json"], cwd=ROOT, text=True
        ))

    def test_four_rechecks_match_runtime_manifest_reviews_and_append_only_history(self):
        self.assertEqual(self.batch["baseline_main_sha"], BASE)
        self.assertEqual(self.batch["reviewed_at"], DATE)
        self.assertEqual(self.batch["review_due_at"], DUE)
        self.assertEqual(self.batch["risk_order"], list(IDS))
        self.assertEqual(self.batch["new_core_ids"], [])
        self.assertEqual(self.batch["rechecked_ids"], list(IDS))
        self.assertTrue(self.batch["professional_review"]["required"])
        self.assertFalse(self.batch["professional_review"]["obtained"])
        self.assertEqual(set(self.batch_items), set(IDS))

        for key in IDS:
            with self.subTest(item_id=key):
                item = self.items[key]
                record = self.batch_items[key]
                review = self.reviews[key]
                body_path = ROOT / item["target_path"]
                body_bytes = body_path.read_bytes()
                body_sha = hashlib.sha256(body_bytes).hexdigest()
                history = [row for row in self.register["substantive_rechecks"]
                           if row["id"] == key and row["reviewed_at"] == DATE]
                self.assertEqual(len(history), 1)
                self.assertEqual(history[0], record)
                self.assertEqual(record["status"], "ai_source_rechecked_professional_pending")
                self.assertEqual(record["prior_revision"], BASE)
                self.assertEqual(record["before_sha256"], hashlib.sha256(
                    self.base_runtime["items"][[x["id"] for x in self.base_runtime["items"]].index(key)]["body"].encode()
                ).hexdigest())
                self.assertEqual(record["after_sha256"], body_sha)
                self.assertEqual(body_path.read_text(encoding="utf-8"), item["body"])
                self.assertEqual(body_sha, review["target_sha256"])
                self.assertEqual(body_sha, review["source_reviewed_sha256"])
                self.assertEqual(review["source_checks"], record["source_checks"])
                prior_review = json.loads(subprocess.check_output(
                    ["git", "show", f"{BASE}:localization/reviews/{key}.json"], cwd=ROOT, text=True
                ))
                self.assertEqual(review["prior_source_checks"], prior_review["source_checks"])
                self.assertEqual(record["prior_source_checks"], prior_review["source_checks"])
                self.assertEqual(review["limits"], record["limits"])
                self.assertEqual(review["statistics_assessed"], record["statistics_assessed"])
                self.assertEqual(self.manifest[key]["sources"], item["source_ids"])
                self.assertEqual(self.manifest[key]["status"], "verified")
                self.assertEqual(self.manifest[key]["verified_at"], DATE)
                self.assertEqual(item["reviewed_at"], DATE)
                self.assertEqual(item["review_due_at"], DUE)

                urls = {self.sources[sid]["url"] for sid in item["source_ids"]}
                self.assertEqual(set(re.findall(r"\]\((https?://[^)]+)\)", item["body"])), urls)
                self.assertEqual({check["url"] for check in review["source_checks"]}, urls)
                self.assertTrue(all(check.get("retrieval_method") and "非逐字" in check["supporting_passage"]
                                    for check in record["source_checks"]))
                self.assertEqual(item["body"].count("\n## "), 5)
                self.assertNotRegex(item["body"], r"(?:批次摘要|AI來源再審|專業審閱待取得|內部審查|本次.{0,12}(?:AI|審查|再審|核對))")
                self.assertTrue(record["statistics_assessed"])
                for statistic in record["statistics_assessed"]:
                    for field in ("period", "geographic_scope", "population", "numerator", "denominator",
                                  "event_definition", "data_type", "limitations", "accessed_at", "source_id"):
                        self.assertTrue(statistic.get(field), (key, field, statistic))
                validate_recheck_history(ROOT, record, item)

    def test_retired_sources_remain_unchanged_and_are_replaced_with_current_evidence(self):
        base_sources = {source["id"]: source for source in self.base_runtime["sources"]}
        current_sources = {source["id"]: source for source in self.runtime["sources"]}
        for key, record in self.batch_items.items():
            old_ids = record["previous_source_ids"]
            retired = {row["id"]: row for row in record["retired_sources"]}
            retained = [source_id for source_id in old_ids if source_id not in retired]
            self.assertEqual(record["source_ids"][:len(retained)], retained)
            self.assertEqual(set(old_ids) - set(record["source_ids"]), set(retired))
            for source_id, row in retired.items():
                self.assertEqual(current_sources[source_id], base_sources[source_id])
                self.assertEqual(row["prior_source_sha256"], hashlib.sha256(
                    json.dumps(base_sources[source_id], ensure_ascii=False, sort_keys=True).encode("utf-8")
                ).hexdigest())

    def test_frequency_and_taiwan_law_limits_are_explicit(self):
        stone = self.items["TW-16-008"]["body"]
        hbv = self.items["TW-16-011"]["body"]
        diabetes = self.items["TW-16-007"]["body"]
        shortage = self.items["TW-24-013"]["body"]
        self.assertIn("1年及5年復發率分別為6.12%及34.71%", stone)
        self.assertIn("盛行率也不是目前的年發生率或個人罹病機率", stone)
        self.assertIn("2026年8月19日起實施的第九版", hbv)
        self.assertIn("2025年11月4日公布", hbv)
        self.assertNotIn("2026年4月刊行", hbv)
        self.assertIn("41,779人年", hbv)
        self.assertIn("各年度糖尿病患者中的足部潰瘍盛行率為0.52%至0.76%", diabetes)
        self.assertIn("不能由百分比自行推算", diabetes)
        self.assertIn("第26條", shortage)
        self.assertIn("2024年6月20日修正公布、同年8月1日施行", shortage)
        self.assertIn("3項臨床必要的化療注射藥", shortage)
        self.assertIn("不是缺藥患者人數、藥局缺貨率或目前每家院所的庫存", shortage)

    def test_new_source_bundle_and_counts_do_not_claim_publication_ready(self):
        source_rows = read_json(SOURCE_INDEX)["sources"]
        coverage = read_json("localization/tw-edition/coverage.json")
        self.assertEqual({row[0] for row in source_rows}, set(self.batch["new_source_ids"]))
        for row in source_rows:
            self.assertEqual(row, [self.sources[row[0]]["id"], self.sources[row[0]]["title"],
                                   self.sources[row[0]]["url"], self.sources[row[0]]["supports"]])
        after = self.batch["counts_after"]
        self.assertGreaterEqual(coverage["core_reviewed_entries"], after["core_reviewed"])
        self.assertGreaterEqual(len(self.runtime["items"]), after["runtime_items"])
        self.assertGreaterEqual(len(self.runtime["sources"]), after["runtime_sources"])
        self.assertGreaterEqual(coverage["registry_sources"], after["source_registry"])
        self.assertGreaterEqual(coverage["json_files_checked"], after["json_files_checked"])
        self.assertGreaterEqual(len(self.register["substantive_rechecks"]), after["substantive_rechecks"])
        self.assertFalse(coverage["publication_ready"])


if __name__ == "__main__":
    unittest.main()

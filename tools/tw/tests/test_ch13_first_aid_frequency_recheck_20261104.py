"""第13章六篇急救內容的台灣情境、來源版本與回溯證據契約。"""
import hashlib
import json
import re
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from review_contract import ROOT, validate_runtime
from retroactive_audit import validate_recheck_history


BASE = "5b0235927b13f544aac9a46d9e618e4cae0ec120"
HISTORICAL_HEAD = "1e2d6a4904123d09217c50c50107df76c7b3e80f"
BATCH_PATH = "localization/ch13-p0-first-aid-frequency-recheck-20261104.json"
SOURCE_PATH = "localization/tw-edition/sources/ch13-p0-first-aid-frequency-recheck-20261104.json"
ITEM_IDS = (
    "TW-13-017",
    "TW-13-023",
    "TW-13-014",
    "TW-13-018",
    "TW-13-021",
    "TW-13-046",
)
VERSIONED_SOURCES = {
    "ch13_chemical_nfa_20261104",
    "ch13_heat_firstaid_20261104",
    "ch13_hypo_hpa_20261104",
    "alcohol_cch_202512_20261104",
    "alcohol_tpech_202606_20261104",
    "ch13_hypo_ada_swallow_20261104",
    "ch13_heat_dataset_20261104",
    "ch13_alcohol_niaaa_20261104",
}


def read_json(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


class Chapter13FirstAidFrequencyRecheckTests(unittest.TestCase):
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
        cls.source_rows = read_json(SOURCE_PATH)["sources"]
        cls.baseline_runtime = json.loads(
            subprocess.check_output(
                ["git", "show", f"{BASE}:localization/tw-edition/runtime.json"],
                cwd=ROOT,
                text=True,
            )
        )
        cls.baseline_sources = {
            source["id"]: source for source in cls.baseline_runtime["sources"]
        }

    def test_six_rechecks_preserve_append_only_hash_and_review_edges(self):
        self.assertEqual(self.batch["baseline_main_sha"], BASE)
        self.assertEqual(self.batch["reviewed_at"], "2026-11-04")
        self.assertEqual(self.batch["review_due_at"], "2027-02-04")
        self.assertEqual(set(self.batch_items), set(ITEM_IDS))
        self.assertEqual(self.batch["professional_review"]["obtained"], False)
        self.assertTrue(self.batch["professional_review"]["required"])

        baseline_items = {item["id"]: item for item in self.baseline_runtime["items"]}
        for item_id in ITEM_IDS:
            with self.subTest(item_id=item_id):
                item = self.runtime_items[item_id]
                record = self.batch_items[item_id]
                review = self.reviews[item_id]
                manifest_item = self.manifest_items[item_id]
                if item_id == "TW-13-021":
                    # A later append-only follow-up supersedes this item in the
                    # current runtime. Keep the 2026-11-04 edge verifiable from
                    # its immutable committed snapshot instead of comparing it
                    # with the newer live body and review.
                    historical_runtime = json.loads(
                        subprocess.check_output(
                            ["git", "show", f"{HISTORICAL_HEAD}:localization/tw-edition/runtime.json"],
                            cwd=ROOT,
                            text=True,
                        )
                    )
                    item = next(
                        row for row in historical_runtime["items"] if row["id"] == item_id
                    )
                    review = json.loads(
                        subprocess.check_output(
                            ["git", "show", f"{HISTORICAL_HEAD}:localization/reviews/{item_id}.json"],
                            cwd=ROOT,
                            text=True,
                        )
                    )
                    historical_manifest = json.loads(
                        subprocess.check_output(
                            ["git", "show", f"{HISTORICAL_HEAD}:localization/manifest.json"],
                            cwd=ROOT,
                            text=True,
                        )
                    )
                    manifest_item = next(
                        row for row in historical_manifest["entries"] if row["id"] == item_id
                    )
                body_path = ROOT / item["target_path"]
                body = body_path.read_text(encoding="utf-8")
                body_sha = hashlib.sha256(body_path.read_bytes()).hexdigest()
                if item_id == "TW-13-021":
                    body = item["body"]
                    body_sha = hashlib.sha256(body.encode("utf-8")).hexdigest()
                previous_body = subprocess.check_output(
                    ["git", "show", f"{BASE}:{item['target_path']}"], cwd=ROOT
                )
                history = [
                    row
                    for row in self.register["substantive_rechecks"]
                    if row["id"] == item_id and row["reviewed_at"] == "2026-11-04"
                ]

                self.assertEqual(len(history), 1)
                self.assertEqual(history[0], record)
                self.assertEqual(record["before_sha256"], hashlib.sha256(previous_body).hexdigest())
                self.assertEqual(record["after_sha256"], body_sha)
                self.assertEqual(item["body"], body)
                self.assertEqual(record["body"], body)
                self.assertEqual(review["target_sha256"], body_sha)
                self.assertEqual(review["source_reviewed_sha256"], body_sha)
                self.assertEqual(review["source_checks"], record["source_checks"])
                self.assertEqual(review["reviewed_at"], "2026-11-04")
                self.assertEqual(review["review_due_at"], "2027-02-04")
                self.assertEqual(
                    review["reader_copy_cleanup"],
                    json.loads(
                        subprocess.check_output(
                            ["git", "show", f"{BASE}:localization/reviews/{item_id}.json"],
                            cwd=ROOT,
                            text=True,
                        )
                    )["reader_copy_cleanup"],
                )
                self.assertEqual(manifest_item["target_path"], item["target_path"])
                self.assertEqual(manifest_item["sources"], item["source_ids"])
                self.assertEqual(manifest_item["status"], "verified")
                self.assertEqual(record["status"], "ai_source_rechecked_professional_pending")

                body_urls = set(re.findall(r"\]\((https?://[^)]+)\)", body))
                runtime_urls = {
                    self.runtime_sources[source_id]["url"]
                    for source_id in item["source_ids"]
                }
                review_urls = {check["url"] for check in review["source_checks"]}
                self.assertEqual(body_urls, runtime_urls)
                self.assertEqual(review_urls, runtime_urls)
                self.assertEqual(set(record["source_ids"]), set(item["source_ids"]))
                self.assertNotRegex(
                    body,
                    r"(?:批次摘要|PR\s*#\d+|CI\s*(?:成功|通過)|(?:本次|本輪).{0,16}(?:AI|審查|再審|核對))",
                )
                if item_id != "TW-13-021":
                    validate_recheck_history(ROOT, record, item)

                baseline_ids = set(baseline_items[item_id]["source_ids"])
                retired = {row["id"]: row for row in record["retired_sources"]}
                self.assertEqual(baseline_ids - set(item["source_ids"]), set(retired))
                for source_id, source_record in retired.items():
                    if source_id not in self.baseline_sources:
                        continue
                    baseline_source = self.baseline_sources[source_id]
                    self.assertEqual(self.runtime_sources[source_id], baseline_source)
                    expected_hash = hashlib.sha256(
                        json.dumps(
                            baseline_source, ensure_ascii=False, sort_keys=True
                        ).encode("utf-8")
                    ).hexdigest()
                    self.assertEqual(source_record["prior_source_sha256"], expected_hash)

    def test_rechecked_source_versions_and_registry_rows_are_synchronized(self):
        evidence_by_id = {row[0]: row for row in self.source_rows}
        self.assertEqual(set(self.batch["new_source_ids"]), set(evidence_by_id))
        self.assertTrue(VERSIONED_SOURCES.issubset(set(self.batch["new_source_ids"])))
        for source_id, row in evidence_by_id.items():
            source = self.runtime_sources[source_id]
            self.assertEqual(
                row,
                [source["id"], source["title"], source["url"], source["supports"]],
            )
            self.assertEqual(source["accessed_at"], "2026-11-04")

        for source_id, source in self.baseline_sources.items():
            self.assertEqual(self.runtime_sources[source_id], source)

        self.assertEqual(
            self.runtime_sources["ch13_heat_firstaid_20261104"]["url"],
            "https://www.hpa.gov.tw/Pages/Detail.aspx?nodeid=577&pid=10751&sid=18379",
        )
        self.assertNotIn("sid=18380", self.runtime_sources["ch13_heat_firstaid_20261104"]["url"])

    def test_heat_and_burn_statistics_keep_their_actual_units_and_limits(self):
        heat = self.batch_items["TW-13-023"]
        heat_stats = heat["statistics_assessed"]
        self.assertEqual([row["value"] for row in heat_stats], [3942, 3496, 2919])
        self.assertEqual(
            [row["period"] for row in heat_stats],
            ["2024-01-01至2024-12-31", "2025-01-01至2025-12-31", "2026-01-01至2026-10-26"],
        )
        for row in heat_stats:
            self.assertEqual(row["kind"], "monitored_medical_visits")
            self.assertEqual(row["denominator"], None)
            self.assertEqual(row["source_id"], "ch13_heat_dataset_20261104")
            self.assertIn("非唯一患者", row["limitations"])
            self.assertIn("無人口或曝險分母", row["limitations"])
        heat_source = self.runtime_sources["ch13_heat_dataset_20261104"]
        self.assertIn("de59b386382753110b1b0be3ded3debba2102661385b614a0e6921af11ae76b8", heat_source["supports"])
        self.assertIn("未涵蓋所有醫療院所", heat_source["supports"])
        self.assertIn("不是全國病例總數、個案發生率或個人風險", heat["body"])

        burn = self.batch_items["TW-13-014"]["statistics_assessed"][0]
        self.assertEqual(burn["period"], "2010")
        self.assertEqual(burn["numerator"], 7630)
        self.assertEqual(burn["denominator"], 1000000)
        self.assertEqual(burn["value"], 763.0)
        self.assertEqual(burn["unit"], "每10萬人年")
        self.assertIn("不含未就醫燒傷", burn["limitations"])

        for item_id in ("TW-13-017", "TW-13-018", "TW-13-021", "TW-13-046"):
            with self.subTest(item_id=item_id):
                assessment = self.batch_items[item_id]["statistics_assessed"][0]
                self.assertEqual(assessment["kind"], "frequency_not_estimated")
                self.assertIsNone(assessment["numerator"])
                self.assertIsNone(assessment["denominator"])
                self.assertTrue(assessment["limitations"].strip())

    def test_chemical_powder_and_urgent_actions_are_not_overgeneralized(self):
        body = self.runtime_items["TW-13-021"]["body"]
        self.assertIn("化學液體濺入眼睛時", body)
        self.assertIn("持續沖洗至少15分鐘", body)
        self.assertIn("成分不明的乾粉或粉狀／金屬化學品入眼時", body)
        self.assertIn("無法由這些資料確認是否適合直接沖洗", body)
        self.assertIn("立即聯絡24小時毒藥物防治諮詢中心", body)
        self.assertIn("安排就近急診", body)
        self.assertIn("不要等回電", body)
        self.assertIn("撥119", body)
        self.assertNotIn("粉末本身不代表一律不能用水", body)
        self.assertIn("眼球穿破", body)

    def test_coverage_counts_remain_consistent_and_not_publication_ready(self):
        coverage = read_json("localization/tw-edition/coverage.json")
        counts = self.batch["counts_after"]
        baseline_coverage = json.loads(subprocess.check_output(
            ["git", "show", f"{BASE}:localization/tw-edition/coverage.json"],
            cwd=ROOT,
            text=True,
        ))
        self.assertEqual(baseline_coverage["publication_completed_entries"], counts["core_completed"])
        self.assertGreaterEqual(coverage["core_reviewed_entries"], counts["core_completed"])
        self.assertGreaterEqual(coverage["registry_sources"], counts["registry_sources"])
        self.assertGreaterEqual(coverage["json_files_checked"], counts["json_files"])
        self.assertEqual(coverage["publication_ready"], False)
        self.assertEqual(counts["publication_ready"], False)
        self.assertGreaterEqual(len(self.runtime["items"]), counts["runtime_items"])
        self.assertGreaterEqual(len(self.runtime["sources"]), counts["runtime_sources"])


if __name__ == "__main__":
    unittest.main()

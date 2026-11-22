"""第13章溺水急救與危機守門人統計再審及跨篇主題保真契約。"""
import hashlib
import json
import re
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools/tw"))

from retroactive_audit import validate_recheck_history
from review_contract import validate_runtime

BASE = "df9344795067a3fa3bcf83de205a576c88a5d08f"
DATE = "2026-11-22"
DUE = "2027-02-22"
BATCH_PATH = "localization/ch13-drowning-suicide-recheck-20261122.json"
BUNDLE_PATH = "localization/tw-edition/sources/ch13-drowning-suicide-recheck-20261122.json"
REGISTER_PATH = "localization/retroactive-review-register-20261019.json"
ITEMS = ("TW-13-025", "TW-01-043")
NEW_SOURCE_IDS = (
    "ch13_sem_drowning_resuscitation_20260430",
    "ch13_aha_drowning_cpr_2025",
)
FIDELITY_ITEMS = ("TW-02-036", "TW-01-041")


def read(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def read_at(revision, path, *, json_value=True):
    raw = subprocess.check_output(["git", "show", f"{revision}:{path}"], cwd=ROOT)
    return json.loads(raw) if json_value else raw


def sha256(data):
    return hashlib.sha256(data).hexdigest()


class DrowningSuicideRecheckTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.runtime = validate_runtime()
        cls.items = {item["id"]: item for item in cls.runtime["items"]}
        cls.sources = {source["id"]: source for source in cls.runtime["sources"]}
        cls.manifest = {item["id"]: item for item in read("localization/manifest.json")["entries"]}
        cls.reviews = {item_id: read(f"localization/reviews/{item_id}.json") for item_id in ITEMS}
        cls.register = read(REGISTER_PATH)
        cls.batch = read(BATCH_PATH)
        cls.batch_items = {item["id"]: item for item in cls.batch["items"]}

    def test_batch_is_append_only_and_matches_live_article_runtime_and_review(self):
        baseline_runtime = read_at(BASE, "localization/tw-edition/runtime.json")
        baseline_manifest = {item["id"]: item for item in read_at(BASE, "localization/manifest.json")["entries"]}
        baseline_register = read_at(BASE, REGISTER_PATH)["substantive_rechecks"]
        baseline_coverage = read_at(BASE, "localization/tw-edition/coverage.json")
        current_coverage = read("localization/tw-edition/coverage.json")
        rows = self.register["substantive_rechecks"]

        self.assertEqual(self.batch["baseline_main_sha"], BASE)
        self.assertEqual((self.batch["reviewed_at"], self.batch["review_due_at"]), (DATE, DUE))
        self.assertEqual(self.batch["risk_order"], list(ITEMS))
        self.assertEqual(set(self.batch_items), set(ITEMS))
        self.assertEqual(self.batch["new_source_ids"], list(NEW_SOURCE_IDS))
        self.assertEqual(rows[:len(baseline_register)], baseline_register)
        self.assertEqual(len(rows), len(baseline_register) + len(ITEMS))
        before = self.batch["counts_before"]
        after = self.batch["counts_after"]
        self.assertEqual(before["substantive_rechecks"], len(baseline_register))
        self.assertEqual(before["runtime_items"], len(baseline_runtime["items"]))
        self.assertEqual(before["runtime_sources"], len(baseline_runtime["sources"]))
        self.assertEqual(before["core_completed"], baseline_coverage["publication_completed_entries"])
        self.assertEqual(after["substantive_rechecks"], len(rows))
        self.assertEqual(after["runtime_items"], len(self.runtime["items"]))
        self.assertEqual(after["runtime_sources"], len(self.runtime["sources"]))
        self.assertEqual(after["source_registry"], current_coverage["registry_sources"])
        self.assertEqual(after["coverage_json_files"], current_coverage["json_files_checked"])
        self.assertEqual(after["core_completed"], current_coverage["publication_completed_entries"])
        self.assertEqual(after["core_total"], current_coverage["publication_total_entries"])
        self.assertEqual(after["unresolved_source_id_kinds"], len(current_coverage["unresolved_source_ids"]))
        self.assertEqual(after["unresolved_reference_occurrences"], current_coverage["unresolved_reference_occurrences"])
        self.assertEqual(after["publication_ready"], current_coverage["publication_ready"])
        self.assertFalse(self.batch["counts_after"]["publication_ready"])
        self.assertEqual(self.batch["professional_review"]["obtained"], False)
        self.assertTrue(self.batch["professional_review"]["required"])

        bundle = read(BUNDLE_PATH)
        self.assertEqual(bundle["checked_at"], DATE)
        self.assertEqual({row[0] for row in bundle["sources"]}, set(NEW_SOURCE_IDS))
        source_map = {source["id"]: source for source in self.runtime["sources"]}
        for source_id, title, url, supports in bundle["sources"]:
            source = source_map[source_id]
            self.assertEqual((source["title"], source["url"], source["supports"]), (title, url, supports))

        for item_id in ITEMS:
            with self.subTest(item_id=item_id):
                body_path = self.manifest[item_id]["target_path"]
                body_bytes = (ROOT / body_path).read_bytes()
                body = body_bytes.decode("utf-8")
                digest = sha256(body_bytes)
                runtime_item = self.items[item_id]
                manifest_item = self.manifest[item_id]
                review = self.reviews[item_id]
                record = self.batch_items[item_id]
                histories = [row for row in rows if row["id"] == item_id and row["reviewed_at"] == DATE]
                self.assertEqual(len(histories), 1)
                history = histories[0]
                baseline_item = next(row for row in baseline_runtime["items"] if row["id"] == item_id)
                baseline_entry = baseline_manifest[item_id]
                previous_body = subprocess.check_output(
                    ["git", "show", f"{BASE}:{baseline_entry['target_path']}"], cwd=ROOT
                )
                prior_review = read_at(BASE, f"localization/reviews/{item_id}.json", json_value=False)

                self.assertEqual(history, record)
                self.assertEqual(record["prior_revision"], BASE)
                self.assertEqual(record["previous_body"].encode("utf-8"), previous_body)
                self.assertEqual(record["before_sha256"], sha256(previous_body))
                self.assertEqual(record["before_sha256"], sha256(record["previous_body"].encode("utf-8")))
                self.assertEqual(record["prior_review_sha256"], sha256(prior_review))
                self.assertEqual(record["prior_reviewed_at"], baseline_item["reviewed_at"])
                self.assertEqual(record["prior_review_due_at"], baseline_item["review_due_at"])
                self.assertEqual(record["after_sha256"], digest)
                self.assertEqual(record["source_reviewed_sha256"], digest)
                self.assertEqual(record["review_sha256"], sha256((ROOT / f"localization/reviews/{item_id}.json").read_bytes()))
                self.assertEqual(record["source_bundle_sha256"], sha256((ROOT / BUNDLE_PATH).read_bytes()))
                self.assertEqual(record["status"], "ai_source_rechecked_professional_pending")
                self.assertEqual(record["professional_review"]["status"], "pending")
                self.assertEqual(record["professional_review"]["obtained"], False)
                self.assertEqual(record["review_due_at"], DUE)
                self.assertEqual(record["source_ids"], runtime_item["source_ids"])
                self.assertEqual(record["source_ids"], manifest_item["sources"])
                self.assertEqual(record["source_ids"], review["source_ids"])
                self.assertEqual(runtime_item["body"], body)
                self.assertEqual(runtime_item["reviewed_at"], DATE)
                self.assertEqual(runtime_item["review_due_at"], DUE)
                self.assertEqual(manifest_item["verified_at"], DATE)
                self.assertEqual(review["target_sha256"], digest)
                self.assertEqual(review["source_reviewed_sha256"], digest)
                self.assertEqual(review["reviewed_at"], DATE)
                self.assertEqual(review["review_due_at"], DUE)
                self.assertEqual(review["source_checks"], record["source_checks"])
                self.assertEqual(review["limits"], record["limits"])
                self.assertIn(record["limits"][0], review["limits"])
                self.assertNotRegex(record["limits"][0], r"本批|本輪|AI|專業審閱仍待")

                source_urls = {source_map[source_id]["url"] for source_id in record["source_ids"]}
                body_urls = re.findall(r"\]\((https://[^)]+)\)", body)
                review_urls = {check["url"] for check in review["source_checks"]}
                self.assertEqual(set(body_urls), source_urls)
                self.assertEqual(len(body_urls), len(set(body_urls)), "正文有重複來源連結")
                self.assertEqual(review_urls, source_urls)
                self.assertEqual({check["source_id"] for check in review["source_checks"]}, set(record["source_ids"]))
                self.assertNotRegex(body, r"本批|本輪再審|來源實質再核對|PR\s*#|CI\s*(?:通過|成功)|專業審閱仍待")
                validate_recheck_history(ROOT, record, runtime_item)

    def test_statistics_preserve_event_definitions_denominators_and_reader_boundaries(self):
        suicide = self.batch_items["TW-01-043"]
        drowning = self.batch_items["TW-13-025"]
        suicide_stats = suicide["statistics_assessed"]
        self.assertEqual(len(suicide_stats), 2)
        notifications = next(row for row in suicide_stats if "34,612" in row["value"])
        deaths = next(row for row in suicide_stats if "3,951" in row["value"])
        self.assertIsNone(notifications["denominator"])
        self.assertIn("無暴露分母", notifications["limitations"])
        self.assertIn("不是唯一個案", notifications["limitations"])
        self.assertIn("WHO 2000", deaths["population"])
        self.assertIn("12.9", deaths["value"])
        self.assertIn("非個人機率", deaths["denominator_definition"])
        for stat in suicide_stats:
            for field in (
                "unit", "period", "geographic_scope", "population", "numerator",
                "denominator_definition", "event_definition", "data_type", "source_id",
                "accessed_at", "checked_at", "limitations",
            ):
                self.assertTrue(stat.get(field), (stat, field))

        drowning_stats = drowning["statistics_assessed"]
        self.assertEqual(len(drowning_stats), 2)
        self.assertTrue(any("4,597" in row["value"] and "2,888" in row["value"] for row in drowning_stats))
        recorded = next(row for row in drowning_stats if "1,056" in row["value"])
        self.assertIsNone(recorded["denominator"])
        self.assertIn("不是致死率", recorded["limitations"])
        self.assertNotIn("個人發生率", drowning["frequency_assessment"])
        self.assertIn("沒有水域活動人次或暴露時間分母", drowning["frequency_assessment"])
        self.assertLess(self.items["TW-13-025"]["body"].index("打119"), self.items["TW-13-025"]["body"].index("4,597"))
        self.assertIn("不等待AED", self.items["TW-13-025"]["body"])
        self.assertIn("人工呼吸", self.items["TW-13-025"]["body"])
        self.assertIn("年齡標準化死亡率", self.items["TW-01-043"]["body"])
        self.assertEqual(suicide["professional_review"]["status"], "pending")
        self.assertEqual(drowning["professional_review"]["status"], "pending")

    def test_japanese_bathing_research_is_preserved_and_ice_topic_is_taiwan_adapted(self):
        for item_id in FIDELITY_ITEMS:
            with self.subTest(item_id=item_id):
                path = self.manifest[item_id]["target_path"]
                current_body = (ROOT / path).read_bytes()
                baseline_body = subprocess.check_output(["git", "show", f"{BASE}:{path}"], cwd=ROOT)
                self.assertEqual(current_body, baseline_body)
                self.assertEqual(
                    self.items[item_id],
                    next(row for row in read_at(BASE, "localization/tw-edition/runtime.json")["items"] if row["id"] == item_id),
                )
                self.assertEqual(
                    (ROOT / f"localization/reviews/{item_id}.json").read_bytes(),
                    read_at(BASE, f"localization/reviews/{item_id}.json", json_value=False),
                )

        bath_path = self.manifest["TW-02-036"]["target_path"]
        bath = (ROOT / bath_path).read_text(encoding="utf-8")
        bath_review = read("localization/reviews/TW-02-036.json")
        self.assertIn("日本JAGES", bath)
        self.assertIn("日本世代研究", bath)
        self.assertIn("538,373人年", bath)
        bath_runtime = self.items["TW-02-036"]
        self.assertIn("tw02_jphc_tub_bathing_cv_2020", bath_runtime["source_ids"])
        self.assertIn("不是死亡或壽命", bath)
        self.assertIn("觀察性研究", bath)
        self.assertIn("TW-02-036", bath_review["id"])
        self.assertEqual(bath_review["reviewed_at"], "2026-11-12")

        mountain = (ROOT / self.manifest["TW-01-041"]["target_path"]).read_text(encoding="utf-8")
        self.assertIn("臺灣登山行程", mountain)
        self.assertIn("119或112", mountain)
        self.assertIn("雪季或高海拔結冰路段", mountain)
        self.assertNotIn("湖面結冰", mountain)
        self.assertEqual(read("localization/reviews/TW-01-041.json")["reviewed_at"], "2026-11-12")


if __name__ == "__main__":
    unittest.main()

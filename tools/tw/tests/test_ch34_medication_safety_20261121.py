"""第34章四篇家庭用藥安全首次正式發布契約。"""
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
from review_contract import publication_report, validate_runtime
from source_bundle_test_support import source_bundle_ids_added_since

BASE = "0d27d112740dd9c237387a04f202ff7b4e8fa5d2"
DATE = "2026-11-21"
DUE = "2027-02-21"
REGISTER = "localization/retroactive-review-register-20261019.json"
SOURCE_BUNDLE = "localization/tw-edition/sources/ch34-medication-safety-20261121.json"
STAGE = "localization/ch34-medication-safety-20261121.json"
ARTICLES = {
    "TW-34-001": {
        "title": "感冒藥、止痛藥併用前，先確認乙醯胺酚沒有重複",
        "path": "locales/zh-TW/book/ch34/TW-34-001.md",
        "source_ids": ["tw34_tfda_acetaminophen_2024", "tw34_mohw_acetaminophen_label", "ch01_vghtpe_poison_hotline_20261108", "ch13_pcc_poison_20261103"],
    },
    "TW-34-002": {
        "title": "孩子發燒用藥依藥袋與標示給，液體使用專用量具",
        "path": "locales/zh-TW/book/ch34/TW-34-002.md",
        "source_ids": ["tw34_hpa_child_health_handbook_2025", "tw34_pids_fever_2019", "tw34_tfda_child_med_2026"],
    },
    "TW-34-003": {
        "title": "使用布洛芬等非類固醇止痛藥前，先核對胃腎風險與其他用藥",
        "path": "locales/zh-TW/book/ch34/TW-34-003.md",
        "source_ids": ["tw34_tfda_nsaid_2024", "tw34_tfda_diclofenac_label"],
    },
    "TW-34-004": {
        "title": "幼兒感冒先由醫師評估，不自行選用綜合感冒藥",
        "path": "locales/zh-TW/book/ch34/TW-34-004.md",
        "source_ids": ["tw34_tfda_combo_cold_2024", "tw34_tfda_child_med_2026"],
    },
}
NEW_SOURCE_IDS = {
    "tw34_tfda_acetaminophen_2024",
    "tw34_mohw_acetaminophen_label",
    "tw34_hpa_child_health_handbook_2025",
    "tw34_pids_fever_2019",
    "tw34_tfda_child_med_2026",
    "tw34_tfda_combo_cold_2024",
    "tw34_tfda_nsaid_2024",
    "tw34_tfda_diclofenac_label",
}
REUSED_SOURCE_IDS = {
    "ch01_vghtpe_poison_hotline_20261108",
    "ch13_pcc_poison_20261103",
}
ALL_SOURCE_IDS = {sid for article in ARTICLES.values() for sid in article["source_ids"]}


def read(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def git_bytes(revision, path):
    result = subprocess.run(["git", "show", f"{revision}:{path}"], cwd=ROOT, capture_output=True)
    return result.stdout if result.returncode == 0 else None


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


class Chapter34MedicationSafetyPublicationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.runtime = validate_runtime()
        cls.items = {row["id"]: row for row in cls.runtime["items"]}
        cls.sources = {row["id"]: row for row in cls.runtime["sources"]}
        cls.manifest = {row["id"]: row for row in read("localization/manifest.json")["entries"]}
        cls.reviews = {key: read(f"localization/reviews/{key}.json") for key in ARTICLES}
        cls.articles = {key: (ROOT / spec["path"]).read_bytes() for key, spec in ARTICLES.items()}
        cls.bodies = {key: raw.decode("utf-8") for key, raw in cls.articles.items()}
        cls.bundle = read(SOURCE_BUNDLE)
        cls.stage = read(STAGE)
        cls.coverage = read("localization/tw-edition/coverage.json")
        cls.register = read(REGISTER)
        cls.batch_items = {row["id"]: row for row in cls.stage["items"]}

    def test_first_publication_preserves_fixed_ids_and_does_not_falsely_count_historical_rechecks(self):
        self.assertEqual(self.stage["baseline_main_sha"], BASE)
        baseline_manifest = {row["id"]: row for row in json.loads(git_bytes(BASE, "localization/manifest.json"))["entries"]}
        baseline_register = json.loads(git_bytes(BASE, REGISTER))
        baseline_runtime = json.loads(git_bytes(BASE, "localization/tw-edition/runtime.json"))
        self.assertIsNone(git_bytes(BASE, "localization/tw-edition/chapters/34.json"))
        for key, spec in ARTICLES.items():
            with self.subTest(id=key):
                old = baseline_manifest[key]
                self.assertEqual((old["status"], old["treatment"], old["target_path"], old["sources"]),
                                 ("pending", "unclassified", None, []))
                self.assertIsNone(git_bytes(BASE, spec["path"]))
                self.assertIsNone(git_bytes(BASE, f"localization/reviews/{key}.json"))
                current = self.manifest[key]
                self.assertEqual((current["status"], current["treatment"], current["verified_at"]),
                                 ("verified", "taiwan_independent_rewrite", DATE))
                self.assertEqual(current["upstream_commit"], old["upstream_commit"])
                self.assertEqual(current["upstream_text_sha256"], old["upstream_text_sha256"])
                self.assertEqual(current["target_path"], spec["path"])
                self.assertEqual(current["sources"], spec["source_ids"])
        self.assertEqual(
            self.register["unpublished_core_inventory"],
            baseline_register["unpublished_core_inventory"],
        )
        inventory = {row["id"] for row in self.register["unpublished_core_inventory"]}
        self.assertTrue(set(ARTICLES).issubset(inventory))
        self.assertEqual(self.register["substantive_rechecks"], baseline_register["substantive_rechecks"])
        self.assertEqual(self.stage["counts_before"]["review_rechecks"], len(baseline_register["substantive_rechecks"]))
        self.assertEqual(self.stage["counts_after"]["review_rechecks"], len(baseline_register["substantive_rechecks"]))
        self.assertEqual(len(self.runtime["items"]), len(baseline_runtime["items"]) + len(ARTICLES))

    def test_body_runtime_review_manifest_sources_and_sha_are_bound(self):
        baseline_runtime = json.loads(git_bytes(BASE, "localization/tw-edition/runtime.json"))
        baseline_ids = [row["id"] for row in baseline_runtime["items"]]
        current_ids = [row["id"] for row in self.runtime["items"]]
        self.assertEqual([key for key in current_ids if key in set(baseline_ids)], baseline_ids)
        self.assertTrue(all(current_ids.index(key) > max(current_ids.index(old) for old in baseline_ids) for key in ARTICLES))
        chapter = (ROOT / "locales/zh-TW/book/ch34/README.md").read_text(encoding="utf-8")
        index = (ROOT / "locales/zh-TW/README.md").read_text(encoding="utf-8")
        self.assertEqual(index.count("[第34章：家庭用藥安全](book/ch34/README.md)"), 1)
        self.assertEqual([int(n) for n in re.findall(r"TW-34-(\d{3})\.md", chapter)], [1, 2, 3, 4])
        for key, spec in ARTICLES.items():
            with self.subTest(id=key):
                body = self.bodies[key]
                digest = sha(self.articles[key])
                item, entry, review = self.items[key], self.manifest[key], self.reviews[key]
                batch = self.batch_items[key]
                self.assertEqual(item["body"], body)
                self.assertEqual(item["title"], spec["title"])
                self.assertEqual(re.search(r"^# (.+)$", body, re.MULTILINE).group(1), spec["title"])
                self.assertEqual(item["target_path"], spec["path"])
                self.assertEqual(item["source_ids"], spec["source_ids"])
                self.assertEqual(item["review_status"], "source_checked")
                self.assertEqual((item["reviewed_at"], item["review_due_at"]), (DATE, DUE))
                self.assertEqual((review["target_sha256"], review["source_reviewed_sha256"]), (digest, digest))
                self.assertEqual(batch["after_sha256"], digest)
                self.assertEqual(batch["target_sha256"], digest)
                self.assertIsNone(review["before_sha256"])
                self.assertEqual((review["after_sha256"], review["review_due_at"]), (digest, DUE))
                self.assertEqual(review["source_bundle_path"], SOURCE_BUNDLE)
                self.assertEqual(review["source_bundle_sha256"], sha((ROOT / SOURCE_BUNDLE).read_bytes()))
                self.assertEqual(review["source_ids"], spec["source_ids"])
                self.assertTrue(review["professional_review"]["required"])
                self.assertFalse(review["professional_review"]["obtained"])
                self.assertTrue(review["unresolved_questions"])
                self.assertEqual(review["statistics_assessed"], [])
                self.assertEqual({row["source_id"] for row in review["source_checks"]}, set(spec["source_ids"]))
                source_urls = {self.sources[sid]["url"] for sid in spec["source_ids"]}
                self.assertEqual(set(re.findall(r"\]\((https://[^)]+)\)", body)), source_urls)
                self.assertNotRegex(body, r"(批次摘要|AI協助|本次.{0,12}(?:審查|再審|核對)|CI\s*(?:成功|通過)|PR\s*#\d+|待專業審閱|fork管理)")

    def test_taiwan_actions_topic_fidelity_and_frequency_limits(self):
        one = self.bodies["TW-34-001"]
        self.assertIn("乙醯胺酚", one)
        self.assertIn("02-2871-7121", one)
        self.assertIn("不要等到", one)
        self.assertNotIn("27%", one)
        self.assertNotIn("2克", one)
        child = self.bodies["TW-34-002"]
        self.assertIn("18歲以下", child)
        self.assertIn("未滿三個月", child)
        self.assertIn("餵藥器", child)
        self.assertIn("不要用家中茶匙、湯匙", child)
        self.assertNotIn("尼美舒利", child)
        self.assertNotIn("安乃近", child)
        nsaid = self.bodies["TW-34-003"]
        self.assertIn("抗凝血劑", nsaid)
        self.assertIn("不要因為想吃止痛藥就自行停掉原處方", nsaid)
        self.assertIn("吐血、黑便", nsaid)
        self.assertNotIn("60歲以上", nsaid)
        self.assertNotIn("4倍", nsaid)
        cold = self.bodies["TW-34-004"]
        self.assertIn("六歲以下幼童就醫", cold)
        self.assertIn("不代表所有產品在臺灣一律禁止", cold)
        self.assertIn("症狀持續三天", cold)
        for key, review in self.reviews.items():
            self.assertIn("沒有", review["frequency_assessment"])
            self.assertTrue(review["limits"])
            self.assertTrue(review["professional_review"]["scope"])

    def test_new_sources_and_coverage_counts_match_live_data(self):
        self.assertEqual(self.bundle["checked_at"], DATE)
        self.assertEqual({row[0] for row in self.bundle["sources"]}, NEW_SOURCE_IDS)
        baseline_runtime = json.loads(git_bytes(BASE, "localization/tw-edition/runtime.json"))
        baseline_ids = {row["id"] for row in baseline_runtime["sources"]}
        baseline_sources = {row["id"]: row for row in baseline_runtime["sources"]}
        self.assertEqual(set(self.sources) - baseline_ids, NEW_SOURCE_IDS)
        self.assertTrue(REUSED_SOURCE_IDS.issubset(baseline_ids))
        for sid in REUSED_SOURCE_IDS:
            self.assertEqual(self.sources[sid], baseline_sources[sid])
        self.assertEqual(source_bundle_ids_added_since(ROOT, BASE), NEW_SOURCE_IDS)
        bundled = {row[0]: row for row in self.bundle["sources"]}
        for sid in NEW_SOURCE_IDS:
            source = self.sources[sid]
            self.assertEqual(bundled[sid], [source["id"], source["title"], source["url"], source["supports"]])
        self.assertEqual(self.coverage, audit_drafts())
        self.assertFalse(self.coverage["publication_ready"])
        self.assertEqual(self.coverage["publication_completed_entries"], publication_report()["publication_completed_entries"])
        self.assertTrue(set(ARTICLES).isdisjoint({row.split(":")[0] for row in self.coverage["publication_blockers"]}))
        before, after = self.stage["counts_before"], self.stage["counts_after"]
        self.assertEqual(after["manifest_entries"], before["manifest_entries"])
        self.assertEqual(after["verified_core_entries"], before["verified_core_entries"] + len(ARTICLES))
        self.assertEqual(after["runtime_items"], before["runtime_items"] + len(ARTICLES))
        self.assertEqual(after["runtime_sources"], before["runtime_sources"] + len(NEW_SOURCE_IDS))
        self.assertEqual(after["source_registry"], before["source_registry"] + len(NEW_SOURCE_IDS))
        self.assertEqual(after["coverage_json_files"], before["coverage_json_files"] + len(ARTICLES) + 2)
        self.assertEqual(after["review_rechecks"], before["review_rechecks"])
        self.assertFalse(after["publication_ready"])
        self.assertIsNone(self.sources["tw34_hpa_child_health_handbook_2025"]["published_at"])
        self.assertEqual(
            self.sources["tw34_tfda_diclofenac_label"]["url"],
            "https://www.fda.gov.tw/tc/includes/GetFile.ashx?id=f636694231200509957",
        )


if __name__ == "__main__":
    unittest.main()

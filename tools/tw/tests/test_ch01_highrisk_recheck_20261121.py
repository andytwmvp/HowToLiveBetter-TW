"""第1章高風險歷史內容於2026-11-21的實質再審契約。"""
import hashlib
import json
import re
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import retroactive_audit as audit
from review_contract import ROOT, publication_report, validate_runtime

BASE = "44b11fd28836d4fe109e207088c393629a4fa96c"
DATE = "2026-11-21"
DUE = "2027-02-21"
IDS = ("TW-01-012", "TW-01-025", "TW-01-033", "TW-01-046")
NEW_SOURCE_IDS = {
    "ch01_cga_118_hotline_20261121",
    "ch01_mohw_community_mental_health_centres_20261121",
    "ch01_co_nfa_20261121",
    "ch01_confined_osha_sequence_20260924",
    "ch01_osh_confined_space_warning_20231106",
}
BUNDLE = "localization/tw-edition/sources/ch01-highrisk-recheck-20261121.json"
EVIDENCE = "localization/ch01-highrisk-recheck-20261121.json"
REGISTER = "localization/retroactive-review-register-20261019.json"


def read(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def git_json(revision, path):
    return json.loads(subprocess.check_output(
        ["git", "show", f"{revision}:{path}"], cwd=ROOT))


def digest(value):
    return hashlib.sha256(value).hexdigest()


class Ch01HighriskRecheck20261121Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.runtime = validate_runtime()
        cls.items = {item["id"]: item for item in cls.runtime["items"]}
        cls.sources = {source["id"]: source for source in cls.runtime["sources"]}
        cls.manifest = {entry["id"]: entry for entry in read("localization/manifest.json")["entries"]}
        cls.reviews = {item_id: read(f"localization/reviews/{item_id}.json") for item_id in IDS}
        cls.register = read(REGISTER)
        cls.rows = cls.register["substantive_rechecks"]
        cls.batch_rows = {
            item_id: next(row for row in reversed(cls.rows)
                          if row["id"] == item_id and row["prior_revision"] == BASE)
            for item_id in IDS
        }
        cls.coverage = read("localization/tw-edition/coverage.json")
        cls.evidence = read(EVIDENCE)
        cls.bundle = read(BUNDLE)

    def test_articles_keep_emergency_actions_and_current_taiwan_context(self):
        bath = self.items["TW-01-012"]["body"]
        self.assertIn("家中浴盆、浴缸、水桶", bath)
        self.assertIn("溪流、漁港及沙灘", bath)
        self.assertIn("先求援", bath)
        self.assertIn("市話、行動電話及公用電話免付費", bath)
        self.assertIn("衛星電話或行動預付卡可能依電信費率收費", bath)
        self.assertNotIn("採用衛福部最新年齡別", bath)

        selfharm = self.items["TW-01-025"]["body"]
        self.assertLess(selfharm.index("先撥119"), selfharm.index("臺灣頻率背景"))
        self.assertIn("社區心理衛生中心", selfharm)
        self.assertIn("實際服務、預約方式與費用先向地方單位確認", selfharm)
        self.assertIn("34,612人次", selfharm)
        self.assertIn("死亡3,951人", selfharm)

        poison = self.items["TW-01-033"]["body"]
        self.assertLess(poison.index("先撥119"), poison.index("臺灣事件頻率"))
        self.assertIn("截至11月19日，全臺通報一氧化碳中毒事故12起、死亡1人、送醫48人", poison)
        self.assertIn("其中10起與屋外式熱水器裝在通風不足處有關", poison)
        self.assertIn("10／12是這12起事故中的原因分類，不是家庭中毒機率", poison)
        self.assertIn("沒有使用燃氣設備家戶數或暴露人次分母", poison)
        self.assertNotIn("2025年截至3月16日", poison)
        self.assertNotIn("ch01_co_nfa_2025", poison)

        confined = self.items["TW-01-046"]["body"]
        self.assertIn("雇主使勞工", confined)
        self.assertIn("先通風、再測定、後作業", confined)
        self.assertIn("通風不會取代測定、隔離、監視及救援安排", confined)
        self.assertIn("2024）列2件事故、2人死亡", confined)
        self.assertIn("沒有進入作業人次分母", confined)
        self.assertNotIn("2027-01-01施行", confined)

    def test_sources_hashes_reviews_and_append_only_history_are_synchronized(self):
        baseline_runtime = git_json(BASE, "localization/tw-edition/runtime.json")
        baseline_manifest = git_json(BASE, "localization/manifest.json")
        baseline_register = git_json(BASE, REGISTER)
        baseline_sources = {source["id"]: source for source in baseline_runtime["sources"]}
        baseline_items = {item["id"]: item for item in baseline_runtime["items"]}
        baseline_reviews = {
            item_id: subprocess.check_output(
                ["git", "show", f"{BASE}:localization/reviews/{item_id}.json"], cwd=ROOT)
            for item_id in IDS
        }

        self.assertEqual(self.rows[:len(baseline_register["substantive_rechecks"])],
                         baseline_register["substantive_rechecks"])
        self.assertEqual(self.runtime["sources"][:len(baseline_runtime["sources"])],
                         baseline_runtime["sources"])
        bundle_ids = {row[0] for row in self.bundle["sources"]}
        self.assertEqual(bundle_ids, NEW_SOURCE_IDS)
        self.assertTrue(NEW_SOURCE_IDS <= (set(self.sources) - set(baseline_sources)))

        for item_id in IDS:
            with self.subTest(item_id=item_id):
                item = self.items[item_id]
                review = self.reviews[item_id]
                row = self.batch_rows[item_id]
                manifest = self.manifest[item_id]
                body_bytes = (ROOT / item["target_path"]).read_bytes()
                body_sha = digest(body_bytes)

                self.assertEqual(row["before_sha256"], digest(baseline_items[item_id]["body"].encode()))
                self.assertEqual(row["previous_body"], baseline_items[item_id]["body"])
                self.assertEqual(row["prior_review_sha256"], digest(baseline_reviews[item_id]))
                self.assertEqual(row["after_sha256"], body_sha)
                self.assertEqual(item["body"].encode(), body_bytes)
                self.assertEqual((item["reviewed_at"], item["review_due_at"]), (DATE, DUE))
                self.assertEqual(manifest["verified_at"], DATE)
                self.assertEqual(manifest["sources"], item["source_ids"])
                self.assertEqual(review["source_ids"], item["source_ids"])
                self.assertEqual(review["target_sha256"], body_sha)
                self.assertEqual(review["source_reviewed_sha256"], body_sha)
                self.assertEqual(review["source_checks"], row["source_checks"])
                self.assertEqual(review["limits"], row["limits"])
                self.assertEqual(row["review_sha256"], digest((ROOT / row["review_path"]).read_bytes()))
                self.assertEqual(row["source_bundle_sha256"], digest((ROOT / BUNDLE).read_bytes()))
                self.assertEqual(row["source_bundle_path"], BUNDLE)
                self.assertEqual(row["status"], "ai_source_rechecked_professional_pending")
                self.assertFalse(review["professional_review"]["obtained"])
                self.assertTrue(review["professional_review"]["required"])
                self.assertEqual(row["statistics_assessed"], review["statistics_assessed"])

                body_urls = set(re.findall(r"\]\((https://[^)]+)\)", body_bytes.decode("utf-8")))
                source_urls = {self.sources[source_id]["url"] for source_id in item["source_ids"]}
                review_urls = {check["url"] for check in review["source_checks"]}
                self.assertEqual(body_urls, source_urls)
                self.assertEqual(review_urls, source_urls)
                self.assertEqual({check["source_id"] for check in review["source_checks"]},
                                 set(item["source_ids"]))
                for check in review["source_checks"]:
                    self.assertGreaterEqual(len(check["supporting_passage"]), 50)
                    self.assertIn("非逐字引文", check["supporting_passage"])
                    self.assertNotIn(check["claim"], check["supporting_passage"])
                    self.assertLessEqual(check["accessed_at"], DATE)
                    self.assertTrue(check["retrieval_method"])
                audit.validate_recheck_history(ROOT, row, item)

        for old_id in ("ch01_cga_118_hotline", "ch01_co_nfa_2025"):
            self.assertEqual(self.sources[old_id], baseline_sources[old_id])

    def test_batch_evidence_and_dynamic_coverage_counts_match_repository(self):
        baseline_coverage = git_json(BASE, "localization/tw-edition/coverage.json")
        baseline_runtime = git_json(BASE, "localization/tw-edition/runtime.json")
        baseline_register = git_json(BASE, REGISTER)
        before = self.evidence["counts_before"]
        after = self.evidence["counts_after"]
        self.assertEqual(before["core_reviewed_entries"], baseline_coverage["core_reviewed_entries"])
        self.assertEqual(before["runtime_items"], len(baseline_runtime["items"]))
        self.assertEqual(before["runtime_sources"], len(baseline_runtime["sources"]))
        self.assertEqual(before["source_registry"], baseline_coverage["registry_sources"])
        self.assertEqual(before["json_files_checked"], baseline_coverage["json_files_checked"])
        self.assertEqual(before["substantive_rechecks"], len(baseline_register["substantive_rechecks"]))
        self.assertEqual(after["core_reviewed_entries"], before["core_reviewed_entries"])
        self.assertEqual(after["runtime_items"], before["runtime_items"])
        self.assertEqual(after["runtime_sources"], before["runtime_sources"] + len(NEW_SOURCE_IDS))
        self.assertEqual(after["source_registry"], before["source_registry"] + len(NEW_SOURCE_IDS))
        self.assertGreater(after["json_files_checked"], before["json_files_checked"])
        self.assertEqual(after["substantive_rechecks"], before["substantive_rechecks"] + len(IDS))
        self.assertGreaterEqual(self.coverage["core_reviewed_entries"], after["core_reviewed_entries"])
        self.assertGreaterEqual(len(self.runtime["items"]), after["runtime_items"])
        self.assertGreaterEqual(len(self.runtime["sources"]), after["runtime_sources"])
        self.assertGreaterEqual(self.coverage["registry_sources"], after["source_registry"])
        self.assertGreaterEqual(self.coverage["json_files_checked"], after["json_files_checked"])
        self.assertGreaterEqual(len(self.rows), after["substantive_rechecks"])
        self.assertEqual(self.evidence["scope"]["new_core_ids"], [])
        self.assertEqual(set(self.evidence["new_source_ids"]), NEW_SOURCE_IDS)
        self.assertFalse(self.evidence["publication_ready"])
        self.assertFalse(self.coverage["publication_ready"])
        self.assertFalse(publication_report()["publication_ready"])


if __name__ == "__main__":
    unittest.main()

"""第1章自傷危機、中毒及局限空間高風險歷史實質再審。"""
import hashlib
import json
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from reader_copy_test_support import assert_body_version_matches_review_or_cleanup
import retroactive_audit as audit
from review_contract import ROOT, publication_report, validate_runtime

HISTORICAL_BASE = "ab6470599140fd7ed841aeea33b7f155e54efb3e"
CURRENT_BATCH_BASE = "44b11fd28836d4fe109e207088c393629a4fa96c"
IDS = ("TW-01-025", "TW-01-033", "TW-01-043", "TW-01-046")
NEW_SOURCE_IDS = {
    "ch01_crisis_mohw_1925_2026",
    "ch01_suicide_reports_2026",
    "ch01_crisis_mohw_online_2026",
    "ch01_poison_center_contact",
    "ch01_co_nfa_2025",
    "ch01_confined_facilities_29",
}


def read(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def git_json(revision, path):
    return json.loads(subprocess.check_output(
        ["git", "show", f"{revision}:{path}"], cwd=ROOT))


class Ch01SelfharmPoisonConfinedRecheckTests(unittest.TestCase):
    def test_rechecks_preserve_history_and_sync_reader_contracts(self):
        historical_runtime = git_json(HISTORICAL_BASE, "localization/tw-edition/runtime.json")
        old_sources = {source["id"]: source for source in historical_runtime["sources"]}
        runtime = validate_runtime()
        items = {item["id"]: item for item in runtime["items"]}
        sources = {source["id"]: source for source in runtime["sources"]}
        manifest = {entry["id"]: entry for entry in read("localization/manifest.json")["entries"]}
        current_register = read("localization/retroactive-review-register-20261019.json")
        current_rows = current_register["substantive_rechecks"]
        historical_register = git_json(
            CURRENT_BATCH_BASE, "localization/retroactive-review-register-20261019.json")
        historical_rows = historical_register["substantive_rechecks"]

        self.assertEqual(historical_runtime["sources"], [
            source for source in runtime["sources"] if source["id"] in old_sources])
        self.assertTrue(NEW_SOURCE_IDS <= (set(sources) - set(old_sources)))
        for item_id in IDS:
            with self.subTest(item_id=item_id):
                item = items[item_id]
                history = [row for row in current_rows if row["id"] == item_id]
                historic = next(row for row in history
                                if row["prior_revision"] == HISTORICAL_BASE
                                and row["reviewed_at"] == "2026-10-25")
                latest = history[-1]
                preserved_historic = next(row for row in historical_rows
                                          if row["id"] == item_id
                                          and row["prior_revision"] == HISTORICAL_BASE
                                          and row["reviewed_at"] == "2026-10-25")
                review = read(f"localization/reviews/{item_id}.json")
                old_item = next(entry for entry in historical_runtime["items"] if entry["id"] == item_id)
                old_review = subprocess.check_output(
                    ["git", "show", f"{HISTORICAL_BASE}:localization/reviews/{item_id}.json"], cwd=ROOT)
                markdown = (ROOT / item["target_path"]).read_bytes()
                digest = hashlib.sha256(markdown).hexdigest()

                self.assertEqual(historic, preserved_historic)
                self.assertEqual(historic["prior_review_sha256"], hashlib.sha256(old_review).hexdigest())
                self.assertEqual(historic["before_sha256"], hashlib.sha256(old_item["body"].encode()).hexdigest())
                self.assertNotEqual(historic["before_sha256"], historic["after_sha256"])
                self.assertEqual(item["body"], markdown.decode("utf-8"))
                self.assertEqual(review["target_sha256"], digest)
                self.assertEqual(review["source_checks"], latest["source_checks"])
                self.assertEqual(review["limits"], latest["limits"])
                self.assertEqual(manifest[item_id]["sources"], item["source_ids"])
                self.assertEqual(
                    {sources[source_id]["url"] for source_id in item["source_ids"]},
                    {check["url"] for check in review["source_checks"]})
                self.assertEqual(item["reviewed_at"], latest["reviewed_at"])
                self.assertEqual(item["review_due_at"], latest["review_due_at"])
                self.assertEqual(latest["status"], "ai_source_rechecked_professional_pending")
                if latest["reviewed_at"] == "2026-10-25":
                    assert_body_version_matches_review_or_cleanup(
                        self, item_id, latest["after_sha256"], digest)
                else:
                    self.assertEqual(latest["after_sha256"], digest)
                for check in review["source_checks"]:
                    self.assertGreaterEqual(len(check["supporting_passage"]), 50)
                    self.assertIn("非逐字引文", check["supporting_passage"])
                    self.assertNotIn(check["claim"], check["supporting_passage"])
                    self.assertTrue(check["retrieval_method"].strip())
                if latest["reviewed_at"] != historic["reviewed_at"]:
                    audit.validate_recheck_history(ROOT, latest, item)
                else:
                    audit.validate_recheck_history(ROOT, historic, item)

    def test_life_safety_steps_and_frequency_scope_are_explicit(self):
        items = {item["id"]: item for item in validate_runtime()["items"]}
        selfharm = items["TW-01-025"]["body"]
        self.assertLess(selfharm.index("先撥119"), selfharm.index("臺灣頻率背景"))
        self.assertIn("34,612人次", selfharm)
        self.assertIn("較2024年同期減少8%", selfharm)
        self.assertIn("不等於不同個案數", selfharm)
        self.assertIn("死亡3,951人", selfharm)
        self.assertIn("不能當個人危機機率", selfharm)

        poison = items["TW-01-033"]["body"]
        self.assertIn("先撥119", poison)
        self.assertIn("02-2871-7121", poison)
        self.assertIn("02-2875-7525分機85500", poison)
        self.assertIn("全年無休、免費諮詢", poison)
        self.assertIn("截至11月19日，全臺通報一氧化碳中毒事故12起、死亡1人、送醫48人", poison)
        self.assertIn("其中10起與屋外式熱水器裝在通風不足處有關", poison)
        self.assertLess(poison.index("先撥119"), poison.index("臺灣事件頻率"))
        self.assertIn("10／12是這12起事故中的原因分類，不是家庭中毒機率", poison)
        self.assertIn("沒有使用燃氣設備家戶數或暴露人次分母", poison)

        gatekeeper = items["TW-01-043"]["body"]
        self.assertIn("網路貼文", gatekeeper)
        self.assertIn("私下提供給可信任協助者或救援單位", gatekeeper)
        self.assertIn("不會因問話而增加念頭", gatekeeper)
        self.assertIn("這是美國研究綜整", gatekeeper)
        self.assertNotIn("cp-16-19209-1.html", gatekeeper)

        confined = items["TW-01-046"]["body"]
        self.assertIn("第29-1至29-7條", confined)
        self.assertIn("雇主使勞工", confined)
        self.assertIn("一般住戶取得許可後自行下槽", confined)
        self.assertIn("先通風、再測定、後作業", confined)
        self.assertNotIn("2027-01-01施行", confined)
        self.assertIn("113年（2024）列2件事故、2人死亡", confined)
        self.assertIn("沒有進入作業人次分母", confined)

    def test_sources_retirements_and_batch_progress_snapshot(self):
        source_batch = read(
            "localization/tw-edition/sources/ch01-selfharm-poison-confined-recheck-20261025.json")
        self.assertEqual({row[0] for row in source_batch["sources"]}, NEW_SOURCE_IDS)
        runtime = validate_runtime()
        sources = {source["id"]: source for source in runtime["sources"]}
        for source_id, title, url, supports in source_batch["sources"]:
            self.assertEqual(sources[source_id]["title"], title)
            self.assertEqual(sources[source_id]["url"], url)
            self.assertEqual(sources[source_id]["supports"], supports)

        evidence = read("localization/ch01-selfharm-poison-confined-recheck-20261025.json")
        register = read("localization/retroactive-review-register-20261019.json")
        coverage = read("localization/tw-edition/coverage.json")
        report = publication_report()
        self.assertEqual(evidence["base_main_sha"], HISTORICAL_BASE)
        self.assertEqual(evidence["scope"]["new_core_ids"], [])
        self.assertEqual(evidence["counts_before"]["core_completed"], 278)
        self.assertEqual(evidence["counts_after"]["core_completed"], 278)
        self.assertEqual(evidence["counts_before"]["substantive_rechecks"], 128)
        self.assertEqual(evidence["counts_after"]["substantive_rechecks"], 132)
        self.assertEqual(evidence["counts_after"]["runtime_sources"], 686)
        self.assertEqual(evidence["counts_after"]["source_registry"], 767)
        # Earlier batch counts remain historical snapshots; later mainline reviews may append rows.
        self.assertGreaterEqual(len(register["substantive_rechecks"]),
                                evidence["counts_after"]["substantive_rechecks"])
        self.assertGreaterEqual(coverage["registry_sources"], evidence["counts_after"]["source_registry"])
        self.assertEqual(coverage["core_reviewed_entries"], report["publication_completed_entries"])
        self.assertFalse(coverage["publication_ready"])
        self.assertFalse(report["publication_ready"])

        historic_rows = git_json(CURRENT_BATCH_BASE,
                                 "localization/retroactive-review-register-20261019.json")["substantive_rechecks"]
        historical_043 = next(row for row in historic_rows if row["id"] == "TW-01-043")
        historical_046 = next(row for row in historic_rows if row["id"] == "TW-01-046")
        self.assertEqual(historical_043["retired_sources"][0]["id"], "ch01_gambling_mental")
        self.assertEqual(historical_046["retired_sources"][0]["id"], "ch01_grinder_facilities")
        old_runtime = git_json(CURRENT_BATCH_BASE, "localization/tw-edition/runtime.json")
        old_sources = {source["id"]: source for source in old_runtime["sources"]}
        for item_id, source_id in (("TW-01-043", "ch01_gambling_mental"),
                                   ("TW-01-046", "ch01_grinder_facilities")):
            retired = next(row for row in historic_rows if row["id"] == item_id)["retired_sources"][0]
            digest = hashlib.sha256(json.dumps(old_sources[source_id], ensure_ascii=False,
                                               sort_keys=True).encode("utf-8")).hexdigest()
            self.assertEqual(retired["prior_source_sha256"], digest)
            self.assertEqual(sources[source_id], old_sources[source_id])


if __name__ == "__main__":
    unittest.main()

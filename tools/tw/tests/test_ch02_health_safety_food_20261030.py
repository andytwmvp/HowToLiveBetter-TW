"""第二章健康與食品安全正文、來源及第13章一氧化碳再審回歸。"""
import hashlib
import json
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import retroactive_audit
from body_renderer import body_blocks
from review_contract import ROOT, publication_report, validate_entry, validate_runtime

BASE = "a853321583f76ef502ec88738af8d221b8d696d4"
NEW_IDS = {"TW-02-020", "TW-02-029", "TW-02-046", "TW-02-047"}


def load(relative):
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


class ChapterTwoHealthSafetyFoodTests(unittest.TestCase):
    def test_new_articles_match_manifest_reviews_and_sources(self):
        manifest = {item["id"]: item for item in load("localization/manifest.json")["entries"]}
        runtime = validate_runtime()
        items = {item["id"]: item for item in runtime["items"]}
        sources = {source["id"]: source for source in runtime["sources"]}
        self.assertTrue(NEW_IDS.issubset(items))

        batch = load("localization/tw-edition/sources/ch02-health-safety-food-20261030.json")
        batch_sources = {row[0]: row for row in batch["sources"]}
        for key in NEW_IDS:
            with self.subTest(id=key):
                entry = manifest[key]
                self.assertEqual(entry["status"], "verified")
                self.assertTrue(validate_entry(entry))
                raw = (ROOT / entry["target_path"]).read_bytes()
                review = load(f"localization/reviews/{key}.json")
                item = items[key]
                self.assertEqual(hashlib.sha256(raw).hexdigest(), review["target_sha256"])
                self.assertEqual(raw.decode("utf-8"), item["body"])
                self.assertEqual(entry["sources"], item["source_ids"])
                self.assertEqual(
                    {row["url"] for row in review["source_checks"]},
                    {sources[source_id]["url"] for source_id in item["source_ids"]},
                )
                self.assertEqual(sum(block["tag"] == "h3" for block in body_blocks(item)), 5)
                self.assertTrue(any("未取得獨立" in limit for limit in review["limits"]))
                for source_id in item["source_ids"]:
                    self.assertIn(source_id, batch_sources)
                    self.assertEqual(batch_sources[source_id][2], sources[source_id]["url"])

    def test_taiwan_risk_and_frequency_claims_keep_correct_units_and_limits(self):
        items = {item["id"]: item for item in validate_runtime()["items"]}
        body = {key: items[key]["body"] for key in NEW_IDS}

        self.assertIn("抽搐、幻覺、明顯混亂", body["TW-02-020"])
        self.assertIn("立即撥119", body["TW-02-020"])
        self.assertIn("不要獨自硬戒", body["TW-02-020"])
        self.assertIn("症狀出現時間也不能當成在家等待的安全時限", body["TW-02-020"])
        self.assertIn("消防署114年（2025）統計", body["TW-02-029"])
        self.assertIn("22件", body["TW-02-029"])
        self.assertIn("5人死亡、59人送醫", body["TW-02-029"])
        self.assertIn("不能換算成個人發生率", body["TW-02-029"])
        self.assertIn("抽驗38件", body["TW-02-046"])
        self.assertIn("單一縣市", body["TW-02-046"])
        self.assertNotIn("餵寵物", body["TW-02-046"])
        self.assertIn("通報1,212件、患者5,650人、死亡0人", body["TW-02-047"])
        self.assertIn("不是確診感染發生率或個人風險", body["TW-02-047"])
        self.assertIn("最後更新於2019年", body["TW-02-047"])

    def test_new_reader_copy_uses_taiwanese_plain_language_without_editorial_process_notes(self):
        items = {item["id"]: item for item in validate_runtime()["items"]}
        bodies = "\n".join(items[key]["body"] for key in NEW_IDS)
        reader_copy = bodies + "\n" + (ROOT / "locales/zh-TW/book/ch02/README.md").read_text(encoding="utf-8")
        for phrase in ("目前查閱到的官方資料", "本文只用它", "本輪", "本批", "AI輔助", "本章目前收錄"):
            with self.subTest(phrase=phrase):
                self.assertNotIn(phrase, reader_copy)

    def test_co_recheck_history_preserves_real_previous_sources(self):
        prior = json.loads(
            subprocess.check_output(
                ["git", "show", f"{BASE}:localization/tw-edition/runtime.json"],
                cwd=ROOT,
                text=True,
            )
        )
        current = validate_runtime()
        prior_items = {item["id"]: item for item in prior["items"]}
        current_items = {item["id"]: item for item in current["items"]}
        prior_item_ids = [item["id"] for item in prior["items"]]
        current_item_ids = [item["id"] for item in current["items"]]
        self.assertEqual(current_item_ids[:len(prior_item_ids)], prior_item_ids)
        self.assertEqual(set(current_item_ids[len(prior_item_ids):]), NEW_IDS)
        for item in prior["items"]:
            retroactive_audit.assert_preserved_or_rechecked(self, item, current_items[item["id"]])

        prior_source_ids = [source["id"] for source in prior["sources"]]
        current_source_ids = [source["id"] for source in current["sources"]]
        self.assertEqual(current_source_ids[:len(prior_source_ids)], prior_source_ids)
        register = load("localization/retroactive-review-register-20261019.json")
        edge = next(
            record for record in register["substantive_rechecks"]
            if record["id"] == "TW-13-019" and record["reviewed_at"] == "2026-10-30"
        )
        base_register = json.loads(
            subprocess.check_output(
                ["git", "show", f"{BASE}:localization/retroactive-review-register-20261019.json"],
                cwd=ROOT,
                text=True,
            )
        )
        prior_rechecks = base_register["substantive_rechecks"]
        current_rechecks = register["substantive_rechecks"]
        self.assertEqual(current_rechecks[:len(prior_rechecks)], prior_rechecks)
        self.assertIn(edge, current_rechecks[len(prior_rechecks):])
        self.assertEqual(edge["previous_source_ids"], prior_items["TW-13-019"]["source_ids"])
        self.assertEqual(edge["source_ids"], current_items["TW-13-019"]["source_ids"])
        retroactive_audit.validate_recheck_history(ROOT, edge, current_items["TW-13-019"])
        for source in prior["sources"]:
            self.assertEqual({item["id"]: item for item in current["sources"]}[source["id"]], source)

    def test_annual_counts_are_not_presented_as_personal_rates_and_coverage_is_current(self):
        co = (ROOT / "locales/zh-TW/book/ch13/TW-13-019.md").read_text(encoding="utf-8")
        self.assertIn("一氧化碳中毒事故22件、5人死亡、59人送醫", co)
        self.assertIn("不能換算個人發生率或事故致死率", co)
        self.assertNotIn("加入燃氣設備安裝", co)

        report = publication_report()
        coverage = load("localization/tw-edition/coverage.json")
        self.assertEqual(coverage["publication_completed_entries"], report["publication_completed_entries"])
        self.assertFalse(report["publication_ready"])


if __name__ == "__main__":
    unittest.main()

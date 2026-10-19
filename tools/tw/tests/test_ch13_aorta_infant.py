"""第13章第六批：主動脈與嬰幼兒急救來源、正文雜湊及已合併內容保全。"""
import hashlib
import json
import subprocess
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from retroactive_audit import assert_preserved_or_rechecked
from review_contract import ROOT, validate_entry, validate_runtime, publication_report
from body_renderer import body_blocks

BASE = "fe54095e7de188479ecc4bf6507b5bb4639b0aec"
IDS = {"TW-13-008", "TW-13-043", "TW-13-044", "TW-13-045"}

def load(p):
    return json.loads((ROOT / p).read_text(encoding="utf-8"))

class Chapter13AortaInfantTests(unittest.TestCase):
    def test_four_taiwan_guides_review_sha_and_registry(self):
        entries = {e["id"]: e for e in load("localization/manifest.json")["entries"]}
        runtime = validate_runtime()
        items = {e["id"]: e for e in runtime["items"]}
        sources = {s["id"]: s for s in runtime["sources"]}
        for key in IDS:
            with self.subTest(key=key):
                entry = entries[key]
                self.assertEqual(entry["status"], "verified")
                self.assertTrue(validate_entry(entry))
                raw = (ROOT / entry["target_path"]).read_bytes()
                review = load("localization/reviews/" + key + ".json")
                self.assertGreater(len(raw), 1800)
                self.assertEqual(hashlib.sha256(raw).hexdigest(), review["target_sha256"])
                self.assertEqual(raw.decode("utf-8"), items[key]["body"])
                self.assertEqual(sum(x["tag"] == "h3" for x in body_blocks(items[key])), 5)
                self.assertEqual({x["url"] for x in review["source_checks"]},
                                 {sources[s]["url"] for s in items[key]["source_ids"]})
    def test_official_taiwan_wording_survives_opencc_without_general_exemption(self):
        # 臺灣托嬰機構名稱與「干預」不可為通過字形檢查而錯改。
        from ci_language_policy import canonical
        from traditionalize import cc
        for phrase in ("托嬰中心", "托嬰人員", "干預"):
            with self.subTest(phrase=phrase):
                self.assertEqual(canonical(cc().convert(phrase)), canonical(phrase))
        # 只修正上述詞組，不對其他真正的簡體字放行。
        self.assertNotEqual(canonical(cc().convert("医疗服务")), canonical("医疗服务"))

    def test_infant_specific_safety_and_taiwan_119(self):
        d = {e["id"]: e["body"].split("## 官方來源及改寫說明")[0] for e in validate_runtime()["items"]}
        for key in IDS:
            self.assertIn("119", d[key])
            self.assertNotIn("打120", d[key])
            self.assertNotIn("撥120", d[key])
        self.assertIn("主動脈剝離", d["TW-13-008"])
        self.assertIn("五次胸部衝擊", d["TW-13-043"])
        self.assertIn("絕不可", d["TW-13-043"])
        self.assertIn("30次", d["TW-13-044"])
        self.assertIn("2次", d["TW-13-044"])
        self.assertIn("不催吐", d["TW-13-045"])
        self.assertIn("磁鐵", d["TW-13-045"])
    def test_previous_220_items_and_sources_unchanged(self):
        old = json.loads(subprocess.check_output(
            ["git", "show", BASE + ":localization/tw-edition/runtime.json"], cwd=ROOT, text=True))
        rt = validate_runtime()
        ii = {item["id"]: item for item in rt["items"]}
        ss = {source["id"]: source for source in rt["sources"]}
        self.assertEqual(len(old["items"]), 220)
        for item in old["items"]:
            assert_preserved_or_rechecked(self,item,ii[item["id"]])
        for source in old["sources"]:
            self.assertEqual(source, ss[source["id"]])
    def test_counts_remain_dynamic_and_full_book_is_not_ready(self):
        report = publication_report()
        c = load("localization/tw-edition/coverage.json")
        rt = validate_runtime()
        self.assertEqual(report["publication_total_entries"], 765)
        self.assertFalse(report["publication_ready"])
        self.assertEqual(report["publication_completed_entries"], c["publication_completed_entries"])
        self.assertEqual(len(rt["items"]), report["publication_completed_entries"] + 10)
        self.assertEqual(c["unique_draft_entries"] + c["entries_without_any_draft"], 765)
        self.assertGreaterEqual(c["registry_sources"], len(rt["sources"]))
        self.assertEqual(len(load("localization/tw-edition/sources/ch13-aorta-infant-20261018.json")["sources"]), 9)
        self.assertEqual(load("localization/ch13-aorta-infant-20261018.json")["chapter_cumulative"], 32)

if __name__ == "__main__":
    unittest.main()

"""第13章第五批：神經、眼科急症的逐條來源、內容SHA及歷史保全測試。"""
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

BASE = "7414873629d9c91a418e1b162073c518c5d49955"
IDS = {"TW-13-004", "TW-13-005", "TW-13-006", "TW-13-009"}

def load(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))

class Chapter13NeuroEyeTests(unittest.TestCase):
    def test_reviewed_complete_taiwan_articles(self):
        manifest = {e["id"]: e for e in load("localization/manifest.json")["entries"]}
        runtime = validate_runtime()
        items = {e["id"]: e for e in runtime["items"]}
        sources = {s["id"]: s for s in runtime["sources"]}
        for key in IDS:
            with self.subTest(key=key):
                entry = manifest[key]
                self.assertEqual(entry["status"], "verified")
                self.assertTrue(validate_entry(entry))
                raw = (ROOT / entry["target_path"]).read_bytes()
                review = load(f"localization/reviews/{key}.json")
                self.assertGreater(len(raw), 1800)
                self.assertEqual(hashlib.sha256(raw).hexdigest(), review["target_sha256"])
                self.assertEqual(raw.decode("utf-8"), items[key]["body"])
                self.assertEqual(sum(x["tag"] == "h3" for x in body_blocks(items[key])), 5)
                self.assertEqual({s["url"] for s in review["source_checks"]},
                                 {sources[s]["url"] for s in items[key]["source_ids"]})

    def test_taiwan_emergency_triage_and_limits(self):
        body = {e["id"]: e["body"].split("## 官方來源及改寫說明")[0] for e in validate_runtime()["items"]}
        for key in IDS:
            self.assertIn("119", body[key])
            self.assertNotIn("撥120", body[key])
            self.assertNotIn("打120", body[key])
        self.assertIn("複視", body["TW-13-004"])
        self.assertIn("不要", body["TW-13-004"])
        self.assertIn("恢復", body["TW-13-005"])
        self.assertIn("眼科急診", body["TW-13-006"])
        self.assertIn("不能要求每個人必做指定", body["TW-13-009"])

    def test_prior_reading_rows_and_sources_preserved(self):
        old = json.loads(subprocess.check_output(
            ["git", "show", BASE + ":localization/tw-edition/runtime.json"],
            cwd=ROOT, text=True))
        now = validate_runtime()
        items = {e["id"]: e for e in now["items"]}
        sources = {s["id"]: s for s in now["sources"]}
        self.assertEqual(len(old["items"]), 216)
        for entry in old["items"]:
            assert_preserved_or_rechecked(self,entry,items[entry["id"]])
        for source in old["sources"]:
            self.assertEqual(source, sources[source["id"]])

    def test_incremental_counts_and_source_registry(self):
        report = publication_report()
        coverage = load("localization/tw-edition/coverage.json")
        runtime = validate_runtime()
        self.assertFalse(report["publication_ready"])
        self.assertEqual(coverage["publication_completed_entries"], report["publication_completed_entries"])
        self.assertEqual(report["publication_total_entries"], 765)
        self.assertEqual(len(runtime["items"]), report["publication_completed_entries"] + 10)
        self.assertEqual(coverage["unique_draft_entries"] + coverage["entries_without_any_draft"], 765)
        self.assertGreaterEqual(coverage["registry_sources"], len(runtime["sources"]))
        self.assertEqual(len(load("localization/tw-edition/sources/ch13-neuro-eye-20261018.json")["sources"]), 6)
        self.assertEqual(load("localization/ch13-neuro-eye-20261018.json")["chapter_cumulative"], 28)

if __name__ == "__main__":
    unittest.main()

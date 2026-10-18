"""第13章第十批：臺灣動物遭遇、戶外暴力、鬥毆及救人受傷之來源與資料一致性。"""
import hashlib, json, subprocess, unittest, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from review_contract import ROOT,validate_entry,validate_runtime,publication_report
from body_renderer import body_blocks
BASE="51c8b3c0148b31f833d5a79b7af16e5d94516fb7"
IDS={"TW-13-031","TW-13-036","TW-13-037","TW-13-039"}
def load(p): return json.loads((ROOT/p).read_text(encoding="utf-8"))
class Chapter13AnimalsPublicSafetyTests(unittest.TestCase):
 def test_source_review_sha_and_renderer(self):
  entries={x["id"]:x for x in load("localization/manifest.json")["entries"]}
  runtime=validate_runtime()
  items={x["id"]:x for x in runtime["items"]}
  sources={x["id"]:x for x in runtime["sources"]}
  for key in IDS:
   with self.subTest(key=key):
    e=entries[key];self.assertEqual(e["status"],"verified");self.assertTrue(validate_entry(e))
    raw=(ROOT/e["target_path"]).read_bytes()
    review=load("localization/reviews/"+key+".json")
    self.assertGreater(len(raw),1800)
    self.assertEqual(hashlib.sha256(raw).hexdigest(),review["target_sha256"])
    self.assertEqual(raw.decode("utf-8"),items[key]["body"])
    self.assertEqual(sum(b["tag"]=="h3" for b in body_blocks(items[key])),5)
    self.assertEqual({x["url"] for x in review["source_checks"]},{sources[s]["url"] for s in items[key]["source_ids"]})
 def test_risk_and_frequency_boundaries(self):
  b={x["id"]:x["body"].split("## 官方來源及改寫說明")[0] for x in validate_runtime()["items"]}
  self.assertIn("黑熊",b["TW-13-031"]);self.assertIn("野豬",b["TW-13-031"]);self.assertIn("犬群",b["TW-13-031"])
  self.assertIn("119",b["TW-13-031"]);self.assertIn("1959",b["TW-13-031"])
  self.assertIn("130件",b["TW-13-036"]);self.assertIn("118件",b["TW-13-036"])
  self.assertIn("不是偏僻山路",b["TW-13-036"])
  self.assertIn("110",b["TW-13-037"]);self.assertIn("119",b["TW-13-037"])
  self.assertIn("第14條之2",b["TW-13-039"]);self.assertIn("第150條",b["TW-13-039"])
  self.assertIn("0800-005-850",b["TW-13-039"])
  for key in IDS:
   self.assertNotIn("撥120",b[key]);self.assertNotIn("打120",b[key])
   self.assertTrue("發生率" in b[key] or "發生頻率" in b[key] or "分母" in b[key])
 def test_old_runtime_and_sources_preserved(self):
  old=json.loads(subprocess.check_output(["git","show",BASE+":localization/tw-edition/runtime.json"],cwd=ROOT,text=True))
  rt=validate_runtime();ii={x["id"]:x for x in rt["items"]};ss={x["id"]:x for x in rt["sources"]}
  self.assertEqual(len(old["items"]),236)
  for x in old["items"]:self.assertEqual(x,ii[x["id"]])
  for x in old["sources"]:self.assertEqual(x,ss[x["id"]])
 def test_dynamic_progress(self):
  c=load("localization/tw-edition/coverage.json");p=publication_report();rt=validate_runtime()
  self.assertFalse(p["publication_ready"]);self.assertEqual(p["publication_total_entries"],765)
  self.assertEqual(p["publication_completed_entries"],230)
  self.assertEqual(c["core_reviewed_entries"],p["publication_completed_entries"])
  self.assertEqual(len(rt["items"]),p["publication_completed_entries"]+10)
  self.assertEqual(c["unique_draft_entries"]+c["entries_without_any_draft"],765)
  self.assertEqual(len(load("localization/tw-edition/sources/ch13-animals-public-safety-20261019.json")["sources"]),13)
  self.assertEqual(load("localization/ch13-animals-public-safety-20261019.json")["chapter_cumulative"],48)
if __name__=="__main__":unittest.main()

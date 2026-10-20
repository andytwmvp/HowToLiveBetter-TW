"""臺灣第26章平台合規：正文、來源與舊版資料保全回歸。"""
import hashlib, json, subprocess, sys, unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from retroactive_audit import assert_preserved_or_rechecked
from review_contract import ROOT, validate_runtime, validate_entry, publication_report
from body_renderer import body_blocks
BASE="212f9e3019a3f8682113a6dcb880817cc44074a3"
IDS={f"TW-26-{i:03}" for i in range(1,14)}
def obj(path):return json.loads((ROOT/path).read_text(encoding="utf-8"))
class PlatformComplianceTests(unittest.TestCase):
 def test_13_reviewed_entries(self):
  records={e["id"]:e for e in obj("localization/manifest.json")["entries"]}
  runtime={e["id"]:e for e in validate_runtime()["items"]}
  self.assertEqual(IDS & set(runtime),IDS)
  for id in IDS:
   with self.subTest(id=id):
    m=records[id];self.assertEqual(m["status"],"verified");self.assertTrue(validate_entry(m))
    raw=(ROOT/m["target_path"]).read_bytes();rev=obj("localization/reviews/"+id+".json")
    self.assertEqual(raw.decode("utf-8"),runtime[id]["body"])
    self.assertEqual(hashlib.sha256(raw).hexdigest(),rev["target_sha256"])
    self.assertGreater(len(raw),850)
    self.assertEqual(sum(block["tag"]=="h3" for block in body_blocks(runtime[id])),5)
 def test_prior_reading_and_source_objects_preserved(self):
  raw=subprocess.check_output(["git","show",BASE+":localization/tw-edition/runtime.json"],cwd=ROOT,text=True)
  old=json.loads(raw);now=validate_runtime()
  previous_items={e["id"]:e for e in now["items"]}
  previous_sources={s["id"]:s for s in now["sources"]}
  self.assertEqual(len(old["items"]),136)
  for item in old["items"]:assert_preserved_or_rechecked(self,item,previous_items[item["id"]])
  for source in old["sources"]:self.assertEqual(source,previous_sources[source["id"]])
 def test_taiwan_law_distinctions(self):
  items={e["id"]:e["body"] for e in validate_runtime()["items"]}
  for phrase in ("第三方支付","電子支付","登錄"):self.assertIn(phrase,items["TW-26-001"])
  for phrase in ("10萬元","5萬元","稅籍"):self.assertIn(phrase,items["TW-26-002"])
  for phrase in ("24小時","180日"):self.assertIn(phrase,items["TW-26-006"])
  for phrase in ("10個工作日","14個工作日"):self.assertIn(phrase,items["TW-26-009"])
  for phrase in ("尚未施行","第12條"):self.assertIn(phrase,items["TW-26-012"])
  self.assertIn("事先同意",items["TW-26-013"])
 def test_sources_and_approval_are_not_faked(self):
  rows=obj("localization/tw-edition/sources/21-platform-compliance.json")["sources"]
  self.assertEqual(len(rows),9)
  self.assertTrue(all(s[2].startswith("https://") for s in rows))
  for id in IDS:
   data=obj("localization/reviews/"+id+".json")
   self.assertIn("AI",data["reviewer"])
   self.assertTrue(all(s["url"] and s["claim"] and s["supporting_passage"] for s in data["source_checks"]))
  report=publication_report()
  self.assertGreaterEqual(report["publication_completed_entries"],140)
  self.assertFalse(report["publication_ready"])
 def test_one_time_writer_retired(self):
  self.assertFalse((ROOT/"tools/tw/apply_ch26.py").exists())
  self.assertFalse((ROOT/".github/workflows/ch26-integrate.yml").exists())
if __name__=="__main__":unittest.main()

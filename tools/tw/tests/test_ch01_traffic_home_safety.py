"""第1章首批臺灣道路／居家安全頻率口徑、審閱及共用閱讀契約。"""
import hashlib, json, subprocess, unittest, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from retroactive_audit import assert_preserved_or_rechecked
from review_contract import ROOT, validate_entry, validate_runtime, publication_report
from body_renderer import body_blocks
BASE="0aa02aa0bf6f8ae32177c5d4fc88f5db24c10b44"
IDS={"TW-01-001","TW-01-002","TW-01-003","TW-01-004"}
def load(p): return json.loads((ROOT/p).read_text(encoding="utf-8"))
class Chapter01TrafficHomeTests(unittest.TestCase):
 def test_4_full_bodies_review_sha_sources_and_renderer(self):
  entries={x["id"]:x for x in load("localization/manifest.json")["entries"]}
  rt=validate_runtime();items={x["id"]:x for x in rt["items"]};sources={x["id"]:x for x in rt["sources"]}
  for key in IDS:
   with self.subTest(key=key):
    entry=entries[key];self.assertEqual(entry["status"],"verified");self.assertTrue(validate_entry(entry))
    raw=(ROOT/entry["target_path"]).read_bytes()
    review=load("localization/reviews/"+key+".json")
    self.assertGreater(len(raw),1800)
    self.assertEqual(hashlib.sha256(raw).hexdigest(),review["target_sha256"])
    self.assertEqual(raw.decode("utf-8"),items[key]["body"])
    self.assertEqual(sum(x["tag"]=="h3" for x in body_blocks(items[key])),5)
    self.assertEqual({x["url"] for x in review["source_checks"]},{sources[s]["url"] for s in items[key]["source_ids"]})
 def test_taiwan_frequency_and_risk_gates(self):
  b={x["id"]:x["body"] for x in validate_runtime()["items"]}
  self.assertIn("2,858人",b["TW-01-001"]);self.assertIn("不是未繫安全帶",b["TW-01-001"])
  self.assertIn("10件",b["TW-01-002"]);self.assertIn("全國",b["TW-01-002"])
  self.assertIn("3,171次",b["TW-01-003"]);self.assertIn("不是全臺房屋戶數",b["TW-01-003"])
  self.assertIn("24件",b["TW-01-004"]);self.assertIn("22件",b["TW-01-004"]);self.assertNotIn("118件",b["TW-01-004"]);self.assertIn("沒有燃氣熱水器使用戶數",b["TW-01-004"])
  for key in IDS:
   self.assertIn("119",b[key]);self.assertTrue("頻率" in b[key] or "分母" in b[key])
   self.assertNotIn("撥120",b[key]);self.assertNotIn("打120",b[key])
 def test_prior_reading_data_preserved(self):
  old=json.loads(subprocess.check_output(["git","show",BASE+":localization/tw-edition/runtime.json"],cwd=ROOT,text=True))
  rt=validate_runtime();items={x["id"]:x for x in rt["items"]};sources={x["id"]:x for x in rt["sources"]}
  self.assertEqual(len(old["items"]),240)
  for x in old["items"]:assert_preserved_or_rechecked(self,x,items[x["id"]])
  for x in old["sources"]:self.assertEqual(x,sources[x["id"]])
 def test_dynamic_progress(self):
  c=load("localization/tw-edition/coverage.json");p=publication_report();rt=validate_runtime()
  self.assertFalse(p["publication_ready"]);self.assertEqual(p["publication_total_entries"],765)
  self.assertGreaterEqual(p["publication_completed_entries"],234)
  self.assertEqual(c["core_reviewed_entries"],p["publication_completed_entries"])
  self.assertEqual(len(rt["items"]),p["publication_completed_entries"]+sum(i['id'].startswith('TW-NAV-') for i in rt['items']))
  self.assertEqual(c["unique_draft_entries"]+c["entries_without_any_draft"],765)
  self.assertEqual(len(load("localization/tw-edition/sources/ch01-traffic-home-20261019.json")["sources"]),8)
if __name__=="__main__": unittest.main()

"""第13章第八批：臺灣山域、雷雨、HIV PEP、性侵害及統計口徑回歸。"""
import hashlib,json,subprocess,unittest,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from retroactive_audit import assert_preserved_or_rechecked
from review_contract import ROOT,validate_entry,validate_runtime,publication_report
from body_renderer import body_blocks
BASE="5224a052adb08c66356257cdc2bfa94c410c567c"
IDS={"TW-13-027","TW-13-032","TW-13-038","TW-13-042"}
def load(p):return json.loads((ROOT/p).read_text(encoding="utf-8"))
class Chapter13TaiwanRealRiskTests(unittest.TestCase):
 def test_complete_taiwan_bodies_review_sha_and_reading(self):
  entries={x["id"]:x for x in load("localization/manifest.json")["entries"]}
  rt=validate_runtime();items={x["id"]:x for x in rt["items"]};sources={x["id"]:x for x in rt["sources"]}
  for key in IDS:
   with self.subTest(key=key):
    e=entries[key];self.assertEqual(e["status"],"verified");self.assertTrue(validate_entry(e))
    raw=(ROOT/e["target_path"]).read_bytes();review=load("localization/reviews/"+key+".json")
    self.assertGreater(len(raw),2000)
    self.assertEqual(hashlib.sha256(raw).hexdigest(),review["target_sha256"])
    self.assertEqual(raw.decode("utf-8"),items[key]["body"])
    self.assertEqual(sum(b["tag"]=="h3" for b in body_blocks(items[key])),5)
    self.assertEqual({x["url"] for x in review["source_checks"]},{sources[s]["url"] for s in items[key]["source_ids"]})
 def test_emergency_taiwan_specificity_and_frequency_denominators(self):
  b={x["id"]:x["body"].split("## 官方來源及改寫說明")[0] for x in validate_runtime()["items"]}
  self.assertIn("502件",b["TW-13-027"]);self.assertIn("695人",b["TW-13-027"]);self.assertIn("1,416面",b["TW-13-027"])
  self.assertIn("VoLTE",b["TW-13-027"]);self.assertIn("119",b["TW-13-027"])
  self.assertIn("30分鐘",b["TW-13-032"]);self.assertIn("涼亭",b["TW-13-032"])
  self.assertIn("72小時",b["TW-13-038"]);self.assertIn("28天",b["TW-13-038"])
  self.assertIn("3,665人",b["TW-13-042"]);self.assertIn("3,123人",b["TW-13-042"])
  self.assertIn("113",b["TW-13-042"]);self.assertIn("110",b["TW-13-042"])
  for key in IDS:
   self.assertNotIn("撥120",b[key]);self.assertNotIn("打120",b[key])
   self.assertTrue("發生率" in b[key] or "頻率" in b[key])
 def test_old_228_items_and_sources_are_unchanged(self):
  old=json.loads(subprocess.check_output(["git","show",BASE+":localization/tw-edition/runtime.json"],cwd=ROOT,text=True))
  rt=validate_runtime();ii={x["id"]:x for x in rt["items"]};ss={x["id"]:x for x in rt["sources"]}
  self.assertEqual(len(old["items"]),228)
  for x in old["items"]:assert_preserved_or_rechecked(self,x,ii[x["id"]])
  for x in old["sources"]:self.assertEqual(x,ss[x["id"]])
 def test_coverage_dynamic_and_sources_logged(self):
  c=load("localization/tw-edition/coverage.json");p=publication_report();rt=validate_runtime()
  self.assertFalse(p["publication_ready"]);self.assertEqual(p["publication_total_entries"],765)
  self.assertEqual(p["publication_completed_entries"],c["core_reviewed_entries"])
  self.assertEqual(len(rt["items"]),p["publication_completed_entries"]+sum(i['id'].startswith('TW-NAV-') for i in rt['items']))
  self.assertEqual(c["unique_draft_entries"]+c["entries_without_any_draft"],765)
  self.assertGreaterEqual(c["registry_sources"],len(rt["sources"]))
  self.assertEqual(len(load("localization/tw-edition/sources/ch13-tw-realrisk-20261018.json")["sources"]),11)
  self.assertEqual(load("localization/ch13-tw-realrisk-20261018.json")["chapter_cumulative"],40)
if __name__=="__main__":unittest.main()

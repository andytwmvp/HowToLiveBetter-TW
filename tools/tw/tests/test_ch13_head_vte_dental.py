"""第13章第七批臺灣急救正文、來源、SHA及歷史保全回歸。"""
import json,hashlib,subprocess,unittest,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from retroactive_audit import assert_preserved_or_rechecked
from review_contract import ROOT,validate_entry,validate_runtime,publication_report
from body_renderer import body_blocks
BASE="a1b2e1953ab740c24d560d9cefb81586e9c04cf1"
IDS={"TW-13-010","TW-13-011","TW-13-047","TW-13-048"}
def load(p):return json.loads((ROOT/p).read_text(encoding="utf-8"))
class Chapter13HeadVteDentalTests(unittest.TestCase):
 def test_review_sha_and_public_reading(self):
  entries={e["id"]:e for e in load("localization/manifest.json")["entries"]}
  rt=validate_runtime();items={i["id"]:i for i in rt["items"]};sources={s["id"]:s for s in rt["sources"]}
  for key in IDS:
   with self.subTest(key=key):
    e=entries[key];self.assertEqual(e["status"],"verified");self.assertTrue(validate_entry(e))
    raw=(ROOT/e["target_path"]).read_bytes();review=load("localization/reviews/"+key+".json")
    self.assertGreater(len(raw),1700);self.assertEqual(hashlib.sha256(raw).hexdigest(),review["target_sha256"])
    self.assertEqual(raw.decode("utf-8"),items[key]["body"])
    self.assertEqual(sum(x["tag"]=="h3" for x in body_blocks(items[key])),5)
    self.assertEqual({x["url"] for x in review["source_checks"]},{sources[x]["url"] for x in items[key]["source_ids"]})
 def test_taiwan_emergencies(self):
  data={e["id"]:e["body"].split("## 官方來源及改寫說明")[0] for e in validate_runtime()["items"]}
  for k in IDS:self.assertIn("119",data[k]);self.assertNotIn("撥120",data[k])
  self.assertIn("慢性硬腦膜下血腫",data["TW-13-010"])
  self.assertIn("Homan",data["TW-13-011"])
  self.assertIn("不要按摩",data["TW-13-011"])
  self.assertIn("斷指直接碰冰水",data["TW-13-047"])
  self.assertIn("乳牙不可",data["TW-13-048"])
 def test_earlier_224_items_and_sources_unchanged(self):
  old=json.loads(subprocess.check_output(["git","show",BASE+":localization/tw-edition/runtime.json"],cwd=ROOT,text=True))
  current=validate_runtime();ii={x["id"]:x for x in current["items"]};ss={x["id"]:x for x in current["sources"]}
  self.assertEqual(len(old["items"]),224)
  for x in old["items"]:assert_preserved_or_rechecked(self,x,ii[x["id"]])
  for x in old["sources"]:self.assertEqual(x,ss[x["id"]])
 def test_dynamic_coverage_not_publication(self):
  c=load("localization/tw-edition/coverage.json");rt=validate_runtime();report=publication_report()
  self.assertFalse(report["publication_ready"]);self.assertEqual(report["publication_total_entries"],765)
  self.assertEqual(report["publication_completed_entries"],c["core_reviewed_entries"])
  self.assertEqual(len(rt["items"]),report["publication_completed_entries"]+10)
  self.assertEqual(c["unique_draft_entries"]+c["entries_without_any_draft"],765)
  self.assertGreaterEqual(c["registry_sources"],len(rt["sources"]))
  self.assertEqual(len(load("localization/tw-edition/sources/ch13-head-vte-dental-20261018.json")["sources"]),8)
  self.assertEqual(load("localization/ch13-head-vte-dental-20261018.json")["chapter_cumulative"],36)
if __name__=="__main__":unittest.main()

"""第13章第九批：臺灣高山症、蜱蟲、野外飲水、酒精中毒來源與風險回歸。"""
import hashlib,json,subprocess,unittest,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from retroactive_audit import assert_preserved_or_rechecked
from review_contract import ROOT,validate_entry,validate_runtime,publication_report
from body_renderer import body_blocks
BASE="b1caf71c8cd99fff72ae915b4d983d9726115257"
IDS={"TW-13-033","TW-13-034","TW-13-035","TW-13-046"}
def load(p):return json.loads((ROOT/p).read_text(encoding="utf-8"))
class Chapter13AltitudeTickWaterAlcoholTests(unittest.TestCase):
 def test_review_sha_source_and_runtime(self):
  entries={x["id"]:x for x in load("localization/manifest.json")["entries"]};rt=validate_runtime();items={x["id"]:x for x in rt["items"]};sources={x["id"]:x for x in rt["sources"]}
  for k in IDS:
   with self.subTest(key=k):
    e=entries[k];self.assertEqual(e["status"],"verified");self.assertTrue(validate_entry(e))
    raw=(ROOT/e["target_path"]).read_bytes();review=load("localization/reviews/"+k+".json")
    self.assertGreater(len(raw),1800)
    self.assertEqual(hashlib.sha256(raw).hexdigest(),review["target_sha256"])
    self.assertEqual(raw.decode("utf-8"),items[k]["body"])
    self.assertEqual(sum(x["tag"]=="h3" for x in body_blocks(items[k])),5)
    self.assertEqual({x["url"] for x in review["source_checks"]},{sources[s]["url"] for s in items[k]["source_ids"]})
 def test_taiwan_season_frequencies_and_emergency_gates(self):
  b={x["id"]:x["body"].split("## 官方來源及改寫說明")[0] for x in validate_runtime()["items"]}
  self.assertIn("2017",b["TW-13-033"]);self.assertIn("下撤",b["TW-13-033"])
  self.assertIn("4至10月",b["TW-13-034"]);self.assertIn("鑷子",b["TW-13-034"])
  self.assertIn("3起",b["TW-13-035"]);self.assertIn("重金屬",b["TW-13-035"])
  self.assertIn("119",b["TW-13-046"]);self.assertIn("CPR",b["TW-13-046"])
  for k in IDS:
   self.assertNotIn("撥120",b[k]);self.assertNotIn("打120",b[k])
   self.assertTrue("發生率" in b[k] or "發生頻率" in b[k],f"{k} 必須交代臺灣統計口徑或無法取得發生頻率的限制")
  self.assertIn("不能推算每年有多少登山客會感染",b["TW-13-035"])
  self.assertIn("不是全臺溪水採樣分母",b["TW-13-035"])
 def test_old_runtime_preserved(self):
  old=json.loads(subprocess.check_output(["git","show",BASE+":localization/tw-edition/runtime.json"],cwd=ROOT,text=True))
  rt=validate_runtime();ii={x["id"]:x for x in rt["items"]};ss={x["id"]:x for x in rt["sources"]}
  self.assertEqual(len(old["items"]),232)
  for x in old["items"]:assert_preserved_or_rechecked(self,x,ii[x["id"]])
  for x in old["sources"]:self.assertEqual(x,ss[x["id"]])
 def test_dynamic_progress(self):
  c=load("localization/tw-edition/coverage.json");p=publication_report();rt=validate_runtime()
  self.assertFalse(p["publication_ready"]);self.assertEqual(p["publication_total_entries"],765)
  self.assertEqual(c["core_reviewed_entries"],p["publication_completed_entries"])
  self.assertEqual(len(rt["items"]),p["publication_completed_entries"]+10)
  self.assertEqual(c["unique_draft_entries"]+c["entries_without_any_draft"],765)
  self.assertEqual(len(load("localization/tw-edition/sources/ch13-altitude-tick-water-alcohol-20261018.json")["sources"]),10)
  self.assertEqual(load("localization/ch13-altitude-tick-water-alcohol-20261018.json")["chapter_cumulative"],44)
if __name__=="__main__":unittest.main()

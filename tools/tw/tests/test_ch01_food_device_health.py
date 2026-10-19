"""第1章第二批臺灣食安、電池、血壓及成人健檢的逐條審閱與回歸。"""
import hashlib,json,subprocess,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from review_contract import ROOT,validate_entry,validate_runtime,publication_report
from body_renderer import body_blocks
BASE="7a53257e911c0e5632ef59b522142ded3dfd46dc"
IDS={"TW-01-005","TW-01-006","TW-01-007","TW-01-008"}
def load(p):return json.loads((ROOT/p).read_text(encoding="utf-8"))
class Chapter01FoodDeviceHealthTests(unittest.TestCase):
 def test_verified_bodies_reviews_source_and_renderer(self):
  entries={x["id"]:x for x in load("localization/manifest.json")["entries"]}
  rt=validate_runtime();items={x["id"]:x for x in rt["items"]};sources={x["id"]:x for x in rt["sources"]}
  for key in IDS:
   with self.subTest(id=key):
    e=entries[key];self.assertEqual(e["status"],"verified");self.assertTrue(validate_entry(e))
    raw=(ROOT/e["target_path"]).read_bytes();review=load("localization/reviews/"+key+".json")
    self.assertGreater(len(raw),1800);self.assertEqual(raw.decode("utf-8"),items[key]["body"])
    self.assertEqual(hashlib.sha256(raw).hexdigest(),review["target_sha256"])
    self.assertEqual(sum(b["tag"]=="h3" for b in body_blocks(items[key])),5)
    self.assertEqual({x["url"] for x in review["source_checks"]},{sources[s]["url"] for s in items[key]["source_ids"]})
 def test_frequency_limits_and_emergency(self):
  b={x["id"]:x["body"] for x in validate_runtime()["items"]}
  self.assertIn("4例",b["TW-01-005"]);self.assertIn("不是臺灣某一年的全國",b["TW-01-005"])
  self.assertIn("提高10倍",b["TW-01-006"]);self.assertIn("不是國內鋰電池起火件數增加10倍",b["TW-01-006"])
  self.assertIn("27.3%",b["TW-01-007"]);self.assertIn("2017至2020年",b["TW-01-007"])
  self.assertIn("每5年1次",b["TW-01-008"]);self.assertIn("每3年1次",b["TW-01-008"])
  for key in IDS:self.assertNotIn("撥120",b[key])
 def test_old_runtime_preservation(self):
  old=json.loads(subprocess.check_output(["git","show",BASE+":localization/tw-edition/runtime.json"],cwd=ROOT,text=True))
  rt=validate_runtime();ii={x["id"]:x for x in rt["items"]};ss={x["id"]:x for x in rt["sources"]}
  self.assertEqual(len(old["items"]),244)
  for x in old["items"]:self.assertEqual(x,ii[x["id"]])
  for x in old["sources"]:self.assertEqual(x,ss[x["id"]])
 def test_dynamic_progress(self):
  p=publication_report();c=load("localization/tw-edition/coverage.json");rt=validate_runtime()
  self.assertFalse(p["publication_ready"]);self.assertEqual(p["publication_total_entries"],765)
  self.assertGreaterEqual(p["publication_completed_entries"],238)
  self.assertEqual(c["core_reviewed_entries"],p["publication_completed_entries"])
  self.assertEqual(len(rt["items"]),p["publication_completed_entries"]+10)
  self.assertEqual(c["unique_draft_entries"]+c["entries_without_any_draft"],765)
  self.assertEqual(len(load("localization/tw-edition/sources/ch01-food-device-health-20261019.json")["sources"]),8)
if __name__=="__main__":unittest.main()

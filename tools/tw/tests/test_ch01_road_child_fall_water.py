"""第1章第三批及2026實質再審：臺灣道路、幼童車座、防墜與防溺統計契約。"""
import hashlib,json,subprocess,unittest,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from retroactive_audit import assert_preserved_or_rechecked
from review_contract import ROOT,validate_entry,validate_runtime,publication_report
from body_renderer import body_blocks
BASE="254a5edb32fc4aee5ba881c0cdf1521f4e66d462"
IDS={"TW-01-009","TW-01-010","TW-01-011","TW-01-012"}
def load(p):return json.loads((ROOT/p).read_text(encoding="utf-8"))
class Chapter01ChildSafetyTests(unittest.TestCase):
 def test_full_bodies_hash_review_sources_and_runtime(self):
  m={x["id"]:x for x in load("localization/manifest.json")["entries"]};rt=validate_runtime()
  items={x["id"]:x for x in rt["items"]};sources={x["id"]:x for x in rt["sources"]}
  for key in IDS:
   with self.subTest(key=key):
    e=m[key];self.assertEqual(e["status"],"verified");self.assertTrue(validate_entry(e))
    raw=(ROOT/e["target_path"]).read_bytes();rev=load("localization/reviews/"+key+".json")
    self.assertGreater(len(raw),1800);self.assertEqual(hashlib.sha256(raw).hexdigest(),rev["target_sha256"])
    self.assertEqual(raw.decode("utf-8"),items[key]["body"])
    self.assertEqual(sum(x["tag"]=="h3" for x in body_blocks(items[key])),5)
    self.assertEqual({x["url"] for x in rev["source_checks"]},{sources[x]["url"] for x in items[key]["source_ids"]})
 def test_frequency_denominator_and_local_safety(self):
  b={x["id"]:x["body"] for x in validate_runtime()["items"]}
  self.assertIn("143人",b["TW-01-009"]);self.assertIn("14名死者",b["TW-01-009"]);self.assertIn("沒有車流量",b["TW-01-009"])
  self.assertIn("後向",b["TW-01-010"]);self.assertIn("乘車旅次、正確使用情形與事故結果配對資料",b["TW-01-010"]);self.assertNotIn("2,858人",b["TW-01-010"])
  self.assertIn("沒有可核對的臺灣兒童窗戶或陽台墜落全國統計及居住暴露分母",b["TW-01-011"])
  self.assertIn("不可把不同事故類型的死亡合計當成窗戶或陽台墜落發生率",b["TW-01-011"])
  self.assertIn("窗戶或陽台墜落",b["TW-01-011"]);self.assertIn("全國統計",b["TW-01-011"]);self.assertIn("逃生",b["TW-01-011"])
  self.assertIn("2024年",b["TW-01-012"]);self.assertIn("叫、叫、伸、拋、划",b["TW-01-012"])
  for key in IDS:self.assertIn("119",b[key]);self.assertNotIn("打120",b[key])
 def test_preserve_original_248_entries_and_sources(self):
  old=json.loads(subprocess.check_output(["git","show",BASE+":localization/tw-edition/runtime.json"],cwd=ROOT,text=True))
  rt=validate_runtime();items={x["id"]:x for x in rt["items"]};sources={x["id"]:x for x in rt["sources"]}
  self.assertEqual(len(old["items"]),248)
  for x in old["items"]:assert_preserved_or_rechecked(self,x,items[x["id"]])
  for x in old["sources"]:self.assertEqual(x,sources[x["id"]])
 def test_dynamic_counts(self):
  c=load("localization/tw-edition/coverage.json");p=publication_report();rt=validate_runtime()
  self.assertFalse(p["publication_ready"]);self.assertGreaterEqual(p["publication_completed_entries"],242)
  self.assertEqual(c["core_reviewed_entries"],p["publication_completed_entries"])
  self.assertEqual(len(rt["items"]),p["publication_completed_entries"]+sum(i['id'].startswith('TW-NAV-') for i in rt['items']))
  self.assertEqual(c["unique_draft_entries"]+c["entries_without_any_draft"],765)
  self.assertEqual(len(load("localization/tw-edition/sources/ch01-road-child-fall-water-20261019.json")["sources"]),8)
if __name__=="__main__":unittest.main()

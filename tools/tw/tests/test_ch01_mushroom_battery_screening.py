"""第1章第二批：臺灣野菇、鋰電池、居家血壓與預防保健頻率。"""
import hashlib,json,subprocess,unittest,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from retroactive_audit import assert_preserved_or_rechecked
from review_contract import ROOT,validate_entry,validate_runtime,publication_report
from body_renderer import body_blocks
BASE="7a53257e911c0e5632ef59b522142ded3dfd46dc"
IDS={"TW-01-005","TW-01-006","TW-01-007","TW-01-008"}
def load(p):return json.loads((ROOT/p).read_text(encoding="utf-8"))
class Chapter01SecondBatchTests(unittest.TestCase):
 def test_complete_review_sha_runtime_sources(self):
  manifest={x["id"]:x for x in load("localization/manifest.json")["entries"]}
  rt=validate_runtime();items={x["id"]:x for x in rt["items"]};sources={x["id"]:x for x in rt["sources"]}
  for key in IDS:
   with self.subTest(key=key):
    e=manifest[key];self.assertEqual(e["status"],"verified");self.assertTrue(validate_entry(e))
    raw=(ROOT/e["target_path"]).read_bytes();review=load("localization/reviews/"+key+".json")
    self.assertGreater(len(raw),1800)
    self.assertEqual(hashlib.sha256(raw).hexdigest(),review["target_sha256"])
    self.assertEqual(raw.decode("utf-8"),items[key]["body"])
    self.assertEqual(sum(b["tag"]=="h3" for b in body_blocks(items[key])),5)
    self.assertEqual({x["url"] for x in review["source_checks"]},{sources[x]["url"] for x in items[key]["source_ids"]})
 def test_statistics_and_safety(self):
  b={x["id"]:x["body"] for x in validate_runtime()["items"]}
  self.assertIn("4例",b["TW-01-005"]);self.assertIn("不要自行催吐",b["TW-01-005"])
  self.assertIn("71件",b["TW-01-006"]);self.assertIn("絕非電動車起火率",b["TW-01-006"])
  self.assertIn("9.7%",b["TW-01-007"]);self.assertIn("722",b["TW-01-007"])
  self.assertIn("2.5%",b["TW-01-008"]);self.assertIn("30.8%",b["TW-01-008"]);self.assertIn("4.7%",b["TW-01-008"]);self.assertIn("47.5萬",b["TW-01-008"]);self.assertIn("19.3%",b["TW-01-008"]);self.assertIn("每5年1次",b["TW-01-008"])
  for key in IDS:self.assertIn("119",b[key]);self.assertNotIn("打120",b[key])
 def test_preserve_prior_244(self):
  old=json.loads(subprocess.check_output(["git","show",BASE+":localization/tw-edition/runtime.json"],cwd=ROOT,text=True))
  rt=validate_runtime();items={x["id"]:x for x in rt["items"]};sources={x["id"]:x for x in rt["sources"]}
  self.assertEqual(len(old["items"]),244)
  for x in old["items"]:assert_preserved_or_rechecked(self,x,items[x["id"]])
  for x in old["sources"]:self.assertEqual(x,sources[x["id"]])
 def test_dynamic_coverage(self):
  c=load("localization/tw-edition/coverage.json");p=publication_report();rt=validate_runtime()
  self.assertFalse(p["publication_ready"]);self.assertGreaterEqual(p["publication_completed_entries"],238)
  self.assertEqual(c["core_reviewed_entries"],p["publication_completed_entries"])
  self.assertEqual(len(rt["items"]),p["publication_completed_entries"]+sum(i['id'].startswith('TW-NAV-') for i in rt['items']))
  self.assertEqual(c["unique_draft_entries"]+c["entries_without_any_draft"],765)
  self.assertEqual(len(load("localization/tw-edition/sources/ch01-mushroom-battery-screening-20261019.json")["sources"]),8)
 def test_frequency_recheck_and_evidence_are_substantive(self):
  reg=load("localization/retroactive-review-register-20261019.json")["substantive_rechecks"]
  entries={}
  for row in reg:
   if row["id"] in {"TW-01-005","TW-01-007","TW-01-008"} and row.get("prior_revision")=="38d4c3d44fd164702d5e2ed44c9be2ebc5d788d9":
    entries[row["id"]]=row
  evidence=load("localization/ch01-p0-mushroom-bp-screening-recheck-20261026.json")
  articles={x["id"]:x for x in evidence["articles"]}
  expected={
   "TW-01-005":["4例","3人","暴露分母"],
   "TW-01-007":["28.9%","9.7%","不是年新發率"],
   "TW-01-008":["2.5%","30.8%","4.7%","47.5萬","19.3%","非全體人口"]}
  self.assertEqual(set(entries),set(expected));self.assertEqual(set(articles),set(expected))
  for key,terms in expected.items():
   with self.subTest(key=key):
    row=entries[key];article=articles[key]
    self.assertEqual(row["status"],"ai_source_rechecked_professional_pending")
    self.assertEqual(row["frequency_assessment"],article["frequency_assessment"])
    self.assertTrue(all(term in row["frequency_assessment"] for term in terms))
    self.assertEqual(row["after_sha256"],article["after_sha256"])
    self.assertEqual(set(row["source_ids"]),set(article["source_ids"]))
    self.assertTrue(row["limits"])
  self.assertFalse(evidence["counts_after"]["publication_ready"])
if __name__=="__main__":unittest.main()

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
  self.assertIn("19件",b["TW-01-001"]);self.assertIn("21人死亡",b["TW-01-001"]);self.assertNotIn("2,858人",b["TW-01-001"])
  self.assertIn("932人",b["TW-01-002"]);self.assertIn("初估",b["TW-01-002"]);self.assertIn("材料",b["TW-01-002"]);self.assertNotIn("衝擊吸收不符",b["TW-01-002"])
  self.assertIn("3,171次",b["TW-01-003"]);self.assertIn("不是全臺房屋戶數",b["TW-01-003"])
  self.assertIn("24件",b["TW-01-004"]);self.assertIn("22件",b["TW-01-004"]);self.assertNotIn("118件",b["TW-01-004"]);self.assertIn("沒有燃氣熱水器使用戶數",b["TW-01-004"])
  for key in IDS:
   self.assertIn("119",b[key]);self.assertTrue("頻率" in b[key] or "分母" in b[key])
   self.assertNotIn("撥120",b[key]);self.assertNotIn("打120",b[key])
 def test_october_26_historical_rechecks_and_frequency_evidence(self):
  evidence=load("localization/ch01-p0-transport-fire-fall-recheck-20261026.json")
  self.assertEqual(evidence["base_main_sha"],"ab51151e3cb4f3fc0e00a32e3f3295ad1bb3d502")
  self.assertEqual(set(evidence["scope"]["substantive_recheck_ids"]),{"TW-01-001","TW-01-002","TW-01-026","TW-01-034"})
  rt=validate_runtime();items={x["id"]:x for x in rt["items"]};entries={x["id"]:x for x in load("localization/manifest.json")["entries"]}
  sources={x["id"]:x for x in rt["sources"]};register=load("localization/retroactive-review-register-20261019.json")
  rows={x["id"]:x for x in register["substantive_rechecks"]}
  for key in evidence["scope"]["substantive_recheck_ids"]:
   with self.subTest(key=key):
    review=load("localization/reviews/"+key+".json");raw=(ROOT/entries[key]["target_path"]).read_bytes()
    self.assertEqual(hashlib.sha256(raw).hexdigest(),review["target_sha256"])
    self.assertEqual(raw.decode("utf-8"),items[key]["body"])
    self.assertEqual(set(entries[key]["sources"]),set(items[key]["source_ids"]))
    self.assertEqual({x["url"] for x in review["source_checks"]},{sources[s]["url"] for s in items[key]["source_ids"]})
    self.assertEqual(rows[key]["after_sha256"],review["target_sha256"])
  b={x["id"]:x["body"] for x in rt["items"]}
  self.assertIn("25,895次",b["TW-01-026"]);self.assertIn("71.5%",b["TW-01-026"]);self.assertIn("每三年",b["TW-01-026"])
  self.assertIn("墜落、滾落136人",b["TW-01-034"]);self.assertIn("墜落49人",b["TW-01-034"]);self.assertIn("TW-19-010.md",b["TW-01-034"])
  self.assertEqual(evidence["counts_after"]["substantive_rechecks"],evidence["counts_before"]["substantive_rechecks"]+len(evidence["scope"]["substantive_recheck_ids"]))
  self.assertEqual(evidence["counts_after"]["runtime_sources"],evidence["counts_before"]["runtime_sources"]+len(evidence["new_source_ids"]))
  self.assertEqual(evidence["counts_after"]["source_registry"],evidence["counts_before"]["source_registry"]+len(evidence["new_source_ids"]))
  self.assertGreaterEqual(len(register["substantive_rechecks"]),evidence["counts_after"]["substantive_rechecks"])
  self.assertGreaterEqual(len(rt["sources"]),evidence["counts_after"]["runtime_sources"])
  self.assertGreaterEqual(load("localization/tw-edition/coverage.json")["registry_sources"],evidence["counts_after"]["source_registry"])
 def test_fire_share_names_building_fire_event_denominator(self):
  b={x["id"]:x["body"] for x in validate_runtime()["items"]}
  self.assertIn("18,521次",b["TW-01-026"])
  self.assertIn("分母是全部25,895次建築物火災事件",b["TW-01-026"])
  self.assertIn("沒有家戶數、居住人口或住宅暴露時間分母",b["TW-01-026"])
  self.assertIn("不能換算成每戶起火機率",b["TW-01-026"])
 def test_fall_death_statistics_are_not_comparable_rates(self):
  b={x["id"]:x["body"] for x in validate_runtime()["items"]}
  self.assertIn("沒有工作者人數或工時分母",b["TW-01-034"])
  self.assertIn("不是墜落者致死率",b["TW-01-034"])
  self.assertIn("2025全年「墜落、滾落」與2026上半年「墜落」的分類和期間不同",b["TW-01-034"])
  self.assertIn("不能用來算個人墜落機率或直接比較趨勢",b["TW-01-034"])
 def test_recheck_batch_added_no_core_articles(self):
  evidence=load("localization/ch01-p0-transport-fire-fall-recheck-20261026.json")
  self.assertEqual(evidence["scope"]["new_core_ids"],[])
  self.assertEqual(evidence["counts_after"]["core_completed"],evidence["counts_before"]["core_completed"])
  self.assertEqual(evidence["counts_after"]["core_total"],evidence["counts_before"]["core_total"])
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

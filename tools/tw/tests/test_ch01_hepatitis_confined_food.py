"""危機先行、症狀分流、統計定義與原有來源保全。"""
import hashlib,json,subprocess,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from review_contract import ROOT,validate_entry,validate_runtime,publication_report
from body_renderer import body_blocks
from retroactive_audit import assert_preserved_or_rechecked,validate_recheck_history
BASE='91c2b57512020cc80ddd84afdeaeedbe0d296895'
NEW={f'TW-01-{n:03}' for n in range(45,49)}
RECHECK={f'TW-13-{n:03}' for n in (28,29,45,46)}
def read(p):return json.loads((ROOT/p).read_text())
class HepatitisConfinedFoodTests(unittest.TestCase):
 def test_formal_sources_hash_and_rendering(self):
  rt=validate_runtime();ii={x['id']:x for x in rt['items']};ss={s['id']:s for s in rt['sources']};mm={e['id']:e for e in read('localization/manifest.json')['entries']}
  for key in NEW|RECHECK:
   with self.subTest(key=key):
    self.assertTrue(validate_entry(mm[key]));i=ii[key];rv=read(f'localization/reviews/{key}.json');raw=(ROOT/i['target_path']).read_bytes()
    self.assertEqual(raw.decode(),i['body']);self.assertEqual(hashlib.sha256(raw).hexdigest(),rv['target_sha256'])
    self.assertEqual({x['url'] for x in rv['source_checks']},{ss[s]['url'] for s in i['source_ids']})
    self.assertEqual(sum(x['tag']=='h3' for x in body_blocks(i)),5)
 def test_emergency_actions_and_denominator_boundaries(self):
  b={x['id']:x['body'] for x in validate_runtime()['items']}
  self.assertIn('1986',b['TW-01-045']);self.assertIn('RNA',b['TW-01-045']);self.assertIn('重新感染',b['TW-01-045'])
  self.assertIn('不可入內救人',b['TW-01-046']);self.assertIn('開蓋',b['TW-01-046'])
  self.assertIn('不是胃鏡',b['TW-01-047']);self.assertIn('騎車',b['TW-01-047'])
  self.assertIn('110件',b['TW-01-048']);self.assertIn('冷藏',b['TW-01-048'])
  self.assertIn('停止發抖',b['TW-13-028']);self.assertIn('979',b['TW-13-029'])
  self.assertIn('減傷',b['TW-13-045']);self.assertIn('停止喝酒後',b['TW-13-046'])
 def test_report_uses_registry_and_live_reading_counts(self):
  from ci_language_policy import audit_drafts
  rt=validate_runtime();batch=read('localization/ch01-hepatitis-confined-food-20261019.json');counts=batch['counts']
  # 批次數字是歷史快照；後續合法增修不能被舊總數凍結。
  self.assertEqual(counts['source_registry_after'],counts['source_registry_before']+batch['sources_added'])
  self.assertGreaterEqual(audit_drafts()['registry_sources'],counts['source_registry_after'])
  self.assertEqual(counts['runtime_after'],counts['runtime_before']+len(batch['new_core_ids'])+len(batch['new_navigation_ids']))
  self.assertGreaterEqual(len(rt['items']),counts['runtime_after'])
  core=sum(not x['id'].startswith('TW-NAV-') for x in rt['items'])
  self.assertEqual(counts['core_after'],counts['core_before']+len(batch['new_core_ids']));self.assertGreaterEqual(core,counts['core_after']);self.assertIn('臺灣生活情境',rt['scope']);self.assertNotRegex(rt['scope'],r'\d+\s*(?:條|項)')
 def test_official_confined_space_term_is_not_generic_character_exemption(self):
  from ci_language_policy import canonical
  from traditionalize import cc
  self.assertEqual(canonical('局限空間'),canonical(cc().convert('局限空間')))
  self.assertNotEqual(canonical('安全\u8bbe\u5907'),canonical(cc().convert('安全\u8bbe\u5907')))
 def test_audit_scope_uses_actual_navigation_count(self):
  from retroactive_audit import audit
  rt=validate_runtime();n=sum(i['id'].startswith('TW-NAV-') for i in rt['items'])
  self.assertIn(str(n)+'則補充',audit()['scope'])
 def test_standalone_occupational_guide_contract(self):
  rt=validate_runtime();i=next(x for x in rt['items'] if x['id']=='TW-NAV-011');rv=read('localization/reviews/TW-NAV-011.json');raw=(ROOT/i['target_path']).read_bytes()
  self.assertEqual(raw.decode(),i['body']);self.assertEqual(hashlib.sha256(raw).hexdigest(),rv['target_sha256']);self.assertEqual(sum(x['tag']=='h3' for x in body_blocks(i)),5)
  ss={x['id']:x for x in rt['sources']};self.assertEqual({ss[k]['url'] for k in i['source_ids']},{x['url'] for x in rv['source_checks']})
  for term in ['承攬','開工','高處','機械','用電','化學品','局限空間','熱','搬運','輪班','霸凌','停止','8小時','2026-07-01']:
   self.assertIn(term,i['body'])
  self.assertNotIn('TW-NAV-011',{e['id'] for e in read('localization/manifest.json')['entries']})
 def test_all_prior_content_and_actual_review_history(self):
  old=json.loads(subprocess.check_output(['git','show',BASE+':localization/tw-edition/runtime.json'],cwd=ROOT));rt=validate_runtime();ii={x['id']:x for x in rt['items']};ss={s['id']:s for s in rt['sources']}
  for row in old['items']:assert_preserved_or_rechecked(self,row,ii[row['id']])
  for row in old['sources']:self.assertEqual(row,ss[row['id']])
  rr={r['id']:r for r in read('localization/retroactive-review-register-20261019.json')['substantive_rechecks']}
  for key in RECHECK:
   self.assertEqual(rr[key]['status'],'ai_source_rechecked_professional_pending');validate_recheck_history(ROOT,rr[key],ii[key])
  self.assertFalse(publication_report()['publication_ready'])
if __name__=='__main__':unittest.main()

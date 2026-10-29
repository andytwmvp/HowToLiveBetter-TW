"""危機先行、症狀分流、統計定義與原有來源保全。"""
import hashlib,json,subprocess,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from review_contract import ROOT,validate_entry,validate_runtime,publication_report
from body_renderer import body_blocks
from retroactive_audit import assert_preserved_or_rechecked,validate_recheck_history
BASE='aa3aa1c19a1c88b6e1ecf95424086fa59da965e4'
NEW={f'TW-01-{n:03}' for n in range(33,37)}
RECHECK={f'TW-13-{n:03}' for n in (8,9,10,11)}
def read(p):return json.loads((ROOT/p).read_text())
class RiskResponseTests(unittest.TestCase):
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
  self.assertIn('先撥119',b['TW-01-033']);self.assertIn('不催吐',b['TW-01-033']);self.assertIn('不能保證',b['TW-01-033'])
  self.assertLess(b['TW-01-034'].index('119'),b['TW-01-034'].index('136'));self.assertIn('不是墜落者致死率',b['TW-01-034'])
  self.assertIn('無償',b['TW-01-035']);self.assertIn('2015年7月1日',b['TW-01-035']);self.assertIn('2023年1月1日',b['TW-01-035']);self.assertNotIn('2015-07-03',b['TW-01-035']);self.assertNotIn('86%',b['TW-01-035'])
  self.assertIn('不觸碰',b['TW-01-036']);self.assertIn('0800-088-928',b['TW-01-036']);self.assertIn('不能保證安全',b['TW-01-036'])
  for key in RECHECK:self.assertIn('頻率',b[key])
  self.assertIn('分母',b['TW-13-008']);self.assertIn('90%',b['TW-13-009']);self.assertIn('無法估算',b['TW-13-010']);self.assertIn('不自行扳腳尖',b['TW-13-011'])
 def test_report_uses_registry_and_live_reading_counts(self):
  from ci_language_policy import audit_drafts
  rt=validate_runtime();batch=read('localization/ch01-risk-response-20261019.json');counts=batch['counts']
  # 批次數字是歷史快照；後續合法增修不能被舊總數凍結。
  self.assertEqual(counts['source_registry_after'],counts['source_registry_before']+batch['sources_added'])
  self.assertGreaterEqual(audit_drafts()['registry_sources'],counts['source_registry_after'])
  self.assertEqual(counts['runtime_after'],counts['runtime_before']+len(batch['new_core_ids']))
  self.assertGreaterEqual(len(rt['items']),counts['runtime_after'])
  core=sum(not x['id'].startswith('TW-NAV-') for x in rt['items'])
  self.assertEqual(counts['core_after'],counts['core_before']+len(batch['new_core_ids']));self.assertGreaterEqual(core,counts['core_after']);self.assertIn('臺灣生活情境',rt['scope']);self.assertNotRegex(rt['scope'],r'\d+\s*(?:條|項)')
 def test_all_prior_content_and_actual_review_history(self):
  old=json.loads(subprocess.check_output(['git','show',BASE+':localization/tw-edition/runtime.json'],cwd=ROOT));rt=validate_runtime();ii={x['id']:x for x in rt['items']};ss={s['id']:s for s in rt['sources']}
  for row in old['items']:assert_preserved_or_rechecked(self,row,ii[row['id']])
  for row in old['sources']:self.assertEqual(row,ss[row['id']])
  rr={r['id']:r for r in read('localization/retroactive-review-register-20261019.json')['substantive_rechecks']}
  for key in RECHECK:
   self.assertEqual(rr[key]['status'],'ai_source_rechecked_professional_pending');validate_recheck_history(ROOT,rr[key],ii[key])
  self.assertFalse(publication_report()['publication_ready'])
if __name__=='__main__':unittest.main()

"""危機先行、症狀分流、統計定義與原有來源保全。"""
import hashlib,json,subprocess,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from review_contract import ROOT,validate_entry,validate_runtime,publication_report
from body_renderer import body_blocks
from retroactive_audit import assert_preserved_or_rechecked,validate_recheck_history
BASE='69da58f9df6e4f5046d71b9c7b9112efe7bc9f62'
NEW={f'TW-01-{n:03}' for n in range(41,45)}
RECHECK={f'TW-13-{n:03}' for n in (21,22,23,27)}
def read(p):return json.loads((ROOT/p).read_text())
class IceToolsCrisisAFTests(unittest.TestCase):
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
  self.assertIn('不以15公分',b['TW-01-041']);self.assertIn('海外',b['TW-01-041'])
  self.assertIn('鋸齒',b['TW-01-042']);self.assertIn('護罩',b['TW-01-042']);self.assertIn('17例',b['TW-01-042'])
  self.assertIn('不要承諾保密',b['TW-01-043']);self.assertIn('119',b['TW-01-043']);self.assertIn('資料限制',b['TW-01-043'])
  self.assertIn('1.51',b['TW-01-044']);self.assertIn('2011',b['TW-01-044']);self.assertIn('阿斯匹靈',b['TW-01-044']);self.assertIn('人年',b['TW-01-044'])
  self.assertIn('不等找出物質',b['TW-13-021']);self.assertIn('退燒藥',b['TW-13-022']);self.assertIn('監測人次',b['TW-13-023']);self.assertIn('不採333',b['TW-13-027'])
 def test_report_uses_registry_and_live_reading_counts(self):
  from ci_language_policy import audit_drafts
  rt=validate_runtime();batch=read('localization/ch01-ice-tools-crisis-af-20261019.json');counts=batch['counts']
  # 批次數字是歷史快照；後續合法增修不能被舊總數凍結。
  self.assertEqual(counts['source_registry_after'],counts['source_registry_before']+batch['sources_added'])
  self.assertGreaterEqual(audit_drafts()['registry_sources'],counts['source_registry_after'])
  self.assertEqual(counts['runtime_after'],counts['runtime_before']+len(batch['new_core_ids']))
  self.assertGreaterEqual(len(rt['items']),counts['runtime_after'])
  core=sum(not x['id'].startswith('TW-NAV-') for x in rt['items'])
  self.assertEqual(counts['core_after'],counts['core_before']+len(batch['new_core_ids']));self.assertGreaterEqual(core,counts['core_after']);self.assertIn(str(core)+'條',rt['scope']);self.assertIn(str(len(rt['items']))+'項',rt['scope'])
 def test_all_prior_content_and_actual_review_history(self):
  old=json.loads(subprocess.check_output(['git','show',BASE+':localization/tw-edition/runtime.json'],cwd=ROOT));rt=validate_runtime();ii={x['id']:x for x in rt['items']};ss={s['id']:s for s in rt['sources']}
  for row in old['items']:assert_preserved_or_rechecked(self,row,ii[row['id']])
  for row in old['sources']:self.assertEqual(row,ss[row['id']])
  rr={r['id']:r for r in read('localization/retroactive-review-register-20261019.json')['substantive_rechecks']}
  for key in RECHECK:
   self.assertEqual(rr[key]['status'],'ai_source_rechecked_professional_pending');validate_recheck_history(ROOT,rr[key],ii[key])
  self.assertFalse(publication_report()['publication_ready'])
if __name__=='__main__':unittest.main()

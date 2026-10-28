"""危機先行、症狀分流、統計定義與原有來源保全。"""
import hashlib,json,subprocess,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from review_contract import ROOT,validate_entry,validate_runtime,publication_report
from body_renderer import body_blocks
from retroactive_audit import assert_preserved_or_rechecked,validate_recheck_history,validate_reader_copy_cleanup_history
BASE='201fd64e138880528ce6d9effc86d06fe67f36cb'
NEW={f'TW-01-{n:03}' for n in range(37,41)}
RECHECK={f'TW-13-{n:03}' for n in (16,17,18,19)}
def read(p):return json.loads((ROOT/p).read_text())
class GamblingPrepBoneTests(unittest.TestCase):
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
  self.assertIn('不交付密碼',b['TW-01-037']);self.assertIn('資料不足',b['TW-01-037'])
  self.assertIn('35歲',b['TW-01-038']);self.assertIn('72小時',b['TW-01-038']);self.assertIn('名額',b['TW-01-038']);self.assertNotIn('約七成',b['TW-01-038'])
  self.assertIn('14.1%',b['TW-01-039']);self.assertIn('不是',b['TW-01-039']);self.assertIn('健保',b['TW-01-039'])
  self.assertIn('不能取代',b['TW-01-040']);self.assertIn('2026-08-01',b['TW-01-040']);self.assertIn('停藥',b['TW-01-040'])
  self.assertIn('不是所有人都等五分鐘',b['TW-13-016']);self.assertIn('能安全吞嚥',b['TW-13-017']);self.assertIn('找冰或把固定做得完美延誤救援',b['TW-13-041']);self.assertIn('冰水容器',b['TW-13-047']);self.assertIn('1911',b['TW-13-018']);self.assertIn('頻率',b['TW-13-019'])
 def test_report_uses_registry_and_live_reading_counts(self):
  from ci_language_policy import audit_drafts
  rt=validate_runtime();batch=read('localization/ch01-gambling-prep-bone-20261019.json');counts=batch['counts']
  # 批次數字是歷史快照；後續合法增修不能被舊總數凍結。
  self.assertEqual(counts['source_registry_after'],counts['source_registry_before']+batch['sources_added'])
  self.assertGreaterEqual(audit_drafts()['registry_sources'],counts['source_registry_after'])
  self.assertEqual(counts['runtime_after'],counts['runtime_before']+len(batch['new_core_ids']))
  self.assertGreaterEqual(len(rt['items']),counts['runtime_after'])
  core=sum(not x['id'].startswith('TW-NAV-') for x in rt['items'])
  self.assertEqual(counts['core_after'],counts['core_before']+len(batch['new_core_ids']));self.assertGreaterEqual(core,counts['core_after']);self.assertIn('臺灣生活情境',rt['scope']);self.assertNotRegex(rt['scope'],r'\d+\s*(?:條|項)')
 def test_recheck_metadata_changes_are_bound_to_body_and_protected_fields(self):
  import copy
  from retroactive_audit import documented_revision
  old=next(x for x in json.loads(subprocess.check_output(['git','show',BASE+':localization/tw-edition/runtime.json'],cwd=ROOT))['items'] if x['id']=='TW-13-016')
  new=next(x for x in validate_runtime()['items'] if x['id']==old['id'])
  register=read('localization/retroactive-review-register-20261019.json')
  rec=next(x for x in register['substantive_rechecks'] if x['id']==old['id'])
  cleanup=next(x for x in register['reader_copy_cleanups'] if x['id']==old['id'] and x['after_sha256']==hashlib.sha256(new['body'].encode()).hexdigest())
  rechecked=validate_reader_copy_cleanup_history(ROOT,cleanup,new)
  self.assertTrue(documented_revision(old,rechecked,rec))
  for field,value in [('title','與正文不同的標題'),('limits','正文沒有的限制'),('eligibility',{'automatic':True}),('target_path','locales/zh-TW/wrong.md'),('review_status','verified'),('question','沒有對應正文的提問')]:
   bad=copy.deepcopy(rechecked);bad[field]=value
   with self.subTest(field=field):self.assertFalse(documented_revision(old,bad,rec))
 def test_all_prior_content_and_actual_review_history(self):
  old=json.loads(subprocess.check_output(['git','show',BASE+':localization/tw-edition/runtime.json'],cwd=ROOT));rt=validate_runtime();ii={x['id']:x for x in rt['items']};ss={s['id']:s for s in rt['sources']}
  for row in old['items']:assert_preserved_or_rechecked(self,row,ii[row['id']])
  for row in old['sources']:self.assertEqual(row,ss[row['id']])
  rr={r['id']:r for r in read('localization/retroactive-review-register-20261019.json')['substantive_rechecks']}
  for key in RECHECK:
   self.assertEqual(rr[key]['status'],'ai_source_rechecked_professional_pending');validate_recheck_history(ROOT,rr[key],ii[key])
  self.assertFalse(publication_report()['publication_ready'])
if __name__=='__main__':unittest.main()

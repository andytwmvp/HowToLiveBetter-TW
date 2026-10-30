"""醫療照護歷史再審：急症不等候、統計口徑、真正Git保全。"""
import hashlib,json,subprocess,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from review_contract import ROOT,validate_runtime,publication_report
from retroactive_audit import assert_preserved_or_rechecked,validate_recheck_history
BASE='2a003509a3a0dd5402441ca6cb82d8d20867ce3e'
IDS={'TW-16-012','TW-17-008','TW-17-013','TW-24-007'}
def load(p):return json.loads((ROOT/p).read_text())
class MedicalCareTests(unittest.TestCase):
 def test_actual_history_body_reviews_and_sources(self):
  rt=validate_runtime();items={i['id']:i for i in rt['items']};rows={r['id']:r for r in load('localization/retroactive-review-register-20261019.json')['substantive_rechecks']};sources={s['id']:s for s in rt['sources']}
  for key in IDS:
   i=items[key];r=rows[key];rv=load('localization/reviews/'+key+'.json');validate_recheck_history(ROOT,r,i)
   self.assertEqual((ROOT/i['target_path']).read_text(),i['body']);self.assertEqual(rv['target_sha256'],hashlib.sha256(i['body'].encode()).hexdigest());self.assertNotEqual(r['before_sha256'],r['after_sha256']);self.assertEqual({c['url'] for c in rv['source_checks']},{sources[s]['url'] for s in i['source_ids']})
 def test_all_old_items_and_source_objects_preserved(self):
  old=json.loads(subprocess.check_output(['git','show',BASE+':localization/tw-edition/runtime.json'],cwd=ROOT));rt=validate_runtime();items={i['id']:i for i in rt['items']};sources={s['id']:s for s in rt['sources']}
  old_ids=[i['id'] for i in old['items']]
  self.assertEqual(old_ids,[i['id'] for i in rt['items'] if i['id'] in set(old_ids)])
  for i in old['items']:assert_preserved_or_rechecked(self,i,items[i['id']])
  for s in old['sources']:self.assertEqual(s,sources[s['id']])
 def test_emergency_action_precedes_frequency_context(self):
  bodies={i['id']:i['body'] for i in validate_runtime()['items']}
  for key in IDS:
   self.assertLess(bodies[key].index('119'),bodies[key].index('事件頻率'))
  for key,terms in {'TW-16-012':['不能等','長效藥','停電','不自行估算'],'TW-24-007':['重新評估','不同階段','安全期限','不表示所有費用免費'],'TW-17-013':['即使原有失智','不自行加鎮靜藥','確診不等於自動補助'],'TW-17-008':['醫療管路','不為減壓拔除','證據確定性極低','不能解讀成買氣墊床就自行延長']}.items():
   for t in terms:self.assertIn(t,bodies[key])
 def test_survey_scope_and_missing_raw_denominators(self):
  batch=load('localization/medical-care-20261020.json');s=batch['statistics'][0]
  self.assertEqual(s['value'],7.99);self.assertEqual(s['period'],'2020至2023年執行調查');self.assertIsNone(s['numerator']);self.assertIsNone(s['denominator']);self.assertIn('MCI',s['definition']);self.assertIn('分層多階段群集抽樣',s['method']);self.assertIn('非2026新發',s['limitations'])
  body=next(i['body'] for i in validate_runtime()['items'] if i['id']=='TW-17-013')
  for t in ['22縣市','65歲以上','7.99%','輕度認知障礙','信賴區間','2026-01-01']:self.assertIn(t,body)
 def test_failed_retrieval_and_professional_limits_remain_explicit(self):
  b=load('localization/medical-care-20261020.json');self.assertEqual(set(b['ai_rechecked_ids']),IDS);self.assertEqual(b['new_core_ids'],[]);self.assertEqual(b['professional_review'],'pending');self.assertFalse(publication_report()['publication_ready'])
  rv=load('localization/reviews/TW-16-012.json');gold=next(c for c in rv['source_checks'] if 'goldcopd.org' in c['url']);self.assertEqual(gold['accessed_at'],'2026-10-17');self.assertIn('未重讀全文',gold['retrieval_method'])
  self.assertTrue(all(r['status']=='ai_source_rechecked_professional_pending' for r in load('localization/retroactive-review-register-20261019.json')['substantive_rechecks']))
if __name__=='__main__':unittest.main()

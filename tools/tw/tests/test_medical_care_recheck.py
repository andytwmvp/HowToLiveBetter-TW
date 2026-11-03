"""醫療照護歷史再審：急症不等候、統計口徑、真正Git保全。"""
import hashlib,json,subprocess,sys,unittest,re
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
  for key in IDS-{'TW-16-014'}:
   body=bodies[key]
   self.assertIn('119',body)
   statistical_heading=re.search(r'(?m)^## .*?(?:事件頻率|發生頻率|統計|數據|資料限制)',body)
   reference_heading=body.index('## 參考資料')
   if statistical_heading:
    self.assertLess(body.index('119'),statistical_heading.start())
   else:
    self.assertLess(body.index('119'),reference_heading)
  self.assertLess(bodies['TW-16-014'].index('運動中胸痛'),bodies['TW-16-014'].index('研究數據與臺灣適用限制'))
  for key,terms in {'TW-16-012':['不要先等血氧機數字','不要自行加用長效吸入藥','停電','不能當成全國發生率或個人年度風險'],'TW-24-007':['重新評估','不同階段','安全期限','不表示所有費用免費'],'TW-17-013':['即使原本已確診失智','不要自行診斷、加鎮靜藥','確診不代表自動取得特定服務'],'TW-17-008':['醫療管路','不為減壓拔除','證據確定性極低','不能因買了氣墊床就自行延長間隔']}.items():
   for t in terms:self.assertIn(t,bodies[key])
 def test_survey_scope_and_missing_raw_denominators(self):
  batch=load('localization/medical-care-20261020.json');s=batch['statistics'][0]
  self.assertEqual(s['value'],7.99);self.assertEqual(s['period'],'2020至2023年執行調查');self.assertIsNone(s['numerator']);self.assertIsNone(s['denominator']);self.assertIn('MCI',s['definition']);self.assertIn('分層多階段群集抽樣',s['method']);self.assertIn('非2026新發',s['limitations'])
  body=next(i['body'] for i in validate_runtime()['items'] if i['id']=='TW-17-013')
  for t in ['22縣市','65歲以上','7.99%','輕度認知障礙','信賴區間','2026年1月1日']:self.assertIn(t,body)
 def test_failed_retrieval_and_professional_limits_remain_explicit(self):
  b=load('localization/medical-care-20261020.json');self.assertEqual(set(b['ai_rechecked_ids']),IDS);self.assertEqual(b['new_core_ids'],[]);self.assertEqual(b['professional_review'],'pending');self.assertFalse(publication_report()['publication_ready'])
  rows=load('localization/retroactive-review-register-20261019.json')['substantive_rechecks']
  historic=next(r for r in rows if r['id']=='TW-16-012' and r['reviewed_at']=='2026-10-20')
  gold=next(c for c in historic['source_checks'] if 'goldcopd.org' in c['url']);self.assertEqual(gold['accessed_at'],'2026-10-17');self.assertIn('未重讀全文',gold['retrieval_method'])
  self.assertFalse(any('goldcopd.org' in c['url'] for c in load('localization/reviews/TW-16-012.json')['source_checks']))
  self.assertTrue(all(r['status']=='ai_source_rechecked_professional_pending' for r in load('localization/retroactive-review-register-20261019.json')['substantive_rechecks']))
if __name__=='__main__':unittest.main()

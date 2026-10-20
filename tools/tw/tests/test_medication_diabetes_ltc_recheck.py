"""用藥糖尿病長照再審：歷史保全、危急分流、統計及給付界線。"""
import hashlib,json,subprocess,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from review_contract import ROOT,validate_runtime,publication_report
from retroactive_audit import assert_preserved_or_rechecked,validate_recheck_history
BASE='989529392f44ab35bbc58852fc617f8b8c735d93';IDS={'TW-16-001','TW-16-007','TW-16-013','TW-24-013','TW-17-007'}
def load(p):return json.loads((ROOT/p).read_text())
class MedicationDiabetesLTCTests(unittest.TestCase):
 def test_real_git_body_review_and_source_contracts(self):
  rt=validate_runtime();items={i['id']:i for i in rt['items']};sources={s['id']:s for s in rt['sources']};rows={r['id']:r for r in load('localization/retroactive-review-register-20261019.json')['substantive_rechecks']}
  for key in IDS:
   i=items[key];rv=load('localization/reviews/'+key+'.json');validate_recheck_history(ROOT,rows[key],i);self.assertEqual((ROOT/i['target_path']).read_text(),i['body']);self.assertEqual(rv['target_sha256'],hashlib.sha256(i['body'].encode()).hexdigest());self.assertEqual({c['url'] for c in rv['source_checks']},{sources[s]['url'] for s in i['source_ids']})
 def test_original_reading_and_sources_preserved(self):
  old=json.loads(subprocess.check_output(['git','show',BASE+':localization/tw-edition/runtime.json'],cwd=ROOT));rt=validate_runtime();items={i['id']:i for i in rt['items']};sources={s['id']:s for s in rt['sources']};self.assertEqual([i['id'] for i in old['items']],[i['id'] for i in rt['items']])
  for i in old['items']:assert_preserved_or_rechecked(self,i,items[i['id']])
  for s in old['sources']:self.assertEqual(s,sources[s['id']])
 def test_urgent_actions_and_specific_dangerous_inferences(self):
  b={i['id']:i['body'] for i in validate_runtime()['items']}
  for key in IDS:self.assertLess(b[key].index('119'),b[key].index('事件頻率'))
  terms={'TW-16-001':['硬吞下一劑','不共用','不自行雙倍補服'],'TW-16-007':['即使不痛','不赤腳','不自行剪除'],'TW-16-013':['不表示急性變化可先等三個月','不代表'], 'TW-24-013':['不可替代','同價或低於原價','並告知','避免因外觀不同重複吃'],'TW-17-007':['不是必須先等滿六個月','不是所有剛出院者都自動符合PAC資格','不是直接匯給家庭的現金']}
  terms['TW-16-013']=['不表示急性變化可先等三個月','不能改稱全臺慢性腎病盛行率']
  for key,ts in terms.items():
   for t in ts:self.assertIn(t,b[key])
 def test_statistic_and_effective_dates_do_not_imply_personal_rates(self):
  batch=load('localization/medication-diabetes-ltc-20261020.json');s=batch['statistics'][0];self.assertEqual(s['value'],15);self.assertIn('2023',s['period']);self.assertIsNone(s['numerator']);self.assertIsNone(s['denominator']);self.assertIn('非全臺CKD',s['limitations']);dates={d['topic']:d for d in batch['legal_evidence']};self.assertEqual(dates['健保醫療辦法26條替代']['effective_at'],'2018-04-29');self.assertEqual(dates['健保醫療辦法22條慢箋']['effective_at'],'2024-08-01');self.assertEqual(dates['長照服務法3條定義']['effective_at'],'2017-06-03')
 def test_no_claim_of_unread_full_text_or_professional_completion(self):
  batch=load('localization/medication-diabetes-ltc-20261020.json');self.assertEqual(set(batch['ai_rechecked_ids']),IDS);self.assertEqual(batch['new_core_ids'],[]);self.assertEqual(batch['professional_review'],'pending');self.assertFalse(publication_report()['publication_ready'])
  for key in ['TW-16-007','TW-16-013']:
   rv=load('localization/reviews/'+key+'.json');ada=[c for c in rv['source_checks'] if 'diabetesjournals.org' in c['url']];self.assertTrue(ada);self.assertTrue(all(c['accessed_at']=='2026-10-17' and '未冒稱全文' in c['retrieval_method'] for c in ada))
if __name__=='__main__':unittest.main()

"""醫爭、身障、植牙與門診之歷史及安全契約。"""
import hashlib,json,subprocess,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from review_contract import ROOT,validate_runtime,publication_report
from retroactive_audit import assert_preserved_or_rechecked,validate_recheck_history
BASE='525f87c5840ef437fbbdcdab36def0d1c171560c';IDS={'TW-24-006','TW-24-010','TW-24-012','TW-24-002'}
def load(p):return json.loads((ROOT/p).read_text())
class MedicalAccessRecheckTests(unittest.TestCase):
 def test_history_body_review_and_sources(self):
  rt=validate_runtime();items={i['id']:i for i in rt['items']};sources={s['id']:s for s in rt['sources']};rows={r['id']:r for r in load('localization/retroactive-review-register-20261019.json')['substantive_rechecks']}
  for k in IDS:
   i=items[k];rv=load('localization/reviews/'+k+'.json');validate_recheck_history(ROOT,rows[k],i);self.assertEqual((ROOT/i['target_path']).read_text(),i['body']);self.assertEqual(rv['target_sha256'],hashlib.sha256(i['body'].encode()).hexdigest());self.assertEqual(rv['source_checks'],rows[k]['source_checks']);self.assertEqual({c['url'] for c in rv['source_checks']},{sources[s]['url'] for s in i['source_ids']})
 def test_all_previous_content_and_source_objects_preserved(self):
  old=json.loads(subprocess.check_output(['git','show',BASE+':localization/tw-edition/runtime.json'],cwd=ROOT));rt=validate_runtime();items={i['id']:i for i in rt['items']};sources={s['id']:s for s in rt['sources']};self.assertEqual([i['id'] for i in old['items']],[i['id'] for i in rt['items']])
  for i in old['items']:assert_preserved_or_rechecked(self,i,items[i['id']])
  for s in old['sources']:self.assertEqual(s,sources[s['id']])
 def test_urgent_care_before_frequency_and_procedural_boundaries(self):
  b={i['id']:i['body'] for i in validate_runtime()['items']}
  for k in IDS:self.assertLess(b[k].index('119'),b[k].index('事件頻率'))
  terms={'TW-24-006':['調解程序不收費','七個工作日','齊備起四十五日','不是所有求償','法院核定'],'TW-24-010':['三十日內','四成作業費','不是所有補助駁回','不等於整個申請二十日','到宅'],'TW-24-012':['不要自行停用','書面全案報價','異常出血','不是全臺療效研究'],'TW-24-002':['不是總帳單','170元、420元','掛號費不是','同次同醫師併行']}
  for k,ts in terms.items():
   for t in ts:self.assertIn(t,b[k])
 def test_retired_mismatched_reference_keeps_provenance(self):
  rt=validate_runtime();i=next(i for i in rt['items'] if i['id']=='TW-24-012');self.assertNotIn('ch24_materials',i['source_ids']);old=json.loads(subprocess.check_output(['git','show',BASE+':localization/tw-edition/runtime.json'],cwd=ROOT));prior=next(s for s in old['sources'] if s['id']=='ch24_materials');self.assertEqual(prior,next(s for s in rt['sources'] if s['id']=='ch24_materials'));r=next(r for r in load('localization/retroactive-review-register-20261019.json')['substantive_rechecks'] if r['id']==i['id']);self.assertEqual(r['retired_sources'][0]['prior_source_sha256'],hashlib.sha256(json.dumps(prior,ensure_ascii=False,sort_keys=True).encode()).hexdigest());self.assertIn('APP',r['retired_sources'][0]['reason'])
 def test_evidence_dates_frequency_and_professional_limits(self):
  x=load('localization/disputes-disability-dental-costs-20261021.json');self.assertEqual(x['statistics'],[]);self.assertEqual(set(x['frequency_assessments']),IDS);self.assertEqual(x['new_core_ids'],[]);self.assertEqual(x['professional_review'],'pending');self.assertFalse(publication_report()['publication_ready']);e=x['legal_evidence'][0];self.assertEqual((e['announced_at'],e['effective_at']),('2022-06-22','2024-01-01'));self.assertIsNone(x['legal_evidence'][2]['effective_at']);self.assertEqual(x['legal_evidence'][1]['effective_at'],'2026-07-01');self.assertEqual(x['legal_evidence'][1]['calculation_source_id'],'ch01_law_effective_day')
  for z in x['frequency_assessments'].values():self.assertIn('不能',z)
if __name__=='__main__':unittest.main()

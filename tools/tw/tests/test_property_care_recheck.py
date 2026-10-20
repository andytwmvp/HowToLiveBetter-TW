"""監護與財產之歷史及安全契約。"""
import hashlib,json,subprocess,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from review_contract import ROOT,validate_runtime,publication_report
from retroactive_audit import assert_preserved_or_rechecked,validate_recheck_history
BASE='22064b9b0c624fcce185ee5697569a2f74b38055';IDS={'TW-17-001','TW-17-003','TW-17-005','TW-17-006'}
def load(p):return json.loads((ROOT/p).read_text())
class PropertyCareRecheckTests(unittest.TestCase):
 def test_history_body_review_and_sources(self):
  rt=validate_runtime();items={i['id']:i for i in rt['items']};sources={s['id']:s for s in rt['sources']};rows={r['id']:r for r in load('localization/retroactive-review-register-20261019.json')['substantive_rechecks']}
  for k in IDS:
   i=items[k];rv=load('localization/reviews/'+k+'.json');validate_recheck_history(ROOT,rows[k],i);self.assertEqual((ROOT/i['target_path']).read_text(),i['body']);self.assertEqual(rv['target_sha256'],hashlib.sha256(i['body'].encode()).hexdigest());self.assertEqual(rv['source_checks'],rows[k]['source_checks']);self.assertEqual({c['url'] for c in rv['source_checks']},{sources[s]['url'] for s in i['source_ids']})
 def test_all_previous_content_and_source_objects_preserved(self):
  old=json.loads(subprocess.check_output(['git','show',BASE+':localization/tw-edition/runtime.json'],cwd=ROOT));rt=validate_runtime();items={i['id']:i for i in rt['items']};sources={s['id']:s for s in rt['sources']};self.assertEqual([i['id'] for i in old['items']],[i['id'] for i in rt['items']])
  for i in old['items']:assert_preserved_or_rechecked(self,i,items[i['id']])
  for s in old['sources']:self.assertEqual(s,sources[s['id']])
 def test_immediate_safety_and_rights_boundaries(self):
  b={i['id']:i['body'] for i in validate_runtime()['items']}
  for k in IDS:self.assertLess(b[k].index('110'),b[k].index('事件頻率'))
  terms={'TW-17-001':['撤回一部視為全部','先以書面向他方','七日內一定','正當理由','第1113-9條'],'TW-17-003':['雙人複核','沒有因此取得法定代理權','不法侵害','1113-9'],'TW-17-005':['不是當然的信託','一至兩個月','必要時','不能據此保證','機構住宿式'],'TW-17-006':['按月繳息','本金到期或終止','2023-03-27','不是銀行必須核准','不假定全臺一律']}
  for k,ts in terms.items():
   for t in ts:self.assertIn(t,b[k])
 def test_single_bank_volume_has_no_probability_denominator(self):
  x=load('localization/guardianship-property-retirement-20261021.json');self.assertEqual(set(x['frequency_assessments']),IDS);s=x['statistics'][0];self.assertEqual(s['value'],2723);self.assertIsNone(s['denominator']);self.assertIn('非全臺',s['scope']);self.assertIn('2025',s['period']);self.assertIn('累積',s['method']);self.assertIn('不能',s['limitations'])
  for z in x['frequency_assessments'].values():self.assertIn('不能',z)
 def test_effective_dates_and_professional_limits(self):
  x=load('localization/guardianship-property-retirement-20261021.json');self.assertEqual(x['new_core_ids'],[]);self.assertEqual(x['professional_review'],'pending');self.assertFalse(publication_report()['publication_ready']);e=x['legal_evidence'][0];self.assertEqual((e['announced_at'],e['effective_at']),('2024-03-15','2024-03-15'));self.assertIsNone(x['legal_evidence'][1]['effective_at']);self.assertIsNone(x['legal_evidence'][2]['effective_at']);rv=load('localization/reviews/TW-17-005.json');self.assertTrue(any('渲染' in c['retrieval_method'] for c in rv['source_checks']));self.assertTrue(any('動態外殼' in c['retrieval_method'] for c in rv['source_checks']))
if __name__=='__main__':unittest.main()

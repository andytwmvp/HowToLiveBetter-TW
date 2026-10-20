"""肝炎、領藥與照護契約：真實歷史、分流及制度邊界回歸。"""
import hashlib,json,subprocess,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from review_contract import ROOT,validate_runtime,publication_report
from retroactive_audit import assert_preserved_or_rechecked,validate_recheck_history
BASE='16be556cec3ea78631bf2797fa30e47b5185c760';IDS={'TW-16-011','TW-16-005','TW-24-014','TW-17-011'}
def load(p):return json.loads((ROOT/p).read_text())
class HepatitisPrescriptionContractTests(unittest.TestCase):
 def test_history_body_review_and_sources(self):
  rt=validate_runtime();items={i['id']:i for i in rt['items']};sources={s['id']:s for s in rt['sources']};rows={r['id']:r for r in load('localization/retroactive-review-register-20261019.json')['substantive_rechecks']}
  for k in IDS:
   i=items[k];rv=load('localization/reviews/'+k+'.json');validate_recheck_history(ROOT,rows[k],i);self.assertEqual((ROOT/i['target_path']).read_text(),i['body']);self.assertEqual(rv['target_sha256'],hashlib.sha256(i['body'].encode()).hexdigest());self.assertEqual(rv['source_checks'],rows[k]['source_checks']);self.assertEqual({c['url'] for c in rv['source_checks']},{sources[s]['url'] for s in i['source_ids']})
 def test_all_previous_content_and_source_objects_preserved(self):
  old=json.loads(subprocess.check_output(['git','show',BASE+':localization/tw-edition/runtime.json'],cwd=ROOT));rt=validate_runtime();items={i['id']:i for i in rt['items']};sources={s['id']:s for s in rt['sources']};self.assertEqual([i['id'] for i in old['items']],[i['id'] for i in rt['items']])
  for i in old['items']:assert_preserved_or_rechecked(self,i,items[i['id']])
  for s in old['sources']:self.assertEqual(s,sources[s['id']])
 def test_emergency_and_key_service_boundaries(self):
  b={i['id']:i['body'] for i in validate_runtime()['items']}
  for k in IDS:self.assertLess(b[k].index('119'),b[k].index('事件頻率'))
  terms={'TW-16-011':['不等例行','不因肝指數正常','AFP不能單獨','不是管理照護費申報間隔'],'TW-16-005':['前10日內','出具切結','腹膜透析液','不因提早拿到就提早加吃'],'TW-24-014':['三者條件不同','限繼續相同方劑','通常限複診','有法定例外'],'TW-17-011':['不能要求拋棄審閱權','機構名義專戶','7個工作日內','不能把這個範圍套到護理之家']}
  for k,ts in terms.items():
   for t in ts:self.assertIn(t,b[k])
 def test_specific_population_and_effective_dates(self):
  b=load('localization/hepatitis-prescriptions-care-contract-20261020.json');s=b['statistics'][0];self.assertEqual(s['value'],1.88);self.assertEqual(s['period'],'2024年');self.assertIsNone(s['numerator']);self.assertIsNone(s['denominator']);self.assertIn('孕婦',s['scope']);self.assertIn('非2026成人',s['limitations']);d={x['topic']:x for x in b['legal_evidence']};self.assertEqual(d['通訊診察治療辦法']['effective_at'],'2024-07-01');self.assertEqual(d['住宿式長照定型化契約應記載及不得記載事項']['effective_at'],'2024-03-15');self.assertEqual(d['肝炎醫療給付改善方案第九版']['effective_at'],'2026-08-19')
 def test_unread_sources_and_professional_limits_not_upgraded(self):
  b=load('localization/hepatitis-prescriptions-care-contract-20261020.json');self.assertEqual(set(b['ai_rechecked_ids']),IDS);self.assertEqual(b['new_core_ids'],[]);self.assertEqual(b['professional_review'],'pending');self.assertFalse(publication_report()['publication_ready'])
  rv=load('localization/reviews/TW-16-011.json');old=[c for c in rv['source_checks'] if 'hpa.gov.tw' in c['url'] or 'pmc.ncbi' in c['url']];self.assertEqual(len(old),2);self.assertTrue(all(c['accessed_at']=='2026-10-17' for c in old));self.assertIn('草案',next(c['retrieval_method'] for c in load('localization/reviews/TW-17-011.json')['source_checks'] if 'moj.gov.tw/2204' in c['url']))
if __name__=='__main__':unittest.main()

"""急救、費用、認定與病歷之歷史及安全契約。"""
import hashlib,json,subprocess,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from review_contract import ROOT,validate_runtime,publication_report
from retroactive_audit import assert_preserved_or_rechecked,validate_recheck_history
BASE='5dfeccd62f6eb13816e0b28645bcb7488fc9d1a7';IDS={'TW-24-008','TW-24-015','TW-24-009','TW-24-005'}
def load(p):return json.loads((ROOT/p).read_text())
class MedicalRightsRecheckTests(unittest.TestCase):
 def test_history_body_review_and_sources(self):
  rt=validate_runtime();items={i['id']:i for i in rt['items']};sources={s['id']:s for s in rt['sources']};rows={r['id']:r for r in load('localization/retroactive-review-register-20261019.json')['substantive_rechecks']}
  for k in IDS:
   i=items[k];rv=load('localization/reviews/'+k+'.json');validate_recheck_history(ROOT,rows[k],i);self.assertEqual((ROOT/i['target_path']).read_text(),i['body']);self.assertEqual(rv['target_sha256'],hashlib.sha256(i['body'].encode()).hexdigest());self.assertEqual(rv['source_checks'],rows[k]['source_checks']);self.assertEqual({c['url'] for c in rv['source_checks']},{sources[s]['url'] for s in i['source_ids']})
 def test_all_previous_content_and_source_objects_preserved(self):
  old=json.loads(subprocess.check_output(['git','show',BASE+':localization/tw-edition/runtime.json'],cwd=ROOT));rt=validate_runtime();items={i['id']:i for i in rt['items']};sources={s['id']:s for s in rt['sources']};self.assertEqual([i['id'] for i in old['items']],[i['id'] for i in rt['items']])
  for i in old['items']:assert_preserved_or_rechecked(self,i,items[i['id']])
  for s in old['sources']:self.assertEqual(s,sources[s['id']])
 def test_emergency_and_consent_boundaries(self):
  b={i['id']:i['body'] for i in validate_runtime()['items']}
  for k in IDS:self.assertLess(b[k].index('119'),b[k].index('事件頻率'))
  terms={'TW-24-008':['不等於所有費用全面免費','貸款不是免還補助','先急救再轉診','申請期限'],'TW-24-015':['前二日','說明書一式兩份','另說明費用','同意書兩份','不簽空白','不把此兩日規定機械套用'],'TW-24-009':['症狀固定','強制納保單位','雇主不協助可自行送件','不擴張為任何未加保者','同次同醫師併行治療'],'TW-24-005':['報告文字與影像檔不是同一項','家屬身分不自動等於','不等全套齊全才就醫','不代表沒做過']}
  for k,ts in terms.items():
   for t in ts:self.assertIn(t,b[k])
 def test_procedures_are_not_population_statistics(self):
  x=load('localization/emergency-records-benefits-consent-20261021.json');self.assertEqual(x['statistics'],[]);self.assertEqual(set(x['frequency_assessments']),IDS)
  for z in x['frequency_assessments'].values():self.assertIn('不能',z)
  e=x['legal_evidence'][0];self.assertEqual((e['announced_at'],e['effective_at']),('2020-02-24','2020-02-24'));self.assertIsNone(x['legal_evidence'][1]['effective_at']);self.assertIn('非本批每條首次施行日',x['legal_evidence'][1]['scope'])
 def test_limits_and_source_access_scope(self):
  x=load('localization/emergency-records-benefits-consent-20261021.json');self.assertEqual(set(x['ai_rechecked_ids']),IDS);self.assertEqual(x['new_core_ids'],[]);self.assertEqual(x['professional_review'],'pending');self.assertFalse(publication_report()['publication_ready']);rv=load('localization/reviews/TW-24-015.json');c=next(c for c in rv['source_checks'] if 'cp-18585' in c['url']);self.assertIn('僅此類別範例',c['retrieval_method']);self.assertIn('403',c['retrieval_method']);self.assertTrue(any('PDF' in c['retrieval_method'] for c in rv['source_checks']))
if __name__=='__main__':unittest.main()

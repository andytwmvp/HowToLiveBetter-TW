"""癌後運動、眼科、飲食及照顧假之歷史與安全邊界。"""
import hashlib,json,subprocess,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from review_contract import ROOT,validate_runtime,publication_report
from retroactive_audit import assert_preserved_or_rechecked,validate_recheck_history
BASE='7f71936381f0d7f877d760a52cf6a8966b5c1d94';IDS={'TW-16-014','TW-17-009','TW-16-010','TW-17-012'}
def load(p):return json.loads((ROOT/p).read_text())
class CancerEyeGoutCareLeaveTests(unittest.TestCase):
 def test_history_body_review_and_sources(self):
  rt=validate_runtime();items={i['id']:i for i in rt['items']};sources={s['id']:s for s in rt['sources']};rows={r['id']:r for r in load('localization/retroactive-review-register-20261019.json')['substantive_rechecks']}
  for k in IDS:
   i=items[k];rv=load('localization/reviews/'+k+'.json');validate_recheck_history(ROOT,rows[k],i);self.assertEqual((ROOT/i['target_path']).read_text(),i['body']);self.assertEqual(rv['target_sha256'],hashlib.sha256(i['body'].encode()).hexdigest());self.assertEqual(rv['source_checks'],rows[k]['source_checks']);self.assertEqual({c['url'] for c in rv['source_checks']},{sources[s]['url'] for s in i['source_ids']})
 def test_all_previous_content_and_source_objects_preserved(self):
  old=json.loads(subprocess.check_output(['git','show',BASE+':localization/tw-edition/runtime.json'],cwd=ROOT));rt=validate_runtime();items={i['id']:i for i in rt['items']};sources={s['id']:s for s in rt['sources']};self.assertEqual([i['id'] for i in old['items']],[i['id'] for i in rt['items']])
  for i in old['items']:assert_preserved_or_rechecked(self,i,items[i['id']])
  for s in old['sources']:self.assertEqual(s,sources[s['id']])
 def test_urgent_actions_and_individual_exceptions(self):
  b={i['id']:i['body'] for i in validate_runtime()['items']}
  for k in IDS:self.assertLess(b[k].index('119'),b[k].index('事件頻率'))
  terms={'TW-16-014':['60至180日','不要自行套用網路年齡心率表','不是單純「復發率」','反推事件數'],'TW-17-009':['立即至急診','處置前二日','病人留一份','不規定人人固定幾週'],'TW-16-010':['證據確定性很低','不能取代必要降尿酸藥','避免斷食','不永久禁掉所有魚'],'TW-17-012':['不是任何輪班10小時','選定後不得變更','考核仍依勞雇約定','七加十四日']}
  for k,ts in terms.items():
   for t in ts:self.assertIn(t,b[k])
 def test_trial_and_law_evidence_units(self):
  x=load('localization/cancer-eye-gout-care-leave-20261020.json');s=x['statistics'][0];self.assertEqual(s['randomized_total'],sum(s['randomized_groups']));self.assertEqual(s['randomized_groups'],[445,444]);self.assertEqual(s['value'],[80.3,73.9]);self.assertAlmostEqual(s['value'][0]-s['value'][1],s['difference_percentage_points']);self.assertIsNone(s['numerator']);self.assertIsNone(s['denominator']);self.assertIn('複合',s['definition']);self.assertIn('非單純復發',s['limitations']);self.assertEqual([(z['announced_at'],z['effective_at']) for z in x['legal_evidence'][:2]],[('2025-12-01','2026-01-01'),('2025-12-09','2026-01-01')])
 def test_professional_and_retrieval_limits_stay_explicit(self):
  x=load('localization/cancer-eye-gout-care-leave-20261020.json');self.assertEqual(set(x['ai_rechecked_ids']),IDS);self.assertEqual(x['new_core_ids'],[]);self.assertEqual(x['professional_review'],'pending');self.assertFalse(publication_report()['publication_ready']);rv=load('localization/reviews/TW-16-010.json');old=[c for c in rv['source_checks'] if 'id=19717' in c['url']];self.assertTrue(old);self.assertEqual(old[0]['accessed_at'],'2026-10-17');self.assertIn('未讀',load('localization/reviews/TW-16-014.json')['source_checks'][0]['retrieval_method'])
if __name__=='__main__':unittest.main()

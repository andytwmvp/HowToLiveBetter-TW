"""居家量測補充品結石痛風：真實歷史與急症及統計邊界。"""
import hashlib,json,subprocess,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from review_contract import ROOT,validate_runtime,publication_report
from retroactive_audit import assert_preserved_or_rechecked,validate_recheck_history
BASE='752ada9447f99fb06f6c9343c43625e2f7ae844b';IDS={'TW-16-003','TW-16-004','TW-16-008','TW-16-009'}
def load(p):return json.loads((ROOT/p).read_text())
class BPSupplementsStonesGoutTests(unittest.TestCase):
 def test_history_body_review_and_sources(self):
  rt=validate_runtime();items={i['id']:i for i in rt['items']};sources={s['id']:s for s in rt['sources']};rows={r['id']:r for r in load('localization/retroactive-review-register-20261019.json')['substantive_rechecks']}
  for k in IDS:
   i=items[k];rv=load('localization/reviews/'+k+'.json');validate_recheck_history(ROOT,rows[k],i);self.assertEqual((ROOT/i['target_path']).read_text(),i['body']);self.assertEqual(rv['target_sha256'],hashlib.sha256(i['body'].encode()).hexdigest());self.assertEqual(rv['source_checks'],rows[k]['source_checks']);self.assertEqual({c['url'] for c in rv['source_checks']},{sources[s]['url'] for s in i['source_ids']})
 def test_all_previous_content_and_source_objects_preserved(self):
  old=json.loads(subprocess.check_output(['git','show',BASE+':localization/tw-edition/runtime.json'],cwd=ROOT));rt=validate_runtime();items={i['id']:i for i in rt['items']};sources={s['id']:s for s in rt['sources']};self.assertEqual([i['id'] for i in old['items']],[i['id'] for i in rt['items']])
  for i in old['items']:assert_preserved_or_rechecked(self,i,items[i['id']])
  for s in old['sources']:self.assertEqual(s,sources[s['id']])
 def test_emergency_actions_and_specific_exceptions(self):
  b={i['id']:i['body'] for i in validate_runtime()['items']}
  for k in IDS:self.assertLess(b[k].index('119'),b[k].index('事件頻率'))
  terms={'TW-16-009':['立即停用allopurinol','不要再服可疑藥來試','條件性建議','6 mg/dL'],'TW-16-004':['非必要補充品','隔兩小時吃','濃縮紅麴','一般紅麴加工食品'],'TW-16-008':['感染合併阻塞或無尿','不要硬灌水','飲水量不等於尿量','限水醫囑'],'TW-16-003':['不為補齊722','坐休5分鐘','沒量滿7天','不反推人數']}
  for k,ts in terms.items():
   for t in ts:self.assertIn(t,b[k])
 def test_statistics_retain_actual_populations_and_denominators(self):
  x=load('localization/bp-supplements-stones-gout-20261020.json');b,g=x['statistics'];self.assertEqual(b['value'],30.4);self.assertIn('2020至2024',b['period']);self.assertIsNone(b['numerator']);self.assertIsNone(b['denominator']);self.assertIn('非2026新發',b['limitations']);self.assertEqual((g['numerator'],g['denominator']),(571,2910));self.assertAlmostEqual(g['numerator']/g['denominator']*100,g['value'],places=1);self.assertIn('不是SCAR病例數',g['definition']);self.assertIn('藥物過敏發生率',g['limitations'])
 def test_professional_and_retrieval_limits_stay_explicit(self):
  x=load('localization/bp-supplements-stones-gout-20261020.json');self.assertEqual(set(x['ai_rechecked_ids']),IDS);self.assertEqual(x['new_core_ids'],[]);self.assertEqual(x['professional_review'],'pending');self.assertFalse(publication_report()['publication_ready'])
  for k in ['TW-16-003','TW-16-008']:
   rv=load('localization/reviews/'+k+'.json');old=[c for c in rv['source_checks'] if c['url'].endswith('pid=14499') or 'auajournals' in c['url'] or '/cKD-' in c['url']];self.assertTrue(old);self.assertTrue(all(c['accessed_at']=='2026-10-17' for c in old))
if __name__=='__main__':unittest.main()

"""早期無審閱檔導航的歷史證據與急症／防災閱讀契約。"""
import copy,hashlib,json,subprocess,sys,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import retroactive_audit as audit
from review_contract import ROOT,validate_runtime,publication_report
BASE='b5c299375ba3b2a24ec3da72421b826bbabfb11e'
IDS={'TW-NAV-001','TW-NAV-002','TW-NAV-010'}
def load(p):return json.loads((ROOT/p).read_text())
class SafetyNavigationTests(unittest.TestCase):
 def test_navigation_history_and_source_preservation(self):
  rt=validate_runtime();items={i['id']:i for i in rt['items']};old=json.loads(subprocess.check_output(['git','show',BASE+':localization/tw-edition/runtime.json'],cwd=ROOT));sources={s['id']:s for s in rt['sources']}
  for row in old['sources']:self.assertEqual(row,sources[row['id']])
  for row in old['items']:audit.assert_preserved_or_rechecked(self,row,items[row['id']])
  self.assertFalse(publication_report()['publication_ready'])
 def test_inline_navigation_recheck_has_real_prior_provenance(self):
  rows={r['id']:r for r in load('localization/retroactive-review-register-20261019.json')['substantive_rechecks']};items={i['id']:i for i in validate_runtime()['items']}
  for key in IDS:
   record=rows[key];audit.validate_recheck_history(ROOT,record,items[key]);review=load('localization/reviews/'+key+'.json');self.assertEqual(review['target_sha256'],hashlib.sha256(items[key]['body'].encode()).hexdigest())
   if key!='TW-NAV-010':self.assertEqual(record['prior_review_kind'],'runtime_item');self.assertEqual(review['target_kind'],'runtime_body')
 def test_corrupt_current_navigation_hash_is_rejected(self):
  key='TW-NAV-001';row=next(r for r in load('localization/retroactive-review-register-20261019.json')['substantive_rechecks'] if r['id']==key);item=next(i for i in validate_runtime()['items'] if i['id']==key);original=audit.load
  def changed(root,path):
   d=original(root,path)
   if path=='localization/reviews/'+key+'.json':d['target_sha256']='0'*64
   return d
  with patch.object(audit,'load',changed),self.assertRaises(ValueError):audit.validate_recheck_history(ROOT,row,item)
  corrupt=copy.deepcopy(row);corrupt['prior_review_sha256']='0'*64
  with self.assertRaises(ValueError):audit.validate_recheck_history(ROOT,corrupt,item)
 def test_emergency_first_and_denominators(self):
  items={i['id']:i for i in validate_runtime()['items']}
  for key in ('TW-NAV-001','TW-NAV-002'):
   b=items[key]['body'];self.assertLess(b.index('119'),b.index('2025年'));self.assertIn('死亡',b);self.assertIn('不是',b);self.assertIn('不自行開車',b)
  self.assertIn('最後正常',items['TW-NAV-001']['body']);self.assertIn('15分鐘',items['TW-NAV-002']['body'])
  b=items['TW-NAV-010']['body'];self.assertIn('不要等待警報',b);self.assertIn('發生率',b);self.assertIn('先撤離',b);self.assertNotIn('剩餘40條',b)
 def test_navigation_not_added_to_core_or_professional_completion(self):
  self.assertTrue(IDS.isdisjoint({e['id'] for e in load('localization/manifest.json')['entries']}))
  b=load('localization/safety-navigation-20261020.json');self.assertEqual(set(b['ai_rechecked_ids']),IDS);self.assertEqual(b['new_core_ids'],[]);self.assertEqual(b['professional_review'],'pending')
if __name__=='__main__':unittest.main()

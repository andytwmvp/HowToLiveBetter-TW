"""心理求援與職安再審：立即危險先行、統計口徑及歷史保全。"""
import hashlib,json,subprocess,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from review_contract import ROOT,validate_runtime,publication_report
from retroactive_audit import assert_preserved_or_rechecked,validate_recheck_history
BASE='920ee4bd88e28e3b53f28a29413d45dc530f9a41';IDS={'TW-NAV-003','TW-NAV-011'}
def load(p):return json.loads((ROOT/p).read_text())
class MentalOccupationalTests(unittest.TestCase):
 def test_real_historical_provenance_and_body_contracts(self):
  rt=validate_runtime();items={i['id']:i for i in rt['items']};records={x['id']:x for x in load('localization/retroactive-review-register-20261019.json')['substantive_rechecks']};sources={s['id']:s for s in rt['sources']}
  for key in IDS:
   row=records[key];i=items[key];rv=load('localization/reviews/'+key+'.json');validate_recheck_history(ROOT,row,i);self.assertEqual(rv['target_sha256'],hashlib.sha256(i['body'].encode()).hexdigest());self.assertEqual({c['url'] for c in rv['source_checks']},{sources[k]['url'] for k in i['source_ids']})
   if i.get('target_path'):self.assertEqual((ROOT/i['target_path']).read_text(),i['body'])
  self.assertEqual(records['TW-NAV-003']['prior_review_kind'],'runtime_item')
 def test_all_old_reading_items_sources_and_scope_preserved(self):
  old=json.loads(subprocess.check_output(['git','show',BASE+':localization/tw-edition/runtime.json'],cwd=ROOT));rt=validate_runtime();items={i['id']:i for i in rt['items']};sources={s['id']:s for s in rt['sources']}
  self.assertEqual(set(items),{i['id'] for i in old['items']})
  for i in old['items']:assert_preserved_or_rechecked(self,i,items[i['id']])
  for s in old['sources']:self.assertEqual(s,sources[s['id']])
  self.assertTrue(IDS.isdisjoint({x['id'] for x in load('localization/manifest.json')['entries']}));self.assertFalse(publication_report()['publication_ready'])
 def test_urgent_help_precedes_statistics_and_is_not_counselling(self):
  b={i['id']:i['body'] for i in validate_runtime()['items']};p=b['TW-NAV-003'];self.assertLess(p.index('119'),p.index('1925'));self.assertLess(p.index('119'),p.index('2025年'))
  for t in ['不批判','不是','不保證','持續','3,951','16.9']:self.assertIn(t,p)
  q=b['TW-NAV-011']
  for t in ['不必先等主管批准','8小時','最高負責人','地方主管機關','不等待','109人','49人','2026-07-01','2027-01-01']:self.assertIn(t,q)
 def test_statistics_have_distinct_periods_and_denominators(self):
  b=load('localization/mental-occupational-20261020.json');stats={x['id']:x for x in b['statistics']};self.assertEqual(stats['self_harm_deaths_2025']['value'],3951);self.assertEqual(stats['self_harm_deaths_2025']['crude_rate_per_100000'],16.9);self.assertEqual(stats['osh_deaths_2026_h1']['value'],109);self.assertEqual(stats['osh_falls_2026_h1']['value'],49)
  self.assertEqual(stats['osh_deaths_2026_h1']['period'],'2026-01-01至2026-06-30');self.assertIsNone(stats['osh_deaths_2026_h1']['denominator']);self.assertTrue(all(x['definition'] and x['limitations'] and x['accessed_at']=='2026-10-20' for x in stats.values()))
 def test_no_professional_or_publication_completion_claim(self):
  b=load('localization/mental-occupational-20261020.json');self.assertEqual(set(b['ai_rechecked_ids']),IDS);self.assertEqual(b['new_core_ids'],[]);self.assertEqual(b['professional_review'],'pending');self.assertTrue(b['limits']);rows=load('localization/retroactive-review-register-20261019.json')['substantive_rechecks'];self.assertTrue(all(r['status']=='ai_source_rechecked_professional_pending' for r in rows))
if __name__=='__main__':unittest.main()

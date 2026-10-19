"""第13章第四批：嚴重過敏、神經、代謝與外傷來源及歷史完整性回歸。"""
import hashlib,json,subprocess,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from retroactive_audit import assert_preserved_or_rechecked
from review_contract import ROOT,validate_runtime,validate_entry,publication_report
from body_renderer import body_blocks
BASE='bc75deaf3a7ff804ee7f8fcc5bf9bbd8565cc912'
IDS={'TW-13-015','TW-13-016','TW-13-017','TW-13-018','TW-13-026','TW-13-029','TW-13-040','TW-13-041'}
def load(path):return json.loads((ROOT/path).read_text(encoding='utf-8'))
class Chapter13EmergencyCareTests(unittest.TestCase):
 def test_eight_taiwan_texts_reviews_and_sources(self):
  manifest={e['id']:e for e in load('localization/manifest.json')['entries']}
  rt=validate_runtime();items={e['id']:e for e in rt['items']};sources={s['id']:s for s in rt['sources']}
  for key in IDS:
   with self.subTest(key=key):
    e=manifest[key];self.assertEqual(e['status'],'verified');self.assertTrue(validate_entry(e))
    raw=(ROOT/e['target_path']).read_bytes();r=load('localization/reviews/'+key+'.json')
    self.assertGreater(len(raw),1800);self.assertEqual(hashlib.sha256(raw).hexdigest(),r['target_sha256'])
    self.assertEqual(raw.decode(),items[key]['body'])
    self.assertEqual(sum(block['tag']=='h3' for block in body_blocks(items[key])),5)
    self.assertEqual({check['url'] for check in r['source_checks']},{sources[s]['url'] for s in items[key]['source_ids']})
 def test_safety_specific_risks(self):
  body={e['id']:e['body'].split('## 官方來源及改寫說明')[0] for e in validate_runtime()['items']}
  for key in IDS:
   self.assertIn('119',body[key]);self.assertNotIn('打120',body[key]);self.assertNotIn('撥120',body[key])
  self.assertIn('自動注射器',body['TW-13-015']);self.assertIn('五分鐘',body['TW-13-016'])
  self.assertIn('禁止強行餵',body['TW-13-017']);self.assertIn('高壓',body['TW-13-018'])
  self.assertIn('仍能用力咳嗽',body['TW-13-026']);self.assertIn('五要五不',body['TW-13-029'])
  self.assertIn('不要旋轉',body['TW-13-040']);self.assertIn('不要牽拉',body['TW-13-041'])
 def test_previous_208_items_and_sources_untouched(self):
  old=json.loads(subprocess.check_output(['git','show',BASE+':localization/tw-edition/runtime.json'],cwd=ROOT,text=True))
  now=validate_runtime();items={e['id']:e for e in now['items']};sources={s['id']:s for s in now['sources']}
  self.assertEqual(len(old['items']),208)
  for e in old['items']:assert_preserved_or_rechecked(self,e,items[e['id']])
  for e in old['sources']:self.assertEqual(sources[e['id']],e)
 def test_new_registry_and_unfinished_core(self):
  report=publication_report();cov=load('localization/tw-edition/coverage.json');rt=validate_runtime()
  self.assertGreaterEqual(report['publication_completed_entries'],206);self.assertFalse(report['publication_ready'])
  self.assertEqual(cov['publication_completed_entries'],report['publication_completed_entries']);self.assertGreaterEqual(cov['registry_sources'],len(rt['sources']))
  self.assertEqual(cov['unique_draft_entries']+cov['entries_without_any_draft'],765);self.assertGreaterEqual(cov['unique_draft_entries'],474)
  self.assertEqual(len(rt['items']),report['publication_completed_entries']+sum(i['id'].startswith('TW-NAV-') for i in rt['items']))
  prior=json.loads(subprocess.check_output(['git','show',BASE+':localization/tw-edition/runtime.json'],cwd=ROOT,text=True))
  self.assertTrue({e['id'] for e in prior['items'] if e['id'].startswith('TW-NAV-')}.issubset({e['id'] for e in rt['items'] if e['id'].startswith('TW-NAV-')}))
  self.assertEqual(len(load('localization/tw-edition/sources/ch13-emergency-care-20261018.json')['sources']),14)
if __name__=='__main__':unittest.main()

"""第13章第二批急救規則及完整來源保全回歸。"""
import hashlib,json,subprocess,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from retroactive_audit import assert_preserved_or_rechecked
from review_contract import ROOT,validate_runtime,validate_entry,publication_report
from body_renderer import body_blocks
BASE='538e88ead8dab2d7c6720fe101bd6af17d898d56'
IDS={'TW-13-002','TW-13-012','TW-13-014','TW-13-024'}
def read(path):return json.loads((ROOT/path).read_text(encoding='utf8'))
class Chapter13SafetyTests(unittest.TestCase):
 def test_four_verified_documents_and_evidence(self):
  ms={e['id']:e for e in read('localization/manifest.json')['entries']}
  rt=validate_runtime();items={e['id']:e for e in rt['items']};sources={e['id']:e for e in rt['sources']}
  self.assertTrue(IDS.issubset(items))
  for key in IDS:
   with self.subTest(key=key):
    m=ms[key];self.assertTrue(validate_entry(m));self.assertEqual(m['status'],'verified')
    data=(ROOT/m['target_path']).read_bytes();review=read(f'localization/reviews/{key}.json')
    self.assertGreater(len(data),1500)
    self.assertEqual(hashlib.sha256(data).hexdigest(),review['target_sha256'])
    self.assertEqual(items[key]['body'],data.decode())
    self.assertEqual(sum(x['tag']=='h3' for x in body_blocks(items[key])),5)
    self.assertEqual({x['url'] for x in review['source_checks']},{sources[k]['url'] for k in items[key]['source_ids']})
 def test_taiwan_triage_and_false_assumptions(self):
  b={e['id']:e['body'] for e in validate_runtime()['items']}
  for key in IDS:self.assertIn('119',b[key])
  self.assertIn('不要急著',b['TW-13-002'])
  self.assertIn('止血帶',b['TW-13-012'])
  self.assertIn('頸部',b['TW-13-012'])
  self.assertIn('15至30分鐘',b['TW-13-014'])
  self.assertIn('失溫',b['TW-13-014'])
  self.assertIn('不要進入或硬闖',b['TW-13-024'])
  self.assertIn('關門',b['TW-13-024'])
 def test_previous_195_items_unchanged(self):
  old=json.loads(subprocess.check_output(['git','show',BASE+':localization/tw-edition/runtime.json'],cwd=ROOT,text=True))
  now=validate_runtime();ii={e['id']:e for e in now['items']};ss={s['id']:s for s in now['sources']}
  for e in old['items']:assert_preserved_or_rechecked(self,e,ii[e['id']])
  for e in old['sources']:self.assertEqual(e,ss[e['id']])
  batch=read('localization/tw-edition/sources/ch13-safety-20261017.json')['sources']
  self.assertEqual(len(batch),8)
  for line in batch:self.assertEqual(ss[line[0]]['url'],line[2])
 def test_incremental_counts_and_unfinished_scope(self):
  r=publication_report();c=read('localization/tw-edition/coverage.json')
  self.assertGreaterEqual(r['publication_completed_entries'],190)
  self.assertEqual(r['publication_total_entries'],765)
  self.assertFalse(r['publication_ready'])
  self.assertGreaterEqual(c['registry_sources'],345)
  self.assertGreaterEqual(c['unique_draft_entries'],458)
  self.assertLessEqual(c['entries_without_any_draft'],307)
  self.assertEqual(read('localization/ch13-safety-batch-20261017.json')['chapter_cumulative'],8)
if __name__=='__main__':unittest.main()

"""第13章第三批八篇臺灣急救，逐條SHA、來源與歷史完整性回歸。"""
import hashlib,json,subprocess,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from retroactive_audit import assert_preserved_or_rechecked
from review_contract import ROOT,validate_runtime,validate_entry,publication_report
from body_renderer import body_blocks
BASE='4a7b56ba4dd9d82b81ef1fb07957d24f3050603b'
IDS={'TW-13-013','TW-13-019','TW-13-020','TW-13-021','TW-13-022','TW-13-023','TW-13-025','TW-13-028'}
def load(p):return json.loads((ROOT/p).read_text(encoding='utf-8'))
class Chapter13ThirdBatchTests(unittest.TestCase):
 def test_full_texts_reviews_and_source_records(self):
  manifest={x['id']:x for x in load('localization/manifest.json')['entries']}
  data=validate_runtime();items={x['id']:x for x in data['items']};sources={s['id']:s for s in data['sources']}
  self.assertTrue(IDS.issubset(items))
  for key in IDS:
   with self.subTest(id=key):
    entry=manifest[key];self.assertEqual(entry['status'],'verified');self.assertTrue(validate_entry(entry))
    self.assertEqual(entry['target_path'],f'locales/zh-TW/book/ch13/{key}.md')
    raw=(ROOT/entry['target_path']).read_bytes();review=load('localization/reviews/'+key+'.json')
    self.assertGreater(len(raw),1600)
    self.assertEqual(hashlib.sha256(raw).hexdigest(),review['target_sha256'])
    self.assertEqual(raw.decode('utf-8'),items[key]['body'])
    self.assertEqual(sum(b['tag']=='h3' for b in body_blocks(items[key])),5)
    self.assertIn('AI',review['reviewer'])
    self.assertEqual({row['url'] for row in review['source_checks']},{sources[s]['url'] for s in items[key]['source_ids']})
 def test_taiwan_specific_immediate_safety(self):
  b={x['id']:x['body'].split('## 官方來源及改寫說明')[0] for x in validate_runtime()['items']}
  self.assertIn('疫苗',b['TW-13-013']);self.assertIn('十五分鐘',b['TW-13-013'])
  self.assertIn('119',b['TW-13-019']);self.assertIn('室外',b['TW-13-019'])
  self.assertIn('02-2871-7121',b['TW-13-020']);self.assertIn('禁止自行催吐',b['TW-13-020'])
  self.assertIn('生石灰',b['TW-13-021']);self.assertIn('遇水反應',b['TW-13-021'])
  self.assertIn('中暑也可能大量流汗',b['TW-13-022']);self.assertIn('不要餵水或灌水',b['TW-13-022'])
  self.assertIn('限水',b['TW-13-023']);self.assertIn('醫療劑量',b['TW-13-023'])
  self.assertIn('叫、叫、伸、拋、划',b['TW-13-025']);self.assertIn('118',b['TW-13-025'])
  self.assertIn('不要因為會游泳就直接跳下水',b['TW-13-025']);self.assertIn('輕柔地',b['TW-13-028'])
  for key in IDS:self.assertNotIn('撥120',b[key]);self.assertNotIn('打120',b[key])
 def test_old_reading_rows_are_unchanged(self):
  old=json.loads(subprocess.check_output(['git','show',BASE+':localization/tw-edition/runtime.json'],cwd=ROOT,text=True))
  after=validate_runtime();rows={e['id']:e for e in after['items']};sources={s['id']:s for s in after['sources']}
  self.assertEqual(len(old['items']),200)
  for e in old['items']:assert_preserved_or_rechecked(self,e,rows[e['id']])
  for s in old['sources']:self.assertEqual(sources[s['id']],s)
  for p in ('ch13-poison-rabies-20261017.json','ch13-heat-water-cold-20261017.json'):
   for row in load('localization/tw-edition/sources/'+p)['sources']:
    self.assertEqual(sources[row[0]]['url'],row[2])
 def test_book_progress_and_not_fully_published(self):
  report=publication_report();cov=load('localization/tw-edition/coverage.json')
  self.assertEqual(report['publication_total_entries'],765)
  self.assertGreaterEqual(report['publication_completed_entries'],198)
  self.assertEqual(report['publication_completed_entries'],cov['publication_completed_entries'])
  self.assertFalse(report['publication_ready'])
  self.assertGreaterEqual(cov['registry_sources'],368)
  self.assertGreaterEqual(cov['unique_draft_entries'],466)
  self.assertLessEqual(cov['entries_without_any_draft'],299)
  batch=load('localization/ch13-poison-heat-water-20261017.json')
  self.assertEqual(batch['chapter_total'],48);self.assertEqual(batch['chapter_cumulative'],16)
if __name__=='__main__':unittest.main()

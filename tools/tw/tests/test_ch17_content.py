"""第17章意定監護、長照3.0、住院契約與家庭照顧假之臺灣版本回歸。"""
import hashlib,json,subprocess,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from review_contract import ROOT, validate_runtime,validate_entry,publication_report
from body_renderer import body_blocks
BASE='72ea775426cdcbc4b716ae506152607b56fc5ca7'
IDS={f'TW-17-{i:03d}' for i in range(1,14)}
def get(path):return json.loads((ROOT/path).read_text(encoding='utf8'))
class Chapter17Tests(unittest.TestCase):
 def test_thirteen_markdowns_and_reviews(self):
  manifest={e['id']:e for e in get('localization/manifest.json')['entries']}
  runtime={e['id']:e for e in validate_runtime()['items']}
  sources={s['id']:s for s in validate_runtime()['sources']}
  self.assertTrue(IDS.issubset(runtime))
  for key in IDS:
   with self.subTest(id=key):
    item=manifest[key]
    self.assertEqual(item['status'],'verified')
    self.assertTrue(validate_entry(item))
    self.assertTrue(item['target_path'].startswith('locales/zh-TW/book/ch17/'))
    raw=(ROOT/item['target_path']).read_bytes()
    review=get(f'localization/reviews/{key}.json')
    self.assertGreater(len(raw),1400)
    self.assertEqual(runtime[key]['body'],raw.decode('utf8'))
    self.assertEqual(review['target_sha256'],hashlib.sha256(raw).hexdigest())
    self.assertIn('AI',review['reviewer'])
    self.assertEqual(sum(x['tag']=='h3' for x in body_blocks(runtime[key])),5)
    self.assertTrue(set(runtime[key]['source_ids']).issubset(sources))
    self.assertEqual({s['url'] for s in review['source_checks']},{sources[s]['url'] for s in runtime[key]['source_ids']})
 def test_taiwan_law_and_service_clarifications(self):
  items={x['id']:x['body'] for x in validate_runtime()['items']}
  snippets={'001':['公證','監護宣告'],'002':['牴觸部分','特留分'],'003':['本人','雙人'],'004':['165','銀行'],'005':['服務','投資'],'006':['銀行','逆向抵押'],'007':['1966','長照3.0'],'008':['壓力性損傷','翻身'],'009':['白內障','自付差額'],'010':['牽繩','動物保護法'],'011':['保證金','兩個月'],'012':['小時','七日'],'013':['失智','就醫']}
  for suffix,needles in snippets.items():
   content=items['TW-17-'+suffix]
   for needle in needles:self.assertIn(needle,content,'TW-17-'+suffix)
  self.assertNotIn('96110', ''.join(items[key] for key in IDS))
  self.assertNotIn('職工七成',items['TW-17-007'])
 def test_sources_and_prior_items_preserved(self):
  base=json.loads(subprocess.check_output(['git','show',BASE+':localization/tw-edition/runtime.json'],cwd=ROOT,text=True))
  after=validate_runtime()
  self.assertEqual(len(base['items']),178)
  current_items={x['id']:x for x in after['items']}
  current_sources={x['id']:x for x in after['sources']}
  for item in base['items']:self.assertEqual(current_items[item['id']],item)
  for source in base['sources']:self.assertEqual(current_sources[source['id']],source)
  self.assertTrue(IDS.issubset(current_items))
  self.assertGreaterEqual(len(after['items']),191)
  sources=get('localization/tw-edition/sources/ch17-elder-20261017.json')['sources']
  self.assertEqual(len(sources),17)
  self.assertEqual(len({s[0] for s in sources}),17)
 def test_progress_and_publication_not_finished(self):
  report=publication_report()
  coverage=get('localization/tw-edition/coverage.json')
  self.assertGreaterEqual(report['publication_completed_entries'],182)
  self.assertGreaterEqual(coverage['publication_completed_entries'],182)
  self.assertFalse(report['publication_ready'])
  self.assertGreaterEqual(coverage['unique_draft_entries'],450)
  self.assertLessEqual(coverage['entries_without_any_draft'],315)
  self.assertGreaterEqual(coverage['registry_sources'],329)
  self.assertLessEqual(coverage['unresolved_reference_occurrences'],306)
if __name__=='__main__':unittest.main()

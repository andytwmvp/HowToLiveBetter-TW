"""第16章臺灣慢性病與跨國臨床證據區分、既有資料保全回歸。"""
import hashlib, json, subprocess, sys, unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from retroactive_audit import assert_preserved_or_rechecked
from review_contract import ROOT, validate_runtime, validate_entry, publication_report
from body_renderer import body_blocks
BASE='e13a1b7ccef36c8b1fe30ccef25e987e5f8e9f60'
IDS={f'TW-16-{i:03d}' for i in range(1,15)}
def read(path): return json.loads((ROOT/path).read_text(encoding='utf8'))

class Chapter16Tests(unittest.TestCase):
 def test_fourteen_real_markdown_entries_and_reviews(self):
  manifest={e['id']:e for e in read('localization/manifest.json')['entries']}
  runtime={e['id']:e for e in validate_runtime()['items']}
  self.assertTrue(IDS.issubset(runtime))
  for key in IDS:
   with self.subTest(id=key):
    entry=manifest[key];self.assertEqual(entry['status'],'verified');self.assertTrue(validate_entry(entry))
    self.assertTrue(entry['target_path'].startswith('locales/zh-TW/book/ch16/'))
    raw=(ROOT/entry['target_path']).read_bytes();review=read(f'localization/reviews/{key}.json')
    self.assertGreater(len(raw),1400)
    self.assertEqual(raw.decode(),runtime[key]['body'])
    self.assertEqual(hashlib.sha256(raw).hexdigest(),review['target_sha256'])
    self.assertIn('AI',review['reviewer'])
    self.assertEqual(sum(b['tag']=='h3' for b in body_blocks(runtime[key])),5)
    self.assertEqual({s['url'] for s in review['source_checks']},{s['url'] for s in validate_runtime()['sources'] if s['id'] in runtime[key]['source_ids']})
 def test_taiwan_and_medical_distinctions(self):
  items={e['id']:e['body'] for e in validate_runtime()['items']}
  self.assertIn('自行停藥',items['TW-16-001'])
  self.assertIn('異地備案',items['TW-16-002'])
  self.assertIn('722',items['TW-16-003'])
  self.assertIn('交互作用',items['TW-16-004'])
  self.assertIn('分次調劑',items['TW-16-005'])
  self.assertIn('家庭醫師',items['TW-16-006'])
  self.assertIn('眼底',items['TW-16-007'])
  self.assertIn('尿量',items['TW-16-008'])
  self.assertIn('6 mg/dL',items['TW-16-009'])
  self.assertIn('飲食',items['TW-16-010'])
  self.assertIn('HBsAg',items['TW-16-011'])
  self.assertIn('肺復健',items['TW-16-012'])
  self.assertIn('UACR',items['TW-16-013'])
  self.assertIn('CHALLENGE',items['TW-16-014'])
 def test_source_registry_and_review_scope(self):
  sources=read('localization/tw-edition/sources/ch16-chronic-20261017.json')['sources']
  self.assertEqual(len(sources),17)
  self.assertEqual(len({s[0] for s in sources}),17)
  self.assertTrue(all(s[2].startswith('https://') for s in sources))
  runtime={s['id']:s for s in validate_runtime()['sources']}
  self.assertTrue(all(runtime[s[0]]['url']==s[2] for s in sources))
  self.assertIn('AI',read('localization/reviews/TW-16-014.json')['reviewer'])
 def test_preserve_previous_core_and_medical_navigation(self):
  before=json.loads(subprocess.check_output(['git','show',BASE+':localization/tw-edition/runtime.json'],cwd=ROOT,text=True))
  after=validate_runtime()
  self.assertEqual(len(before['items']),164)
  self.assertEqual([e['id'] for e in after['items'][:164]],[e['id'] for e in before['items']])
  for previous,current in zip(before['items'],after['items'][:164],strict=True):assert_preserved_or_rechecked(self,previous,current)
  self.assertGreaterEqual(len(after['items']),178)
  b={s['id']:s for s in before['sources']};a={s['id']:s for s in after['sources']}
  self.assertTrue(all(a[k]==v for k,v in b.items()))
  self.assertEqual({e['id'] for e in after['items'][164:178]},IDS)
 def test_exact_progress_and_unfinished_book(self):
  report=publication_report()
  self.assertGreaterEqual(report['publication_completed_entries'],169)
  self.assertEqual(report['publication_total_entries'],765)
  self.assertFalse(report['publication_ready'])
  coverage=read('localization/tw-edition/coverage.json')
  self.assertGreaterEqual(coverage['publication_completed_entries'],169)
  self.assertGreaterEqual(coverage['unique_draft_entries'],437)
  self.assertLessEqual(coverage['entries_without_any_draft'],328)
  self.assertGreaterEqual(coverage['registry_sources'],312)
  self.assertEqual(coverage['unresolved_reference_occurrences'],306)

if __name__=='__main__':unittest.main()

"""第17章意定監護、長照3.0、住院契約與家庭照顧假之臺灣版本回歸。"""
import hashlib,json,subprocess,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from retroactive_audit import assert_preserved_or_rechecked
from review_contract import ROOT, validate_runtime,validate_entry,publication_report
from body_renderer import body_blocks
BASE='72ea775426cdcbc4b716ae506152607b56fc5ca7'
IDS={f'TW-17-{i:03d}' for i in range(1,14)}
REVERSE_MORTGAGE_RECHECK_BATCH='localization/topic-fidelity-reverse-mortgage-recheck-20261114.json'
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
    # Subsequent substantive rechecks may add a reader-facing section while
    # preserving the fixed ID and original review history.
    expected_headings=sum(line.startswith('## ') for line in runtime[key]['body'].splitlines())
    self.assertGreaterEqual(expected_headings,5)
    self.assertEqual(sum(x['tag']=='h3' for x in body_blocks(runtime[key])),expected_headings)
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
  for item in base['items']:assert_preserved_or_rechecked(self,item,current_items[item['id']])
  for source in base['sources']:self.assertEqual(current_sources[source['id']],source)
  self.assertTrue(IDS.issubset(current_items))
  self.assertGreaterEqual(len(after['items']),191)
  bundle_path='localization/tw-edition/sources/ch17-elder-20261017.json'
  sources=get(bundle_path)['sources']
  batch=get(REVERSE_MORTGAGE_RECHECK_BATCH)
  baseline_sources=json.loads(subprocess.check_output(
   ['git','show',batch['baseline_main_sha']+':'+bundle_path],cwd=ROOT,text=True
  ))['sources']
  baseline_runtime=json.loads(subprocess.check_output(
   ['git','show',batch['baseline_main_sha']+':localization/tw-edition/runtime.json'],cwd=ROOT,text=True
  ))
  by_id={row[0]:row for row in sources}
  baseline_by_id={row[0]:row for row in baseline_sources}
  shared_source_ids=set(batch['shared_source_ids'])
  reused_additions=(set(batch['source_records_reused'])-set(baseline_by_id))-shared_source_ids
  self.assertEqual(set(by_id),set(baseline_by_id)|set(batch['new_source_ids'])|reused_additions)
  for source_id,old_source in baseline_by_id.items():
   self.assertEqual(by_id[source_id],old_source)
  for source_id in batch['new_source_ids']:
   self.assertIn(source_id,by_id)
  baseline_runtime_sources={row['id']:row for row in baseline_runtime['sources']}
  for source_id in reused_additions:
   source=baseline_runtime_sources[source_id]
   self.assertEqual(by_id[source_id],[source_id,source['title'],source['url'],source['supports']])
  all_bundle_rows={}
  for path in (ROOT/'localization/tw-edition/sources').glob('*.json'):
   for row in get(path.relative_to(ROOT).as_posix())['sources']:
    self.assertNotIn(row[0],all_bundle_rows)
    all_bundle_rows[row[0]]=row
  for source_id in shared_source_ids:
   source=baseline_runtime_sources[source_id]
   self.assertEqual(all_bundle_rows[source_id],[source_id,source['title'],source['url'],source['supports']])
   self.assertNotIn(source_id,by_id)
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

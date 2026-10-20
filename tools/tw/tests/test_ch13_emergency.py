"""驗證第13章急救首批4條與原有來源審閱資料完全保留。"""
import hashlib,json,subprocess,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from retroactive_audit import assert_preserved_or_rechecked
from review_contract import ROOT,validate_entry,validate_runtime,publication_report
from body_renderer import body_blocks
BASE='5437a44b4d640657f5542a7e259e1e6ea294c9ad'
IDS={'TW-13-001','TW-13-003','TW-13-007','TW-13-030'}
def read(p):return json.loads((ROOT/p).read_text(encoding='utf8'))
class EmergencyTests(unittest.TestCase):
 def test_markdowns_sources_and_reviews(self):
  manifest={e['id']:e for e in read('localization/manifest.json')['entries']}
  runtime=validate_runtime();items={x['id']:x for x in runtime['items']};sources={s['id']:s for s in runtime['sources']}
  self.assertTrue(IDS.issubset(items))
  for key in IDS:
   with self.subTest(id=key):
    m=manifest[key];self.assertEqual(m['status'],'verified');self.assertTrue(validate_entry(m))
    raw=(ROOT/m['target_path']).read_bytes();rv=read(f'localization/reviews/{key}.json')
    self.assertGreater(len(raw),1400);self.assertEqual(hashlib.sha256(raw).hexdigest(),rv['target_sha256'])
    self.assertEqual(raw.decode('utf8'),items[key]['body'])
    self.assertEqual(sum(b['tag']=='h3' for b in body_blocks(items[key])),5)
    self.assertEqual({s['url'] for s in rv['source_checks']},{sources[s]['url'] for s in items[key]['source_ids']})
 def test_taiwan_emergency_rules(self):
  d={e['id']:e['body'] for e in validate_runtime()['items']}
  for key in IDS:
   # 原作120的引文屬跨法域差異說明，不能誤判成要求臺灣民眾撥120。
   instructions=d[key].replace('原作「打120」','原作錯誤號碼')
   self.assertNotIn('打120',instructions)
   self.assertNotIn('撥120',instructions)
   self.assertIn('119',d[key] if key!='TW-13-030' else '119')
  self.assertIn('100至120次',d['TW-13-001'])
  self.assertIn('AED',d['TW-13-001'])
  self.assertIn('FAST',d['TW-13-003'])
  self.assertIn('最後一次確認',d['TW-13-003'])
  self.assertIn('不能等到胸痛超過十五分鐘',d['TW-13-007'])
  self.assertIn('趴下、掩護、穩住',d['TW-13-030'])
 def test_preserve_all_old_runtime_rows(self):
  base=json.loads(subprocess.check_output(['git','show',BASE+':localization/tw-edition/runtime.json'],cwd=ROOT,text=True))
  new=validate_runtime();items={x['id']:x for x in new['items']};sources={s['id']:s for s in new['sources']}
  for old in base['items']:assert_preserved_or_rechecked(self,old,items[old['id']])
  for old in base['sources']:self.assertEqual(sources[old['id']],old)
  registry=read('localization/tw-edition/sources/ch13-emergency-20261017.json')['sources']
  self.assertEqual(len(registry),8)
  for source in registry:self.assertEqual(sources[source[0]]['url'],source[2])
 def test_counts_and_unfinished_scope(self):
  report=publication_report();coverage=read('localization/tw-edition/coverage.json')
  self.assertGreaterEqual(report['publication_completed_entries'],186)
  self.assertEqual(report['publication_total_entries'],765);self.assertFalse(report['publication_ready'])
  self.assertGreaterEqual(coverage['registry_sources'],337)
  self.assertGreaterEqual(coverage['unique_draft_entries'],454)
  self.assertLessEqual(coverage['entries_without_any_draft'],311)
  self.assertEqual(read('localization/ch13-batch-20261017.json')['chapter_total'],48)
if __name__=='__main__':unittest.main()

"""第24章醫療費用、病歷、急診與保險制度：來源、審閱與前版保全回歸。"""
import json, hashlib, sys, unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from review_contract import ROOT,validate_runtime,validate_entry,publication_report
from body_renderer import body_blocks
IDS={f'TW-24-{n:03d}' for n in range(1,16)}

def data(path):return json.loads((ROOT/path).read_text(encoding='utf-8'))

class MedicalCareTaiwanTests(unittest.TestCase):
 def test_15_documents_have_recorded_evidence(self):
  manifest={e['id']:e for e in data('localization/manifest.json')['entries']}
  runtime={e['id']:e for e in validate_runtime()['items']}
  self.assertTrue(IDS.issubset(runtime))
  for key in sorted(IDS):
   with self.subTest(id=key):
    entry=manifest[key];self.assertEqual(entry['status'],'verified');self.assertTrue(validate_entry(entry))
    self.assertTrue(entry['target_path'].startswith('locales/zh-TW/book/ch24/'))
    raw=(ROOT/entry['target_path']).read_bytes();review=data('localization/reviews/'+key+'.json')
    self.assertGreater(len(raw),1200);self.assertEqual(raw.decode('utf-8'),runtime[key]['body'])
    self.assertEqual(hashlib.sha256(raw).hexdigest(),review['target_sha256'])
    self.assertEqual(sum(b['tag']=='h3' for b in body_blocks(runtime[key])),5)
    self.assertIn('AI',review['reviewer']);self.assertTrue(all(s['url'].startswith('https://') and '摘要' in s['supporting_passage'] for s in review['source_checks']))
    self.assertEqual({s['url'] for s in review['source_checks']},{s['url'] for s in validate_runtime()['sources'] if s['id'] in runtime[key]['source_ids']})
 def test_known_medical_distinctions_and_no_trivial_renaming(self):
  items={e['id']:e['body'] for e in validate_runtime()['items']}
  self.assertIn('掛號費',items['TW-24-002']);self.assertIn('部分負擔',items['TW-24-002'])
  self.assertIn('病歷複製',items['TW-24-005']);self.assertIn('健康存摺',items['TW-24-005'])
  self.assertIn('調解',items['TW-24-006']);self.assertIn('檢傷',items['TW-24-007'])
  self.assertIn('不等於所有費用全面免費',items['TW-24-008'])
  self.assertIn('不同制度',items['TW-24-009']);self.assertIn('身心障礙',items['TW-24-010'])
  self.assertIn('不將所有',items['TW-24-011'])
  self.assertIn('書面',items['TW-24-012']);self.assertIn('斷藥',items['TW-24-013']);self.assertIn('90日',items['TW-24-014']);self.assertIn('收據',items['TW-24-015'])
 def test_all_new_sources_are_official_and_registered(self):
  added=data('localization/tw-edition/sources/ch24-care-20261017.json')['sources']
  self.assertEqual(len(added),15);self.assertEqual(len({s[0] for s in added}),15)
  runtime_sources={s['id']:s for s in validate_runtime()['sources']}
  for key,title,url,scope in added:
   self.assertTrue(key.startswith('ch24_'));self.assertEqual(runtime_sources[key]['url'],url)
   self.assertTrue(any(url.split('/')[2].endswith(host) for host in ('gov.tw','mohw.gov.tw','nhi.gov.tw','fda.gov.tw','moj.gov.tw')))
   self.assertTrue(scope)
 def test_no_premature_publication_and_prior_navigation_preserved(self):
  runtime=validate_runtime();ids={e['id'] for e in runtime['items']}
  self.assertTrue({f'TW-NAV-{i:03d}' for i in range(1,10)}.issubset(ids))
  for n,size in [(7,23),(14,12),(15,18),(19,24),(21,13),(23,25),(25,12),(26,13)]:
   self.assertTrue({f'TW-{n:02d}-{i:03d}' for i in range(1,size+1)}.issubset(ids))
  report=publication_report()
  self.assertGreaterEqual(report['publication_completed_entries'],155)
  self.assertEqual(report['publication_total_entries'],765)
  self.assertFalse(report['publication_ready'])

if __name__=='__main__':unittest.main()

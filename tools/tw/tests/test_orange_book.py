"""小橘書事實參考與獨立可出版導航：授權保護、統計及多端共用契約。"""
import hashlib,json,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from review_contract import ROOT,publication_report,validate_runtime
from body_renderer import body_blocks
ID='TW-NAV-010'
PATH='locales/zh-TW/guides/全民安全與防災準備.md'
def data(path):return json.loads((ROOT/path).read_text(encoding='utf-8'))
class OrangeBookTests(unittest.TestCase):
 def test_guide_review_checksum_and_sources(self):
  rt=validate_runtime();items={e['id']:e for e in rt['items']};src={s['id']:s for s in rt['sources']}
  self.assertIn(ID,items)
  item=items[ID];raw=(ROOT/PATH).read_bytes()
  self.assertEqual(item['target_path'],PATH);self.assertEqual(item['body'],raw.decode('utf-8'))
  review=data('localization/reviews/TW-NAV-010.json')
  self.assertEqual(review['target_sha256'],hashlib.sha256(raw).hexdigest())
  self.assertEqual(review['review_due_at'],item['review_due_at'])
  self.assertEqual({row['url'] for row in review['source_checks']},{src[k]['url'] for k in item['source_ids']})
  self.assertEqual(sum(block['tag']=='h3' for block in body_blocks(item)),6)
  self.assertGreater(len(raw),3000)
 def test_core_count_not_inflated_by_navigation(self):
  report=publication_report();rt=validate_runtime()
  self.assertEqual(report['publication_completed_entries'],190)
  self.assertEqual(report['publication_total_entries'],765)
  self.assertFalse(report['publication_ready'])
  self.assertEqual(sum(e['id'].startswith('TW-NAV-') for e in rt['items']),10)
  self.assertEqual(len(rt['items']),200)
  self.assertNotIn(ID,{e['id'] for e in data('localization/manifest.json')['entries']})
  coverage=data('localization/tw-edition/coverage.json')
  self.assertEqual(coverage['registry_sources'],353)
  self.assertEqual(coverage['publication_completed_entries'],190)
 def test_official_attribution_without_pdf_or_image_republication(self):
  text=(ROOT/PATH).read_text()
  self.assertIn('不複製原書PDF',text)
  self.assertIn('七天',text);self.assertIn('三公升',text)
  self.assertIn('一至三天',text);self.assertIn('不能當成',text)
  self.assertIn('心理',text);self.assertIn('查證',text)
  self.assertIn('https://prepare.mnd.gov.tw/download-pdf',text)
  self.assertEqual(len(data('localization/tw-edition/sources/orange-book-20261017.json')['sources']),8)
  for path in ('README.md','locales/zh-TW/README.md','locales/zh-TW/book/ch13/README.md','locales/zh-TW/book/ch14/README.md','locales/zh-TW/book/ch17/README.md'):
   self.assertIn('全民安全與防災準備.md',(ROOT/path).read_text(encoding='utf-8'))
  for file in ROOT.rglob('*'):
   if file.is_file() and file.name.lower().endswith(('.pdf','.png','.jpg','.jpeg','.webp')) and ('orange' in file.name.lower() or '小橘書' in file.name):
    self.fail('手冊圖像或PDF不應被複製進專案：'+str(file))
if __name__=='__main__':unittest.main()

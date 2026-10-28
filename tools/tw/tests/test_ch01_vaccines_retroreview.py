"""驗證臺灣公費銜接、檢測分流與四篇歷史再審不冒稱專業完成。"""
import hashlib,json,subprocess,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from review_contract import ROOT,validate_runtime,validate_entry,publication_report
from body_renderer import body_blocks
from retroactive_audit import assert_preserved_or_rechecked,validate_recheck_history
BASE='b5c80a47faf877ec966396f3618731d59f8caf5b'
NEW={f'TW-01-{n:03}' for n in range(21,25)}
RECHECK={f'TW-13-{n:03}' for n in (12,14,15,25)}
def read(p):return json.loads((ROOT/p).read_text())
class VaccinesRetroreviewTests(unittest.TestCase):
 def test_formal_bodies_sources_hashes_and_rendering(self):
  rt=validate_runtime();items={x['id']:x for x in rt['items']};sources={s['id']:s for s in rt['sources']};manifest={e['id']:e for e in read('localization/manifest.json')['entries']}
  for key in NEW|RECHECK:
   with self.subTest(key=key):
    self.assertTrue(validate_entry(manifest[key]));i=items[key];rv=read(f'localization/reviews/{key}.json');raw=(ROOT/i['target_path']).read_bytes()
    self.assertEqual(i['body'],raw.decode());self.assertEqual(hashlib.sha256(raw).hexdigest(),rv['target_sha256'])
    self.assertEqual({x['url'] for x in rv['source_checks']},{sources[s]['url'] for s in i['source_ids']})
    self.assertEqual(sum(x['tag']=='h3' for x in body_blocks(i)),5)
 def test_2026_policy_and_denominators(self):
  b={x['id']:x['body'] for x in validate_runtime()['items']}
  self.assertIn('2至6個月',b['TW-01-021']);self.assertIn('2011至2020年',b['TW-01-021']);self.assertIn('每千人年7.15例',b['TW-01-021']);self.assertIn('每千人年7.82例',b['TW-01-021']);self.assertIn('舊申報率不能當作2026年即時風險',b['TW-01-021'])
  self.assertIn('PCV21',b['TW-01-022']);self.assertIn('8週例外不適用僅打PPV23',b['TW-01-022']);self.assertIn('Q10',b['TW-01-022']);self.assertIn('不是所有肺炎',b['TW-01-022'])
  self.assertIn('終身一次',b['TW-01-023']);self.assertIn('民眾可領450元',b['TW-01-023']);self.assertIn('缺',b['TW-01-023']);self.assertIn('4週',b['TW-01-023'])
  self.assertIn('每2年一次',b['TW-01-024']);self.assertIn('戒菸未達15年',b['TW-01-024']);self.assertIn('不是每個結節都需開刀',b['TW-01-024'])
  self.assertIn('資料不足',b['TW-13-012']);self.assertIn('15／30',read('localization/reviews/TW-13-014.json')['limits'][-1])
  self.assertIn('全球食物過敏',b['TW-13-015']);self.assertIn('所有溺水者獲救後應送醫',b['TW-13-025'])
 def test_actual_history_and_all_prior_content_preserved_or_rechecked(self):
  old=json.loads(subprocess.check_output(['git','show',BASE+':localization/tw-edition/runtime.json'],cwd=ROOT));rt=validate_runtime();items={x['id']:x for x in rt['items']};sources={s['id']:s for s in rt['sources']}
  for row in old['items']:assert_preserved_or_rechecked(self,row,items[row['id']])
  for row in old['sources']:self.assertEqual(row,sources[row['id']])
  records={r['id']:r for r in read('localization/retroactive-review-register-20261019.json')['substantive_rechecks']}
  for key in RECHECK:
   self.assertEqual(records[key]['status'],'ai_source_rechecked_professional_pending');validate_recheck_history(ROOT,records[key],items[key])
  self.assertFalse(publication_report()['publication_ready'])
if __name__=='__main__':unittest.main()

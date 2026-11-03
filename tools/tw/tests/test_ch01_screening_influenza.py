"""公費界線、統計單位、已合併內容保全與正式閱讀共用契約。"""
import json
import hashlib
import subprocess
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from review_contract import ROOT,validate_runtime,validate_entry,publication_report
from body_renderer import body_blocks
from retroactive_audit import assert_preserved_or_rechecked

class ScreeningInfluenzaTests(unittest.TestCase):
    def test_new_bodies_sources_and_review_hash(self):
        rt=validate_runtime();items={x['id']:x for x in rt['items']};sources={x['id']:x for x in rt['sources']}
        manifest=json.loads((ROOT/'localization/manifest.json').read_text())
        for n in range(17,21):
            key=f'TW-01-{n:03}';entry=next(x for x in manifest['entries'] if x['id']==key)
            with self.subTest(key=key):
                self.assertTrue(validate_entry(entry))
                raw=(ROOT/entry['target_path']).read_bytes()
                review=json.loads((ROOT/f'localization/reviews/{key}.json').read_text())
                self.assertEqual(items[key]['body'],raw.decode())
                self.assertEqual(review['target_sha256'],hashlib.sha256(raw).hexdigest())
                self.assertEqual({x['url'] for x in review['source_checks']},{sources[s]['url'] for s in items[key]['source_ids']})
                expected_sections = 6 if key == 'TW-01-020' else 5
                self.assertEqual(sum(x['tag']=='h3' for x in body_blocks(items[key])),expected_sections)

    def test_policy_and_frequency_do_not_become_personal_probability(self):
        b={x['id']:x['body'] for x in validate_runtime()['items']}
        self.assertIn('40至74歲',b['TW-01-017']);self.assertIn('17,779',b['TW-01-017'])
        self.assertIn('1,429',b['TW-01-018']);self.assertIn('不是HPV感染盛行率',b['TW-01-018'])
        self.assertIn('19,074',b['TW-01-019']);self.assertIn('間歇',b['TW-01-019'])
        for n in (17,18,19):
            self.assertIn('2000',b[f'TW-01-{n:03}']);self.assertIn('不含原位癌',b[f'TW-01-{n:03}'])
        self.assertIn('第二階段已於11月2日開放',b['TW-01-020']);self.assertIn('不是確診流感人數',b['TW-01-020'])
        self.assertNotIn('預定11月2日',b['TW-01-020'])
        self.assertIn('101,746人次',b['TW-01-020'])
        self.assertIn('391例流感併發重症及57例死亡',b['TW-01-020'])
        self.assertIn('不能換算成個人感染機率',b['TW-01-020'])
        self.assertEqual(next(x for x in validate_runtime()['items'] if x['id']=='TW-01-020')['review_due_at'],'2027-02-03')

    def test_all_prior_items_and_sources_unchanged(self):
        old=json.loads(subprocess.check_output(['git','show','4d3080f84f778fa55d070cf66ea75de80c56f988:localization/tw-edition/runtime.json'],cwd=ROOT))
        rt=validate_runtime();items={x['id']:x for x in rt['items']};sources={x['id']:x for x in rt['sources']}
        for row in old['items']:assert_preserved_or_rechecked(self,row,items[row['id']])
        for row in old['sources']:self.assertEqual(row,sources[row['id']])
        self.assertFalse(publication_report()['publication_ready'])
if __name__=='__main__':unittest.main()

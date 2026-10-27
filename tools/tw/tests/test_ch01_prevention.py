"""新正文須來源與SHA一致；原有正文只能透過有證據的再審修訂。"""
import hashlib
import json
import subprocess
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from review_contract import ROOT, validate_entry, validate_runtime
from retroactive_audit import assert_preserved_or_rechecked
from body_renderer import body_blocks

class PreventionBatchTests(unittest.TestCase):
    def test_new_bodies_evidence_and_shared_reader(self):
        manifest=json.loads((ROOT/'localization/manifest.json').read_text())
        runtime=validate_runtime(); items={x['id']:x for x in runtime['items']}
        sources={x['id']:x for x in runtime['sources']}
        for n in range(13,17):
            key=f'TW-01-{n:03}'
            entry=next(x for x in manifest['entries'] if x['id']==key)
            with self.subTest(key=key):
                self.assertTrue(validate_entry(entry))
                raw=(ROOT/entry['target_path']).read_bytes()
                review=json.loads((ROOT/f'localization/reviews/{key}.json').read_text())
                self.assertEqual(items[key]['body'],raw.decode())
                self.assertEqual(review['target_sha256'],hashlib.sha256(raw).hexdigest())
                self.assertEqual({x['url'] for x in review['source_checks']},{sources[k]['url'] for k in items[key]['source_ids']})
                self.assertEqual(sum(x['tag']=='h3' for x in body_blocks(items[key])),5)

    def test_current_baseline_preserved_or_documented(self):
        prior=json.loads(subprocess.check_output(['git','show','6b85081cd806bea348523d486bf9e87efb686117:localization/tw-edition/runtime.json'],cwd=ROOT))
        runtime=validate_runtime(); items={x['id']:x for x in runtime['items']}; sources={x['id']:x for x in runtime['sources']}
        for item in prior['items']: assert_preserved_or_rechecked(self,item,items[item['id']])
        for source in prior['sources']: self.assertEqual(source,sources[source['id']])

    def test_safety_correction_and_statistical_boundaries(self):
        items={x['id']:x['body'] for x in validate_runtime()['items']}
        self.assertIn('先讓患者前傾',items['TW-13-026'])
        self.assertNotIn('未受訓者不要胡亂按壓胸腹',items['TW-13-026'])
        self.assertIn('非高危險群尚無須全面追加',items['TW-01-014'])
        self.assertIn('2026年當年累計4例',items['TW-01-015'])
        self.assertIn('不是全臺釘刺傷人數',items['TW-01-015'])
        self.assertIn('目前依學校通知核對本人名冊、接種日及補接種期限',items['TW-01-016'])
        for key in ('TW-13-001','TW-13-026','TW-13-043','TW-13-044'):
            self.assertIn('臺灣事件頻率再審',items[key])
            self.assertIn('不等於醫師或急救教官專業簽證',items[key])
if __name__=='__main__':unittest.main()

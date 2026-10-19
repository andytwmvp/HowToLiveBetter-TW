"""歷史災害及外傷正文的實際修訂、來源與閱讀契約。"""
import hashlib
import json
import subprocess
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from review_contract import ROOT, validate_runtime, validate_entry, publication_report
from retroactive_audit import assert_preserved_or_rechecked, validate_recheck_history
from body_renderer import body_blocks

BASE = 'c530f53fbf97b9c90ba6e90824e57b36cb2bafcb'
IDS = {f'TW-13-{n:03}' for n in (30, 32, 33, 40)}

class DisasterAltitudeTraumaTests(unittest.TestCase):
    def test_actionable_safety_boundaries(self):
        b = {i['id']: i['body'] for i in validate_runtime()['items']}
        for text in ('不等待警報', '不為關瓦斯', '不是個人受傷機率'):
            self.assertIn(text, b['TW-13-030'])
        for text in ('不會殘留電荷', '水管', '最後一次雷聲或閃電', '不是可靠避雷所'):
            self.assertIn(text, b['TW-13-032'])
        for text in ('1066', '2007年4月至2008年3月', '871', '就醫者', '氧氣罐', '血氧'):
            self.assertIn(text, b['TW-13-033'])
        for text in ('四肢', '持續加壓', '胸腹', '不為沖洗', '同定義'):
            self.assertIn(text, b['TW-13-040'])

    def test_recheck_history_and_body_source_contracts(self):
        rt = validate_runtime()
        items = {i['id']: i for i in rt['items']}
        sources = {s['id']: s for s in rt['sources']}
        records = json.loads((ROOT/'localization/retroactive-review-register-20261019.json').read_text())
        records = {r['id']: r for r in records['substantive_rechecks']}
        manifest = json.loads((ROOT/'localization/manifest.json').read_text())
        manifest = {e['id']: e for e in manifest['entries']}
        for key in IDS:
            with self.subTest(key=key):
                row = records[key]
                self.assertEqual(row['prior_revision'], BASE)
                validate_recheck_history(ROOT, row, items[key])
                self.assertTrue(validate_entry(manifest[key]))
                review = json.loads((ROOT/f'localization/reviews/{key}.json').read_text())
                raw = (ROOT/items[key]['target_path']).read_bytes()
                self.assertEqual(raw.decode(), items[key]['body'])
                self.assertEqual(hashlib.sha256(raw).hexdigest(), review['target_sha256'])
                self.assertEqual({s['url'] for s in review['source_checks']}, {sources[s]['url'] for s in items[key]['source_ids']})
                self.assertEqual(sum(b['tag']=='h3' for b in body_blocks(items[key])), 5)

    def test_original_items_sources_and_publication_limit_preserved(self):
        old = json.loads(subprocess.check_output(['git', 'show', BASE+':localization/tw-edition/runtime.json'], cwd=ROOT))
        rt = validate_runtime()
        items = {i['id']: i for i in rt['items']}
        sources = {s['id']: s for s in rt['sources']}
        self.assertEqual(set(items), {i['id'] for i in old['items']})
        for row in old['items']:
            assert_preserved_or_rechecked(self, row, items[row['id']])
        for row in old['sources']:
            self.assertEqual(row, sources[row['id']])
        self.assertFalse(publication_report()['publication_ready'])

    def test_statistics_are_separate_samples_not_current_population_rates(self):
        batch = json.loads((ROOT/'localization/disaster-altitude-trauma-20261020.json').read_text())
        self.assertEqual(set(batch['ai_rechecked_ids']), IDS)
        self.assertEqual(batch['new_core_ids'], [])
        self.assertEqual(batch['professional_review'], 'pending')
        records = batch['statistics']
        self.assertEqual([s['denominator'] for s in records], [1066, 871])
        self.assertIsNone(records[0]['numerator'])
        self.assertEqual(records[1]['numerator'], 558)
        self.assertTrue(all(s['limits'] and s['period'] and s['method'] for s in records))

if __name__ == '__main__':
    unittest.main()

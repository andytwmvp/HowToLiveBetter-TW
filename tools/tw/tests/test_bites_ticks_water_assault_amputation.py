"""五篇感染、照護與斷肢歷史再審的安全與證據契約。"""
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

BASE = '48433c16d9efedabf9f5775d33f06a0597b94750'
IDS = {f'TW-13-{n:03}' for n in (13, 34, 35, 42, 47)}

class BitesTicksWaterAssaultAmputationTests(unittest.TestCase):
    def test_actionable_safety_boundaries(self):
        b = {i['id']: i['body'] for i in validate_runtime()['items']}
        for text in ('先止血', '黏膜', '至少十五分鐘', '1,146件', '41件', '不能當成人被咬後的感染機率'):
            self.assertIn(text, b['TW-13-013'])
        for text in ('儘速移除', '不要旋轉', '不要為等', '商業檢測'):
            self.assertIn(text, b['TW-13-034'])
        for text in ('不能生飲', '化學汙染煮沸仍有風險', '重金屬', '全臺水汙染率', '感染機率'):
            self.assertIn(text, b['TW-13-035'])
        for text in ('3,643人', '3,078人', '同意', '法定通報', '2023-02-17', '暫停'):
            self.assertIn(text, b['TW-13-042'])
        for text in ('不為找冰', '記錄', '同一口徑', '6小時'):
            self.assertIn(text, b['TW-13-047'])

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
        batch = json.loads((ROOT/'localization/bites-ticks-water-assault-amputation-20261020.json').read_text())
        self.assertEqual(set(batch['ai_rechecked_ids']), IDS)
        self.assertEqual(batch['new_core_ids'], [])
        self.assertEqual(batch['professional_review'], 'pending')
        records = {s['id']: s for s in batch['statistics']}
        self.assertEqual(records['latest_animal_antigen']['numerator'], 41)
        self.assertEqual(records['latest_animal_antigen']['denominator'], 1146)
        self.assertEqual(records['animal_monitoring']['numerator'], 137)
        self.assertEqual(records['animal_monitoring']['denominator'], 2597)
        self.assertEqual(records['assault_arrivals']['numerator'], 3643)
        self.assertEqual(records['assault_certificates']['numerator'], 3078)
        self.assertIsNone(records['assault_arrivals']['denominator'])
        self.assertTrue(all(x['limits'] and x['period'] and x['method'] for x in records.values()))
        self.assertEqual(batch['legal_effective_dates']['assault_selected_articles'], '2023-02-17')

if __name__ == '__main__':
    unittest.main()

"""三篇暴力現場與施救權益歷史再審的安全與證據契約。"""
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

BASE = 'ee8f6ed08267350e3808302c8be9dc9f47cad0f9'
IDS = {f'TW-13-{n:03}' for n in (36, 37, 39)}

class ConflictRescueRightsTests(unittest.TestCase):
    def test_actionable_safety_boundaries(self):
        b = {i['id']: i['body'] for i in validate_runtime()['items']}
        for text in ('七類', '2024年9月', '不要為了財物突然追趕', '無聲', '不要尾隨'):
            self.assertIn(text, b['TW-13-036'])
        for text in ('第24條', '2023-07-01', '七類', '不要為蒐證', '心理'):
            self.assertIn(text, b['TW-13-037'])
        for text in ('2013-01-18', '非值勤', '第24條', '第176條', '2023-07-01', '免責不是補助'):
            self.assertIn(text, b['TW-13-039'])

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

    def test_count_scope_and_law_effective_dates(self):
        b = json.loads((ROOT/'localization/conflict-rescue-rights-20261020.json').read_text())
        self.assertEqual(set(b['ai_rechecked_ids']), IDS)
        self.assertEqual(b['new_core_ids'], [])
        self.assertEqual(b['professional_review'], 'pending')
        s = {x['id']:x for x in b['statistics']}
        self.assertEqual(s['violent_cases_2025']['value'],503)
        self.assertEqual(s['robbery_2025']['value'],130)
        self.assertEqual(s['snatch_2025']['value'],118)
        self.assertTrue(all(x['denominator'] is None and x['period']=='2025年' and x['limits'] for x in s.values()))
        self.assertEqual(b['legal_effective_dates']['ems_14_2'],'2013-01-18')
        self.assertEqual(b['legal_effective_dates']['victim_services_compensation'],'2023-07-01')
        self.assertEqual(b['legal_effective_dates']['victim_definition'],'2023-02-10')
        rows = json.loads((ROOT/'localization/retroactive-review-register-20261019.json').read_text())['substantive_rechecks']
        chapter = {i['id'] for i in validate_runtime()['items'] if i['id'].startswith('TW-13-')}
        self.assertEqual(chapter, {r['id'] for r in rows if r['id'].startswith('TW-13-')})
        self.assertTrue(all(r['status']=='ai_source_rechecked_professional_pending' for r in rows))

if __name__ == '__main__':
    unittest.main()

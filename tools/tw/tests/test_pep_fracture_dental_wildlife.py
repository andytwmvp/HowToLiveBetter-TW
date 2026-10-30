"""四篇PEP、骨折、牙齒與遇獸歷史再審的安全與證據契約。"""
import hashlib
import json
import subprocess
import sys
import unittest
import copy
from unittest.mock import patch
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from review_contract import ROOT, validate_runtime, validate_entry, publication_report
from retroactive_audit import assert_preserved_or_rechecked, validate_recheck_history, documented_revision, validate_reader_copy_cleanup_history
from body_renderer import body_blocks

BASE = '8c9685deee6efa0936178695582d4c908c1c5599'
IDS = {f'TW-13-{n:03}' for n in (31, 38, 41, 48)}

class PepFractureDentalWildlifeTests(unittest.TestCase):
    def test_actionable_safety_boundaries(self):
        b = {i['id']: i['body'] for i in validate_runtime()['items']}
        for text in ('不要等對方', '776', '679', '97', '2025-12-01', '急診欄'):
            self.assertIn(text, b['TW-13-038'])
        for text in ('先處理', '骨頭', '不要為製作夾板', '沒有變形'):
            self.assertIn(text, b['TW-13-041'])
        for text in ('晾乾', '容器', '6,312', '19.9%', '30分鐘'):
            self.assertIn(text, b['TW-13-048'])
        for text in ('不裝死', '不爬樹', '2026-09-14', '0800-000-930'):
            self.assertIn(text, b['TW-13-031'])

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
        self.assertTrue({i['id'] for i in old['items']}.issubset(items))
        for row in old['items']:
            assert_preserved_or_rechecked(self, row, items[row['id']])
        for row in old['sources']:
            self.assertEqual(row, sources[row['id']])
        self.assertFalse(publication_report()['publication_ready'])

    def test_statistics_and_effective_date_do_not_imply_personal_rates(self):
        batch = json.loads((ROOT/'localization/pep-fracture-dental-wildlife-20261020.json').read_text())
        self.assertEqual(set(batch['ai_rechecked_ids']), IDS)
        self.assertEqual(batch['new_core_ids'], [])
        self.assertEqual(batch['professional_review'], 'pending')
        stats = {s['id']: s for s in batch['statistics']}
        self.assertEqual(stats['hiv_202609']['numerator'], 776)
        self.assertIsNone(stats['hiv_202609']['denominator'])
        self.assertEqual(stats['dental_2009']['denominator'], 6312)
        self.assertIsNone(stats['dental_2009']['numerator'])
        self.assertEqual(stats['dental_2009']['value'], 19.9)
        self.assertTrue(all(s['limits'] and s['period'] and s['method'] for s in stats.values()))
        self.assertEqual(batch['policy_effective_dates']['opep'], '2025-12-01')

    def test_source_retirement_requires_history_reason_and_replacement(self):
        import retroactive_audit
        rt = validate_runtime()
        current = next(i for i in rt['items'] if i['id']=='TW-13-048')
        old_rt = json.loads(subprocess.check_output(['git','show',BASE+':localization/tw-edition/runtime.json'],cwd=ROOT))
        old = next(i for i in old_rt['items'] if i['id']==current['id'])
        rows = json.loads((ROOT/'localization/retroactive-review-register-20261019.json').read_text())
        record = next(r for r in rows['substantive_rechecks'] if r['id']==current['id'])
        cleanup = next(r for r in rows['reader_copy_cleanups'] if r['id']==current['id'] and r['after_sha256']==hashlib.sha256(current['body'].encode()).hexdigest())
        reviewed = validate_reader_copy_cleanup_history(ROOT, cleanup, current)
        self.assertEqual([r['id'] for r in record['retired_sources']], ['dental_iadt_2024'])
        self.assertTrue(documented_revision(old, reviewed, record))
        validate_recheck_history(ROOT, record, current)
        for field, value in [('reason',''),('prior_source_sha256',None),('replacement_ids',[]),('replacement_ids',['unknown']),('id','other')]:
            bad = copy.deepcopy(record)
            bad['retired_sources'][0][field] = value
            self.assertFalse(documented_revision(old,reviewed,bad),field)
        bad = copy.deepcopy(record)
        bad['prior_revision'] = BASE
        bad['retired_sources'][0]['prior_source_sha256'] = '0'*64
        with self.assertRaises(ValueError):
            validate_recheck_history(ROOT,bad,current)
        bad = copy.deepcopy(record)
        del bad['retired_sources']
        self.assertFalse(documented_revision(old,reviewed,bad))
        original_load = retroactive_audit.load
        def altered_load(root, relative):
            data = original_load(root,relative)
            if relative=='localization/tw-edition/runtime.json':
                next(s for s in data['sources'] if s['id']=='dental_iadt_2024')['title']='mutated'
            return data
        with patch.object(retroactive_audit,'load',side_effect=altered_load):
            with self.assertRaises(ValueError):
                validate_recheck_history(ROOT,record,current)

if __name__ == '__main__':
    unittest.main()

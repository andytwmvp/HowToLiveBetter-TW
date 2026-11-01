"""臺灣急救、慢性用藥、食品通報與住宿式長照再審契約。"""
import hashlib
import json
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from review_contract import ROOT, publication_report, validate_runtime
from retroactive_audit import assert_preserved_or_rechecked, validate_recheck_history


BASE = '6369232c36a5f4c002ddacbc421b1ec4a96699ec'
DATE = '2026-11-01'
DUE = '2027-01-31'
IDS = {'TW-24-001', 'TW-16-001', 'TW-16-004', 'TW-24-008', 'TW-17-011'}
BATCH = 'localization/medical-ltc-recheck-20261101.json'


def load(path):
    return json.loads((ROOT / path).read_text(encoding='utf-8'))


def digest(value):
    return hashlib.sha256(value.encode('utf-8')).hexdigest()


class MedicalLtcRecheckTests(unittest.TestCase):
    def test_body_hash_source_history_and_manifest_are_consistent(self):
        runtime = validate_runtime()
        items = {item['id']: item for item in runtime['items']}
        sources = {source['id']: source for source in runtime['sources']}
        register = load('localization/retroactive-review-register-20261019.json')
        rows = {row['id']: row for row in register['substantive_rechecks'][-len(IDS):]}
        manifest = {entry['id']: entry for entry in load('localization/manifest.json')['entries']}
        self.assertEqual(set(rows), IDS)
        for key in IDS:
            item = items[key]
            review = load(f'localization/reviews/{key}.json')
            row = rows[key]
            validate_recheck_history(ROOT, row, item)
            self.assertEqual((ROOT / item['target_path']).read_text(encoding='utf-8'), item['body'])
            self.assertEqual(review['target_sha256'], digest(item['body']))
            self.assertEqual(review['source_reviewed_sha256'], digest(item['body']))
            self.assertEqual(review['source_checks'], row['source_checks'])
            self.assertEqual(review['limits'], row['limits'])
            self.assertEqual(
                {check['url'] for check in review['source_checks']},
                {sources[source_id]['url'] for source_id in item['source_ids']},
            )
            self.assertEqual(manifest[key]['sources'], item['source_ids'])
            self.assertEqual(manifest[key]['verified_at'], DATE)
            self.assertEqual(item['reviewed_at'], DATE)
            self.assertEqual(item['review_due_at'], DUE)
            self.assertEqual(row['prior_revision'], BASE)
            self.assertEqual(row['status'], 'ai_source_rechecked_professional_pending')
            for check in review['source_checks']:
                self.assertGreaterEqual(len(check['supporting_passage']), 50)
                self.assertNotEqual(check['claim'], check['supporting_passage'])
                self.assertIn('非逐字', check['supporting_passage'])

    def test_previous_runtime_history_and_source_objects_are_preserved(self):
        previous = json.loads(
            subprocess.check_output(
                ['git', 'show', BASE + ':localization/tw-edition/runtime.json'], cwd=ROOT
            )
        )
        previous_register = json.loads(
            subprocess.check_output(
                ['git', 'show', BASE + ':localization/retroactive-review-register-20261019.json'], cwd=ROOT
            )
        )
        runtime = validate_runtime()
        items = {item['id']: item for item in runtime['items']}
        sources = {source['id']: source for source in runtime['sources']}
        current_register = load('localization/retroactive-review-register-20261019.json')
        self.assertEqual(
            current_register['substantive_rechecks'][:len(previous_register['substantive_rechecks'])],
            previous_register['substantive_rechecks'],
        )
        self.assertEqual(
            len(current_register['substantive_rechecks']),
            len(previous_register['substantive_rechecks']) + len(IDS),
        )
        previous_ids = [item['id'] for item in previous['items']]
        self.assertEqual(previous_ids, [item['id'] for item in runtime['items'] if item['id'] in set(previous_ids)])
        for old_item in previous['items']:
            assert_preserved_or_rechecked(self, old_item, items[old_item['id']])
        for old_source in previous['sources']:
            self.assertEqual(old_source, sources[old_source['id']])
        batch = load(BATCH)
        self.assertEqual(len(batch['new_source_ids']), 2)
        self.assertTrue(set(batch['new_source_ids']).issubset(sources))
        self.assertEqual(len(runtime['sources']), len(previous['sources']) + 2)

    def test_taiwan_frequency_and_law_boundaries_are_not_overstated(self):
        batch = load(BATCH)
        runtime = validate_runtime()
        items = {item['id']: item for item in runtime['items']}
        self.assertEqual(batch['new_core_ids'], [])
        self.assertEqual(set(batch['frequency_assessments']), IDS)
        self.assertFalse(any(row['credible_taiwan_rate_found'] for row in batch['frequency_assessments'].values()))
        stat = batch['statistics'][0]
        self.assertEqual((stat['numerator'], stat['denominator']), (None, None))
        self.assertIn('不使用於正文', stat['limitations'])
        self.assertNotIn('30.4%', items['TW-16-001']['body'])
        self.assertNotIn('302萬', items['TW-16-001']['body'])
        self.assertIn('2017-04-15', items['TW-24-001']['body'])
        self.assertIn('第18條', items['TW-24-008']['body'])
        self.assertIn('第21條', items['TW-24-008']['body'])
        self.assertIn('不是第18條醫療補助的同一項給付', items['TW-24-008']['body'])
        self.assertIn('得直接通知終止', items['TW-17-011']['body'])
        self.assertIn('長照服務地理資訊地圖', items['TW-17-011']['body'])
        legal = {row['law']: row for row in batch['legal_evidence']}
        contract = next(
            row for law, row in legal.items()
            if law.startswith('機構住宿式服務類長照機構定型化契約')
        )
        self.assertEqual((contract['announced_at'], contract['effective_at']), ('2024-03-15', '2024-03-15'))
        self.assertEqual(batch['professional_review'], 'pending')
        self.assertFalse(publication_report()['publication_ready'])

    def test_retired_food_notice_route_keeps_original_provenance(self):
        previous = json.loads(
            subprocess.check_output(
                ['git', 'show', BASE + ':localization/tw-edition/runtime.json'], cwd=ROOT
            )
        )
        old_source = next(source for source in previous['sources'] if source['id'] == 'ch16_fda_supp')
        runtime = validate_runtime()
        sources = {source['id']: source for source in runtime['sources']}
        item = next(item for item in runtime['items'] if item['id'] == 'TW-16-004')
        row = next(
            row for row in load('localization/retroactive-review-register-20261019.json')['substantive_rechecks']
            if row['id'] == 'TW-16-004' and row['reviewed_at'] == DATE
        )
        retired = next(source for source in row['retired_sources'] if source['id'] == 'ch16_fda_supp')
        self.assertEqual(sources['ch16_fda_supp'], old_source)
        self.assertEqual(retired['prior_source_sha256'], hashlib.sha256(
            json.dumps(old_source, ensure_ascii=False, sort_keys=True).encode('utf-8')
        ).hexdigest())
        self.assertNotIn('ch16_fda_supp', item['source_ids'])
        self.assertIn('ch16_fda_food_adverse_report_20260203', item['source_ids'])

    def test_reader_articles_do_not_contain_batch_progress_notes(self):
        runtime = validate_runtime()
        items = {item['id']: item for item in runtime['items']}
        for key in IDS:
            body = items[key]['body']
            self.assertEqual(body.count('\n## '), 5)
            for phrase in ('本批', '累計', 'AI來源實質再審', '專業審閱仍待取得', '本文查閱日為'):
                self.assertNotIn(phrase, body)


if __name__ == '__main__':
    unittest.main()

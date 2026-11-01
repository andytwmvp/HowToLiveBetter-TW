"""臺灣急救、慢性用藥、食品通報與住宿式長照再審契約。"""
import hashlib
import json
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from review_contract import ROOT, publication_report, validate_runtime
from retroactive_audit import (
    _historical_recheck_edges,
    assert_preserved_or_rechecked,
    validate_recheck_history,
)


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
    @classmethod
    def setUpClass(cls):
        cls.batch = load(BATCH)
        cls.register = load('localization/retroactive-review-register-20261019.json')
        cls.runtime = validate_runtime()
        cls.items = {item['id']: item for item in cls.runtime['items']}
        cls.sources = {source['id']: source for source in cls.runtime['sources']}
        cls.manifest = {entry['id']: entry for entry in load('localization/manifest.json')['entries']}
        snapshots = cls.batch['review_history']
        cls.batch_rows = {}
        cls.batch_items = {}
        for key in IDS:
            history = snapshots[key]
            candidates = [
                row for row in cls.register['substantive_rechecks']
                if row.get('id') == key
                and row.get('reviewed_at') == DATE
                and row.get('prior_revision') == BASE
                and row.get('after_sha256') == history['after_body_sha256']
            ]
            if len(candidates) != 1:
                continue
            cls.batch_rows[key] = candidates[0]
            matches = [
                (new, row)
                for _old, new, row in _historical_recheck_edges(ROOT, key)
                if row == candidates[0]
            ]
            if len(matches) == 1:
                cls.batch_items[key] = matches[0][0]
            else:
                current = cls.items.get(key)
                if current and digest(current['body']) == history['after_body_sha256']:
                    cls.batch_items[key] = current

    def test_body_hash_source_history_and_manifest_are_consistent(self):
        self.assertEqual(set(self.batch_rows), IDS)
        self.assertEqual(set(self.batch_items), IDS)
        current_rows = {}
        for key in IDS:
            item = self.items[key]
            review = load(f'localization/reviews/{key}.json')
            source_reviewed_sha256 = review.get('source_reviewed_sha256', review['target_sha256'])
            candidates = [
                row for row in self.register['substantive_rechecks']
                if row.get('id') == key
                and row.get('reviewed_at') == review['reviewed_at']
                and row.get('after_sha256') == source_reviewed_sha256
                and row.get('source_checks') == review['source_checks']
                and row.get('limits') == review['limits']
            ]
            self.assertEqual(len(candidates), 1, key)
            current_rows[key] = candidates[0]
            batch_row = self.batch_rows[key]
            batch_history = self.batch['review_history'][key]
            prior_review = json.loads(subprocess.check_output(
                ['git', 'show', f"{BASE}:localization/reviews/{key}.json"], cwd=ROOT
            ))
            self.assertEqual(batch_row['prior_reviewed_at'], prior_review['reviewed_at'])
            self.assertEqual(batch_row['prior_review_due_at'], prior_review['review_due_at'])
            self.assertEqual(batch_history['prior_reviewed_at'], prior_review['reviewed_at'])
            self.assertEqual(batch_history['prior_review_due_at'], prior_review['review_due_at'])
            self.assertEqual(batch_row['prior_review_sha256'], digest(
                subprocess.check_output(['git', 'show', f"{BASE}:localization/reviews/{key}.json"], cwd=ROOT).decode('utf-8')
            ))
            self.assertEqual(batch_history['after_body_sha256'], batch_row['after_sha256'])
            if batch_row == current_rows[key]:
                self.assertEqual(self.batch_items[key]['body'], item['body'])
            validate_recheck_history(ROOT, current_rows[key], item)
            self.assertEqual((ROOT / item['target_path']).read_text(encoding='utf-8'), item['body'])
            self.assertEqual(review['target_sha256'], digest(item['body']))
            self.assertEqual(review['source_reviewed_sha256'], digest(item['body']))
            self.assertEqual(review['source_checks'], current_rows[key]['source_checks'])
            self.assertEqual(review['limits'], current_rows[key]['limits'])
            self.assertEqual(
                {check['url'] for check in review['source_checks']},
                {self.sources[source_id]['url'] for source_id in item['source_ids']},
            )
            self.assertEqual(self.manifest[key]['sources'], item['source_ids'])
            self.assertEqual(self.manifest[key]['verified_at'], item['reviewed_at'])
            self.assertEqual(review['reviewed_at'], item['reviewed_at'])
            self.assertEqual(review['review_due_at'], item['review_due_at'])
            self.assertEqual(batch_row['prior_revision'], BASE)
            self.assertEqual(batch_row['review_due_at'], DUE)
            self.assertEqual(batch_row['status'], 'ai_source_rechecked_professional_pending')
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
        self.assertEqual(set(self.batch_rows), IDS)
        previous_ids = [item['id'] for item in previous['items']]
        self.assertEqual(previous_ids, [item['id'] for item in runtime['items'] if item['id'] in set(previous_ids)])
        for old_item in previous['items']:
            assert_preserved_or_rechecked(self, old_item, items[old_item['id']])
        for old_source in previous['sources']:
            self.assertEqual(old_source, sources[old_source['id']])
        batch = load(BATCH)
        self.assertEqual(len(batch['new_source_ids']), 2)
        self.assertTrue(set(batch['new_source_ids']).issubset(sources))
        self.assertEqual(self.batch['source_counts']['runtime_sources_before'], len(previous['sources']))
        self.assertEqual(self.batch['source_counts']['runtime_sources_after'], len(previous['sources']) + 2)
        self.assertGreaterEqual(len(runtime['sources']), self.batch['source_counts']['runtime_sources_after'])

    def test_taiwan_frequency_and_law_boundaries_are_not_overstated(self):
        batch = load(BATCH)
        items = self.batch_items
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
        medical_law = next(row for law, row in legal.items() if law.startswith('醫療法2026-09-23'))
        self.assertEqual((medical_law['announced_at'], medical_law['effective_at']), ('2026-09-23', '2026-09-25'))
        ltc_law = next(row for law, row in legal.items() if law.startswith('長期照顧服務法2021'))
        self.assertEqual((ltc_law['announced_at'], ltc_law['effective_at']), ('2021-06-09', '2021-06-11'))
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
        item = self.batch_items['TW-16-004']
        row = self.batch_rows['TW-16-004']
        retired = next(source for source in row['retired_sources'] if source['id'] == 'ch16_fda_supp')
        self.assertEqual(sources['ch16_fda_supp'], old_source)
        self.assertEqual(retired['prior_source_sha256'], hashlib.sha256(
            json.dumps(old_source, ensure_ascii=False, sort_keys=True).encode('utf-8')
        ).hexdigest())
        self.assertNotIn('ch16_fda_supp', item['source_ids'])
        self.assertIn('ch16_fda_food_adverse_report_20260203', item['source_ids'])

    def test_reader_articles_do_not_contain_batch_progress_notes(self):
        for key in IDS:
            body = self.items[key]['body']
            for phrase in ('本批', '累計', 'AI來源實質再審', '專業審閱仍待取得', '本文查閱日為'):
                self.assertNotIn(phrase, body)


if __name__ == '__main__':
    unittest.main()

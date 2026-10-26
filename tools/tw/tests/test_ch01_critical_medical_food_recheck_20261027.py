"""第1章四篇安全、心理危機、心血管與食品毒理歷史實質再審契約。"""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from content_validation import load_json
from retroactive_audit import validate_recheck_history
from review_contract import ROOT, validate_runtime

BASE = '14b71d87acf2acad5fea74c6de500cd5ed042d9b'
EVIDENCE_PATH = 'localization/ch01-critical-medical-food-recheck-20261027.json'
ITEM_IDS = {'TW-01-015', 'TW-01-032', 'TW-01-044', 'TW-01-048'}
NEW_SOURCE_IDS = {
    'ch01_cdc_tetanus_manual_2026',
    'ch01_cdc_tetanus_counts_20261027',
    'ch01_mohw_suicide_stats_114',
    'ch01_af_stroke_guideline_2024',
    'ch01_af_incidence_2021',
    'ch01_food_tpe_milkrice_2026',
}


def read(path):
    return load_json(ROOT / path)


def old(path):
    return json.loads(subprocess.check_output(
        ['git', 'show', f'{BASE}:{path}'], cwd=ROOT, text=True
    ))


class Ch01CriticalMedicalFoodRecheckTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.evidence = read(EVIDENCE_PATH)
        cls.runtime = validate_runtime()
        cls.items = {item['id']: item for item in cls.runtime['items']}
        cls.sources = {source['id']: source for source in cls.runtime['sources']}
        cls.manifest = {
            entry['id']: entry
            for entry in read('localization/manifest.json')['entries']
        }
        cls.coverage = read('localization/tw-edition/coverage.json')
        cls.register = read('localization/retroactive-review-register-20261019.json')
        cls.records = {
            record['id']: record
            for record in cls.register['substantive_rechecks']
        }
        cls.evidence_items = {item['id']: item for item in cls.evidence['items']}

    def test_counts_and_publication_boundary(self):
        before, after = self.evidence['counts_before'], self.evidence['counts_after']
        self.assertEqual(self.evidence['base_main_sha'], BASE)
        self.assertEqual(set(self.evidence_items), ITEM_IDS)
        self.assertEqual(self.evidence['new_core_entries'], [])
        self.assertEqual(after['substantive_rechecks'], before['substantive_rechecks'] + 4)
        self.assertEqual((before['substantive_rechecks'], after['substantive_rechecks']), (194, 198))
        self.assertEqual(after['runtime_sources'], before['runtime_sources'] + len(NEW_SOURCE_IDS))
        self.assertEqual(after['source_registry'], before['source_registry'] + len(NEW_SOURCE_IDS))
        self.assertEqual((before['json_files_checked'], after['json_files_checked']), (473, 475))
        for field in ('core_completed', 'core_total', 'shared_reader_items',
                      'topics_with_any_content', 'topics_without_content',
                      'unresolved_source_ids', 'unresolved_reference_occurrences'):
            self.assertEqual(after[field], before[field], field)
        self.assertEqual((after['unresolved_source_ids'], after['unresolved_reference_occurrences']), (115, 306))
        self.assertEqual(len(self.coverage['unresolved_source_ids']), 115)
        self.assertEqual(self.coverage['unresolved_reference_occurrences'], 306)
        # This test certifies the historical batch snapshot. Later batches may
        # append sources and JSON files without changing that snapshot.
        self.assertGreaterEqual(len(self.runtime['sources']), after['runtime_sources'])
        self.assertGreaterEqual(self.coverage['registry_sources'], after['source_registry'])
        self.assertGreaterEqual(self.coverage['json_files_checked'], after['json_files_checked'])
        self.assertFalse(self.evidence['publication_ready'])
        self.assertFalse(self.coverage['publication_ready'])

    def test_body_runtime_manifest_review_and_history_hashes_align(self):
        for item_id in ITEM_IDS:
            with self.subTest(item=item_id):
                item = self.evidence_items[item_id]
                runtime_item = self.items[item_id]
                body = (ROOT / item['target_path']).read_bytes()
                body_hash = hashlib.sha256(body).hexdigest()
                markdown = body.decode('utf-8')
                review_path = f'localization/reviews/{item_id}.json'
                review_raw = (ROOT / review_path).read_bytes()
                review = json.loads(review_raw)
                record = self.records[item_id]
                manifest_entry = self.manifest[item_id]

                self.assertEqual(body_hash, item['after_sha256'])
                self.assertEqual(body_hash, review['target_sha256'])
                self.assertEqual(markdown, runtime_item['body'])
                self.assertEqual(item['source_ids'], runtime_item['source_ids'])
                self.assertEqual(item['source_ids'], manifest_entry['sources'])
                self.assertEqual(self.evidence['reviewed_at'], manifest_entry['verified_at'])
                self.assertEqual(review['reviewed_at'], self.evidence['reviewed_at'])
                self.assertEqual(review['review_due_at'], record['review_due_at'])
                self.assertEqual(record['prior_revision'], BASE)
                self.assertEqual(record['before_sha256'], item['before_sha256'])
                self.assertEqual(record['after_sha256'], item['after_sha256'])
                self.assertEqual(record['source_ids'], item['source_ids'])
                self.assertEqual(record['source_checks'], review['source_checks'])
                self.assertEqual(record['limits'], review['limits'])
                self.assertEqual(runtime_item['limits'], review['limits'][0])
                self.assertEqual(record['status'], 'ai_source_rechecked_professional_pending')
                self.assertEqual(record['review_path'], review_path)
                self.assertEqual(
                    {self.sources[source_id]['url'] for source_id in item['source_ids']},
                    {check['url'] for check in review['source_checks']},
                )

                prior_body = subprocess.check_output(
                    ['git', 'show', item['prior_body_git_ref']], cwd=ROOT
                )
                prior_review = subprocess.check_output(
                    ['git', 'show', item['prior_review_git_ref']], cwd=ROOT
                )
                self.assertEqual(hashlib.sha256(prior_body).hexdigest(), item['before_sha256'])
                self.assertEqual(hashlib.sha256(prior_review).hexdigest(), item['prior_review_sha256'])
                validate_recheck_history(ROOT, record, runtime_item)

    def test_sources_are_additive_and_retired_objects_are_preserved(self):
        previous_runtime = old('localization/tw-edition/runtime.json')
        previous_sources = {source['id']: source for source in previous_runtime['sources']}
        runtime_ids = [source['id'] for source in self.runtime['sources']]
        previous_ids = list(previous_sources)
        self.assertEqual(runtime_ids[:len(previous_ids)], previous_ids)
        for source_id, source in previous_sources.items():
            self.assertEqual(self.sources[source_id], source)

        added = {source['id']: source for source in self.evidence['sources_added']}
        self.assertEqual(set(added), NEW_SOURCE_IDS)
        actual_added = set(runtime_ids) - set(previous_ids)
        self.assertTrue(NEW_SOURCE_IDS.issubset(actual_added))
        catalog_path = 'localization/tw-edition/sources/ch01-critical-medical-food-recheck-20261027.json'
        catalog = read(catalog_path)
        rows = {row[0]: row for row in catalog['sources']}
        self.assertEqual(set(rows), NEW_SOURCE_IDS)
        for source_id in NEW_SOURCE_IDS:
            self.assertEqual(self.sources[source_id], added[source_id])
            self.assertEqual(rows[source_id][2], added[source_id]['url'])

        reused_id = 'ch01_crisis_mohw_1925_2026'
        self.assertIn(reused_id, self.sources)
        self.assertEqual(self.sources[reused_id], previous_sources[reused_id])
        retired = self.evidence['sources_retired']
        self.assertEqual({source['id'] for source in retired}, {
            'ch01_cdc_tetanus_counts', 'ch01_af_chao_pubmed', 'ch01_af_chao_manuscript'
        })
        for source in retired:
            self.assertTrue(source['current_source_object_unchanged'])
            self.assertEqual(self.sources[source['id']], previous_sources[source['id']])
            recorded = self.records[source['article_id']]['retired_sources']
            self.assertIn(source['id'], {entry['id'] for entry in recorded})

    def test_frequency_evidence_preserves_measure_and_denominator_limits(self):
        stats = {stat['id']: stat for stat in self.evidence['statistics']}
        expected = {
            'tetanus_confirmed_cases_2025_tw': (3, 3, None, '2025全年'),
            'tetanus_confirmed_cases_2026_through_week43_tw': (4, 4, None, '2026年截至第43週；頁面日期上限2026-10-31'),
            'suicide_death_count_2025_tw': (3951, 3951, None, '2025（民國114年）'),
            'suicide_crude_death_rate_2025_tw': (16.9, 3951, None, '2025（民國114年）'),
            'suicide_age_standardized_death_rate_2025_tw': (12.9, 3951, None, '2025（民國114年）'),
            'af_new_diagnoses_2021_tw': (32817, 32817, None, '2021年'),
            'af_incidence_rate_2021_tw': (169.06, 32817, None, '2021年'),
            'af_standardized_incidence_2021_tw': (112.38, 32817, None, '2021年'),
            'bongkrekic_sample_2024_tw': (0, 0, 110, '2024-05-20啟動至2024-08-16公告'),
            'bongkrekic_sample_2026_taipei': (0, 0, 50, '2026-09-14公告之115年度抽驗'),
        }
        self.assertEqual(set(stats), set(expected))
        for stat_id, (value, numerator, denominator, period) in expected.items():
            with self.subTest(stat=stat_id):
                stat = stats[stat_id]
                self.assertEqual(stat['value'], value)
                self.assertEqual(stat['numerator'], numerator)
                self.assertEqual(stat['denominator'], denominator)
                self.assertEqual(stat['period'], period)
                self.assertTrue(stat['geography'])
                self.assertTrue(stat['population'])
                self.assertTrue(stat['event_definition'])
                self.assertTrue(stat['data_type'])
                self.assertTrue(stat['method'])
                self.assertEqual(stat['source_accessed_at'], '2026-10-27')
                self.assertTrue(stat['limitations'])
        self.assertIn('不能計算受傷後感染率', stats['tetanus_confirmed_cases_2025_tw']['denominator_description'])
        self.assertIn('晚於查閱日', stats['tetanus_confirmed_cases_2026_through_week43_tw']['denominator_description'])
        self.assertIn('不是自傷意念', stats['suicide_death_count_2025_tw']['denominator_description'])
        self.assertIn('未列總人年', stats['af_incidence_rate_2021_tw']['denominator_description'])
        self.assertIn('非全國', stats['bongkrekic_sample_2026_taipei']['denominator_description'])

    def test_articles_keep_safe_actions_and_professional_limits(self):
        bodies = {item_id: self.items[item_id]['body'] for item_id in ITEM_IDS}
        self.assertIn('仍插在身體的深部異物不要自行拔出', bodies['TW-01-015'])
        self.assertIn('不把表格改寫成民眾自用決策表', bodies['TW-01-015'])
        self.assertIn('先撥119', bodies['TW-01-032'])
        self.assertIn('1925安心專線', bodies['TW-01-032'])
        self.assertIn('不是自傷意念盛行率', bodies['TW-01-032'])
        self.assertIn('突然臉歪、單側無力、說話不清', bodies['TW-01-044'])
        self.assertIn('不要自行買來預防', bodies['TW-01-044'])
        self.assertIn('7°C以下', bodies['TW-01-048'])
        self.assertIn('不能換算成汙染盛行率或個人中毒機率', bodies['TW-01-048'])
        for item_id in ITEM_IDS:
            review = read(f'localization/reviews/{item_id}.json')
            self.assertIn('非醫療', review['reviewer'])
            self.assertEqual(self.records[item_id]['status'], 'ai_source_rechecked_professional_pending')


if __name__ == '__main__':
    unittest.main()

"""第1章四篇疫苗與傳染病預防高風險歷史再審契約。"""
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

BASE = '1f41c8175518ebadf01ba72f5f17566eed2e39b4'
EVIDENCE_PATH = 'localization/ch01-vaccine-prevention-recheck-20261027.json'
ITEM_IDS = {'TW-01-014', 'TW-01-016', 'TW-01-020', 'TW-01-022'}
NEW_SOURCE_IDS = {
    'ch01_mohw_hepatitis_prevention_20260728',
    'ch01_hpa_hpv_115_schedule_20261027',
    'ch01_cdc_flu_surveillance_20261020',
    'ch01_cdc_ipd_nidss_20261027',
}
RETIRED_SOURCE_IDS = {'ch01_flu_update_20261013', 'ch01_ipd_surveillance_2025'}


def read(path):
    return load_json(ROOT / path)


def old(path):
    return json.loads(subprocess.check_output(['git', 'show', f'{BASE}:{path}'], cwd=ROOT, text=True))


class Ch01VaccinePreventionRecheckTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.evidence = read(EVIDENCE_PATH)
        cls.runtime = validate_runtime()
        cls.items = {item['id']: item for item in cls.runtime['items']}
        cls.sources = {source['id']: source for source in cls.runtime['sources']}
        cls.manifest = {item['id']: item for item in read('localization/manifest.json')['entries']}
        cls.register = read('localization/retroactive-review-register-20261019.json')
        cls.rows = cls.register['substantive_rechecks']
        cls.base_rows = old('localization/retroactive-review-register-20261019.json')['substantive_rechecks']
        cls.new_records = {
            item_id: [row for row in cls.rows if row['id'] == item_id and row.get('reviewed_at') == '2026-10-27']
            for item_id in ITEM_IDS
        }
        cls.evidence_items = {item['id']: item for item in cls.evidence['items']}

    def test_batch_progress_and_publication_boundary(self):
        coverage = read('localization/tw-edition/coverage.json')
        self.assertEqual(self.evidence['base_main_sha'], BASE)
        self.assertEqual(self.evidence['new_core_entries'], [])
        self.assertEqual({item['id'] for item in self.evidence['items']}, ITEM_IDS)
        self.assertEqual(self.evidence['counts_before']['core_completed'], 278)
        self.assertEqual(self.evidence['counts_after']['core_completed'], 278)
        self.assertEqual(self.evidence['counts_after']['core_total'], 765)
        self.assertEqual(self.evidence['counts_before']['substantive_rechecks'], 206)
        self.assertEqual(self.evidence['counts_after']['substantive_rechecks'], 210)
        self.assertEqual(self.evidence['counts_after']['substantive_rechecks'], 206 + len(ITEM_IDS))
        self.assertEqual(self.evidence['counts_before']['runtime_sources'], 827)
        self.assertEqual(self.evidence['counts_after']['runtime_sources'], 831)
        self.assertEqual(self.evidence['counts_before']['source_registry'], 908)
        self.assertEqual(self.evidence['counts_after']['source_registry'], 912)
        self.assertEqual(self.evidence['counts_before']['json_files_checked'], 477)
        self.assertEqual(self.evidence['counts_after']['json_files_checked'], 479)
        self.assertEqual(coverage['json_files_checked'], 479)
        self.assertEqual(coverage['registry_sources'], 912)
        self.assertEqual(coverage['unique_draft_entries'], 498)
        self.assertEqual(coverage['entries_without_any_draft'], 267)
        self.assertFalse(self.evidence['publication_ready'])
        self.assertFalse(self.evidence['counts_after']['publication_ready'])
        self.assertEqual(len(self.rows), 210)
        self.assertEqual(len(self.rows), len(self.base_rows) + len(ITEM_IDS))
        self.assertEqual(self.rows[:len(self.base_rows)], self.base_rows)
        self.assertEqual(len(self.evidence['items']), len(ITEM_IDS))

    def test_body_review_manifest_runtime_and_append_only_register_are_synchronized(self):
        for item_id in ITEM_IDS:
            with self.subTest(item=item_id):
                evidence_item = self.evidence_items[item_id]
                runtime_item = self.items[item_id]
                manifest_item = self.manifest[item_id]
                review_path = f'localization/reviews/{item_id}.json'
                review = read(review_path)
                body = (ROOT / manifest_item['target_path']).read_bytes()
                body_text = body.decode('utf-8')
                body_hash = hashlib.sha256(body).hexdigest()
                title = next(line[2:] for line in body_text.splitlines() if line.startswith('# '))
                self.assertEqual(body_hash, evidence_item['after_sha256'])
                self.assertEqual(body_hash, review['target_sha256'])
                self.assertEqual(body_hash, runtime_item['body'] and hashlib.sha256(runtime_item['body'].encode('utf-8')).hexdigest())
                self.assertEqual(body_text, runtime_item['body'])
                self.assertEqual(title, runtime_item['title'])
                self.assertIn('source_title_zh_tw', manifest_item)  # 原作標題與臺灣正式標題是兩個不同欄位。
                self.assertEqual(manifest_item['target_path'], review['target_path'])
                self.assertEqual(manifest_item['sources'], evidence_item['source_ids'])
                self.assertEqual(runtime_item['source_ids'], evidence_item['source_ids'])
                self.assertEqual(manifest_item['verified_at'], '2026-10-27')
                self.assertEqual(review['reviewed_at'], '2026-10-27')
                self.assertEqual(review['review_due_at'], evidence_item['review_due_at'])
                self.assertEqual(runtime_item['review_due_at'], evidence_item['review_due_at'])
                self.assertEqual(runtime_item['review_status'], 'source_checked')
                self.assertEqual(len(self.new_records[item_id]), 1)
                record = self.new_records[item_id][0]
                self.assertEqual(record['before_sha256'], evidence_item['before_sha256'])
                self.assertEqual(record['after_sha256'], evidence_item['after_sha256'])
                self.assertEqual(record['prior_review_sha256'], evidence_item['prior_review_sha256'])
                self.assertEqual(record['review_due_at'], evidence_item['review_due_at'])
                self.assertEqual(record['prior_revision'], BASE)
                self.assertEqual(record['source_ids'], evidence_item['source_ids'])
                self.assertEqual(record['reviewed_at'], '2026-10-27')
                self.assertEqual(record['status'], 'ai_source_rechecked_professional_pending')
                self.assertEqual(record['source_checks'], review['source_checks'])
                self.assertEqual(record['limits'], review['limits'])
                old_body = subprocess.check_output(['git', 'show', evidence_item['prior_body_git_ref']], cwd=ROOT)
                old_review = subprocess.check_output(['git', 'show', evidence_item['prior_review_git_ref']], cwd=ROOT)
                self.assertEqual(hashlib.sha256(old_body).hexdigest(), evidence_item['before_sha256'])
                self.assertEqual(hashlib.sha256(old_review).hexdigest(), evidence_item['prior_review_sha256'])
                # The previous review event is preserved ahead of this new append-only event.
                prior_rows = [row for row in self.rows if row['id'] == item_id and row.get('reviewed_at') != '2026-10-27']
                expected_prior_rows = [row for row in self.base_rows if row['id'] == item_id]
                self.assertEqual(prior_rows, expected_prior_rows)
                validate_recheck_history(ROOT, record, runtime_item)

    def test_sources_are_additive_and_stale_article_citations_are_retired_with_history(self):
        previous = old('localization/tw-edition/runtime.json')['sources']
        previous_ids = [source['id'] for source in previous]
        current_ids = [source['id'] for source in self.runtime['sources']]
        self.assertEqual(current_ids[:len(previous_ids)], previous_ids)
        self.assertEqual(set(current_ids[len(previous_ids):]), NEW_SOURCE_IDS)
        for source in previous:
            self.assertEqual(self.sources[source['id']], source)
        evidence_added = {source['id']: source for source in self.evidence['sources_added']}
        self.assertEqual(set(evidence_added), NEW_SOURCE_IDS)
        catalog = read('localization/tw-edition/sources/ch01-vaccine-prevention-recheck-20261027.json')
        catalog_rows = {row[0]: row for row in catalog['sources']}
        self.assertEqual(set(catalog_rows), NEW_SOURCE_IDS)
        self.assertEqual([row[0] for row in catalog['sources']], [source['id'] for source in self.evidence['sources_added']])
        for source_id in NEW_SOURCE_IDS:
            source = self.sources[source_id]
            self.assertEqual(source, evidence_added[source_id])
            self.assertEqual(catalog_rows[source_id][2], source['url'])
            self.assertGreater(len(source['retrieval_method']), 20)
        self.assertEqual({item['id'] for item in self.evidence['sources_retired']}, RETIRED_SOURCE_IDS)
        for retired in self.evidence['sources_retired']:
            old_source = next(source for source in previous if source['id'] == retired['id'])
            self.assertEqual(self.sources[retired['id']], old_source)
            self.assertEqual(hashlib.sha256(json.dumps(old_source, ensure_ascii=False, sort_keys=True).encode()).hexdigest(), retired['prior_source_sha256'])
            self.assertTrue(retired['preserved_in_runtime'])
        for item_id in ['TW-01-020', 'TW-01-022']:
            record = self.new_records[item_id][0]
            self.assertEqual(len(record['retired_sources']), 1)
            self.assertIn(record['retired_sources'][0]['id'], RETIRED_SOURCE_IDS)

    def test_frequency_records_retain_period_population_event_and_denominator_limits(self):
        stats = {stat['id']: stat for stat in self.evidence['statistics']}
        self.assertEqual(len(stats), 9)
        for stat in stats.values():
            for field in ['value', 'unit', 'period', 'geography', 'population', 'numerator', 'denominator', 'denominator_description', 'event_definition', 'data_type', 'method', 'source_accessed_at', 'limitations']:
                self.assertIn(field, stat)
            self.assertTrue(stat['period'])
            self.assertTrue(stat['event_definition'])
            self.assertTrue(stat['limitations'])
        hbv = stats['hepatitis_b_reported_positive_rate_40_79_2011_2026']
        self.assertEqual(hbv['value'], 8.5)
        self.assertIsNone(hbv['numerator'])
        self.assertIsNone(hbv['denominator'])
        self.assertIn('15.6%', hbv['period'])
        self.assertIn('沒有列出', hbv['denominator_description'])
        screening = stats['hepatitis_screening_service_users_20260728']
        self.assertEqual(screening['reported_value'], '>7,880,000')
        self.assertIn('不是感染事件', screening['event_definition'])
        cervical = stats['cervical_cancer_registry_2023_taiwan_female']
        self.assertEqual((cervical['numerator'], cervical['value']), (1429, 7.4))
        self.assertEqual(cervical['period'], '2023（民國112年）')
        self.assertIn('不是HPV感染率', cervical['limitations'][0])
        self.assertIsNone(cervical['denominator'])
        self.assertEqual(stats['influenza_ili_visits_week41_2026']['value'], 123820)
        self.assertEqual(stats['influenza_severe_cases_2026_season_to_20261019']['value'], 307)
        self.assertEqual(stats['influenza_deaths_2026_season_to_20261019']['value'], 42)
        self.assertEqual(stats['influenza_vaccine_doses_to_20261019']['value'], 3400000)
        self.assertEqual(stats['ipd_confirmed_cases_2026_to_20261027']['value'], 220)
        self.assertEqual(stats['ipd_deaths_2026_to_20261027']['value'], 27)
        for stat_id in ['influenza_ili_visits_week41_2026','influenza_severe_cases_2026_season_to_20261019','influenza_deaths_2026_season_to_20261019','ipd_confirmed_cases_2026_to_20261027','ipd_deaths_2026_to_20261027']:
            self.assertIsNone(stats[stat_id]['denominator'])
            self.assertTrue(stats[stat_id]['denominator_description'])

    def test_article_wording_uses_current_taiwan_policy_and_does_not_promote_counts_to_risk(self):
        bodies = {item_id: self.items[item_id]['body'] for item_id in ITEM_IDS}
        self.assertIn('15.6%', bodies['TW-01-014'])
        self.assertIn('8.5%', bodies['TW-01-014'])
        self.assertIn('超過788萬', bodies['TW-01-014'])
        self.assertIn('不當成一般人口盛行率或個人感染機率', bodies['TW-01-014'])
        self.assertIn('114年入學國二生接種第1劑', bodies['TW-01-016'])
        self.assertIn('子宮頸癌新發病例', bodies['TW-01-016'])
        self.assertIn('不是HPV感染率', bodies['TW-01-016'])
        self.assertIn('25至29歲女性每3年一次公費抹片', bodies['TW-01-016'])
        self.assertIn('123,820人次', bodies['TW-01-020'])
        self.assertIn('307例', bodies['TW-01-020'])
        self.assertIn('42例', bodies['TW-01-020'])
        self.assertNotIn('1,673', bodies['TW-01-020'])
        self.assertNotIn('334例', bodies['TW-01-020'])
        self.assertIn('220例', bodies['TW-01-022'])
        self.assertIn('死亡27例', bodies['TW-01-022'])
        self.assertNotIn('347例', bodies['TW-01-022'])


if __name__ == '__main__':
    unittest.main()

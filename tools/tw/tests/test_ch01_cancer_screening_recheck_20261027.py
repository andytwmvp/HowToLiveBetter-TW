"""第1章四篇癌症篩檢歷史實質再審資料契約。"""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from reader_copy_test_support import assert_body_version_matches_review_or_cleanup, assert_reader_limits_match_review_or_cleanup
from content_validation import load_json
from retroactive_audit import validate_recheck_history
from review_contract import ROOT, validate_runtime

BASE = 'adec31f28c151587f97481dbd3fd97f96839e0b3'
EVIDENCE_PATH = 'localization/ch01-cancer-screening-recheck-20261027.json'
ITEM_IDS = {'TW-01-017', 'TW-01-018', 'TW-01-019', 'TW-01-024'}
TITLES = {
    'TW-01-017': '乳癌篩檢依臺灣40至74歲公費資格，乳房異常不要等下次檢查',
    'TW-01-018': '子宮頸抹片與HPV檢測分開查資格，異常結果要完成追蹤',
    'TW-01-019': '大腸癌糞便潛血篩檢先查臺灣資格，陽性要接續大腸鏡評估',
    'TW-01-024': '肺癌LDCT依臺灣高風險資格每兩年篩檢，結節追蹤與戒菸另行安排',
}
NEW_SOURCE_IDS = {
    'hpa_breast_screening_service_20260911',
    'hpa_cancer_registry_latest_20261027',
    'hpa_ldct_service_20260828',
    'ch01_cancer_registry_2023_lung',
}


def read(path):
    return load_json(ROOT / path)


def old(path):
    return json.loads(subprocess.check_output(['git', 'show', f'{BASE}:{path}'], cwd=ROOT, text=True))


class Ch01CancerScreeningRecheckTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.evidence = read(EVIDENCE_PATH)
        cls.runtime = validate_runtime()
        cls.items = {item['id']: item for item in cls.runtime['items']}
        cls.sources = {source['id']: source for source in cls.runtime['sources']}
        cls.manifest = {entry['id']: entry for entry in read('localization/manifest.json')['entries']}
        cls.register = read('localization/retroactive-review-register-20261019.json')
        cls.records = {record['id']: record for record in cls.register['substantive_rechecks']}
        cls.evidence_items = {item['id']: item for item in cls.evidence['items']}

    def test_batch_counts_and_publication_boundary(self):
        before, after = self.evidence['counts_before'], self.evidence['counts_after']
        self.assertEqual(self.evidence['base_main_sha'], BASE)
        self.assertEqual(set(self.evidence_items), ITEM_IDS)
        self.assertEqual(self.evidence['new_core_entries'], [])
        self.assertEqual(after['substantive_rechecks'], before['substantive_rechecks'] + 4)
        self.assertEqual(after['runtime_sources'], before['runtime_sources'] + len(NEW_SOURCE_IDS))
        self.assertEqual(after['source_registry'], before['source_registry'] + len(NEW_SOURCE_IDS))
        self.assertEqual(after['json_files_checked'], 473)
        self.assertEqual(after['core_completed'], before['core_completed'])
        self.assertEqual(after['core_total'], 765)
        self.assertEqual(after['shared_reader_items'], before['shared_reader_items'])
        self.assertEqual(after['topics_with_any_content'], before['topics_with_any_content'])
        self.assertEqual(after['topics_without_content'], before['topics_without_content'])
        self.assertEqual(after['unresolved_source_ids'], before['unresolved_source_ids'])
        self.assertEqual(after['unresolved_reference_occurrences'], before['unresolved_reference_occurrences'])
        self.assertFalse(self.evidence['publication_ready'])
        self.assertFalse(read('localization/tw-edition/coverage.json')['publication_ready'])

    def test_runtime_manifest_review_body_and_historical_hashes_align(self):
        for item_id in ITEM_IDS:
            with self.subTest(item=item_id):
                item = self.evidence_items[item_id]
                self.assertEqual(item['title'], TITLES[item_id])
                body = (ROOT / item['target_path']).read_bytes()
                body_hash = hashlib.sha256(body).hexdigest()
                markdown_title = next(line[2:] for line in body.decode('utf-8').splitlines() if line.startswith('# '))
                review_path = f'localization/reviews/{item_id}.json'
                review_raw = (ROOT / review_path).read_bytes()
                review = json.loads(review_raw)
                entry = self.manifest[item_id]
                record = self.records[item_id]
                assert_body_version_matches_review_or_cleanup(self, item_id, item['after_sha256'], body_hash)
                self.assertEqual(body_hash, review['target_sha256'])
                self.assertEqual(item['title'], markdown_title)
                self.assertEqual(self.items[item_id]['title'], markdown_title)
                self.assertEqual(body.decode('utf-8'), self.items[item_id]['body'])
                self.assertEqual(entry['verified_at'], self.evidence['reviewed_at'])
                self.assertEqual(entry['sources'], item['source_ids'])
                self.assertEqual(self.items[item_id]['source_ids'], item['source_ids'])
                self.assertEqual({self.sources[s]['url'] for s in item['source_ids']}, {c['url'] for c in review['source_checks']})
                self.assertEqual(record['before_sha256'], item['before_sha256'])
                self.assertEqual(record['after_sha256'], item['after_sha256'])
                self.assertEqual(record['prior_revision'], BASE)
                self.assertEqual(record['source_ids'], item['source_ids'])
                self.assertEqual(record['reviewed_at'], self.evidence['reviewed_at'])
                self.assertEqual(record['review_due_at'], self.evidence['review_due_at'])
                self.assertEqual(record['status'], 'ai_source_rechecked_professional_pending')
                old_body = subprocess.check_output(['git', 'show', item['prior_body_git_ref']], cwd=ROOT)
                old_review = subprocess.check_output(['git', 'show', item['prior_review_git_ref']], cwd=ROOT)
                self.assertEqual(hashlib.sha256(old_body).hexdigest(), item['before_sha256'])
                self.assertEqual(hashlib.sha256(old_review).hexdigest(), item['prior_review_sha256'])
                self.assertEqual(record['source_checks'], review['source_checks'])
                self.assertEqual(record['limits'], review['limits'])
                assert_reader_limits_match_review_or_cleanup(self, item_id, review['limits'][0])
                validate_recheck_history(ROOT, record, self.items[item_id])

    def test_new_sources_are_additive_and_prior_records_keep_order(self):
        previous = old('localization/tw-edition/runtime.json')['sources']
        previous_ids = [source['id'] for source in previous]
        current_ids = [source['id'] for source in self.runtime['sources']]
        self.assertEqual(current_ids[:len(previous_ids)], previous_ids)
        runtime_added_ids = current_ids[len(previous_ids):]
        self.assertTrue(NEW_SOURCE_IDS.issubset(set(runtime_added_ids)))
        for source in previous:
            self.assertEqual(self.sources[source['id']], source)
        added = {source['id']: source for source in self.evidence['sources_added']}
        self.assertEqual(set(added), NEW_SOURCE_IDS)
        self.assertEqual(set(self.evidence['sources_retired']), set())
        catalog = read('localization/tw-edition/sources/ch01-cancer-screening-recheck-20261027.json')
        rows = {row[0]: row for row in catalog['sources']}
        self.assertEqual(set(rows), NEW_SOURCE_IDS)
        runtime_batch_order = [source_id for source_id in runtime_added_ids if source_id in NEW_SOURCE_IDS]
        self.assertEqual([source['id'] for source in self.evidence['sources_added']], runtime_batch_order)
        self.assertEqual([row[0] for row in catalog['sources']], runtime_batch_order)
        for source_id in NEW_SOURCE_IDS:
            self.assertEqual(self.sources[source_id], added[source_id])
            self.assertEqual(rows[source_id][2], added[source_id]['url'])
            self.assertGreater(len(added[source_id]['retrieval_method']), 20)
        self.assertEqual(self.sources['hpa_ldct_service_20260828']['url'], 'https://www.hpa.gov.tw/Pages/List.aspx?nodeid=4619')
        self.assertIn('應同意接受衛教戒菸', self.sources['hpa_ldct_service_20260828']['supports'])

    def test_frequency_data_keeps_period_population_and_denominator_limits(self):
        stats = {stat['id']: stat for stat in self.evidence['statistics']}
        expected = {
            'breast_cancer_registry_2023_taiwan_female': (17779, 91.2, '每10萬女性；年齡標準化發生率'),
            'cervical_cancer_registry_2023_taiwan_female': (1429, 7.4, '每10萬女性；年齡標準化發生率'),
            'colorectal_cancer_registry_2023_taiwan_all': (19074, 43.1, '每10萬人口；年齡標準化發生率'),
            'lung_cancer_registry_2023_taiwan_all': (19986, 44.9, '每10萬人口；年齡標準化發生率'),
        }
        for key, (numerator, value, unit) in expected.items():
            with self.subTest(stat=key):
                stat = stats[key]
                self.assertEqual(stat['period'], '2023（民國112年）')
                self.assertEqual(stat['geography'], '臺灣全國')
                self.assertEqual(stat['numerator'], numerator)
                self.assertIsNone(stat['denominator'])
                self.assertEqual(stat['value'], value)
                self.assertEqual(stat['unit'], unit)
                self.assertEqual(stat['source_accessed_at'], '2026-10-19')
                self.assertEqual(stat['date_reconfirmed_in_index'], '2026-10-27')
                self.assertIn('不含原位癌', stat['event_definition'])
                self.assertIn('2000年世界標準人口', stat['denominator_description'])
                self.assertTrue(stat['limitations'])
        ldct = stats['ldct_screening_program_2022_2025']
        self.assertEqual((ldct['numerator'], ldct['denominator']), (3139, 277306))
        self.assertIn('可能包含同一人多次', ldct['denominator_description'])
        self.assertIn('不可將分子除以人次', ldct['method'])
        self.assertEqual(self.evidence['policy_dates'][0]['published_at'], '2026-10-08')
        self.assertEqual(self.evidence['policy_dates'][0]['effective_at'], '2027-01-01')
        self.assertIn('尚未生效', self.evidence['policy_dates'][0]['status'])

    def test_article_changes_state_current_taiwan_screening_rules(self):
        bodies = {key: self.items[key]['body'] for key in ITEM_IDS}
        self.assertIn('40至74歲女性每2年一次', bodies['TW-01-017'])
        self.assertIn('2023年登記有公布落差', bodies['TW-01-017'])
        self.assertIn('2027-01-01生效', bodies['TW-01-018'])
        self.assertIn('2026年仍依現行', bodies['TW-01-018'])
        self.assertIn('45至74歲', bodies['TW-01-019'])
        self.assertIn('40至44歲', bodies['TW-01-019'])
        self.assertIn('檢查年度減出生年', bodies['TW-01-024'])
        self.assertIn('女性年差40至75、男性45至75', bodies['TW-01-024'])
        self.assertIn('年差50至75', bodies['TW-01-024'])
        self.assertIn('同意接受衛教戒菸', bodies['TW-01-024'])
        self.assertIn('兩次檢查的間隔以檢查年度相差至少2年', bodies['TW-01-024'])
        self.assertIn('咳血', bodies['TW-01-024'])
        self.assertIn('19,986例', bodies['TW-01-024'])


if __name__ == '__main__':
    unittest.main()

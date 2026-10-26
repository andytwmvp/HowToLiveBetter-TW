"""第23章教育、健康與教育報酬四篇歷史再審資料契約。"""
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

BASE = '0d0c4304fe6730c2e0e14834618c2bdb6e43f536'
EVIDENCE_PATH = 'localization/ch23-education-outcomes-recheck-20261027.json'
ITEM_IDS = {'TW-23-002', 'TW-23-003', 'TW-23-006', 'TW-23-007'}
NEW_SOURCE_IDS = {
    'ch23_taiwan_elder_mortality_2011',
    'ch23_mol_initial_salary_114',
    'ch23_returns_wb_wps8402_pdf',
    'ch23_returns_causal_meta_2026',
    'ch23_returns_comment_2026',
    'ch23_returns_tw_schooling_2020',
    'ch23_moi_education_2025_pdf',
}


def read(path):
    return load_json(ROOT / path)


def old(path):
    return json.loads(subprocess.check_output(['git', 'show', f'{BASE}:{path}'], cwd=ROOT, text=True))


class Ch23EducationOutcomesRecheckTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.evidence = read(EVIDENCE_PATH)
        cls.runtime = validate_runtime()
        cls.items = {entry['id']: entry for entry in cls.runtime['items']}
        cls.sources = {source['id']: source for source in cls.runtime['sources']}
        cls.register = read('localization/retroactive-review-register-20261019.json')
        cls.records = {record['id']: record for record in cls.register['substantive_rechecks']}
        cls.evidence_items = {item['id']: item for item in cls.evidence['items']}

    def test_batch_identity_counts_and_publication_boundary(self):
        self.assertEqual(self.evidence['base_main_sha'], BASE)
        self.assertEqual(self.evidence['new_core_entries'], [])
        self.assertEqual({item['id'] for item in self.evidence['items']}, ITEM_IDS)
        self.assertEqual(self.evidence['counts_before']['substantive_rechecks'], 186)
        self.assertEqual(self.evidence['counts_after']['substantive_rechecks'], 190)
        self.assertEqual(self.evidence['counts_after']['substantive_rechecks'], self.evidence['counts_before']['substantive_rechecks'] + 4)
        self.assertEqual(self.evidence['counts_after']['runtime_sources'], self.evidence['counts_before']['runtime_sources'] + len(NEW_SOURCE_IDS))
        self.assertEqual(self.evidence['counts_after']['source_registry'], self.evidence['counts_before']['source_registry'] + len(NEW_SOURCE_IDS))
        self.assertEqual(self.evidence['counts_after']['json_files_checked'], self.evidence['counts_before']['json_files_checked'] + 1)
        self.assertEqual(self.evidence['counts_after']['core_completed'], self.evidence['counts_before']['core_completed'])
        self.assertFalse(self.evidence['publication_ready'])
        self.assertFalse(read('localization/tw-edition/coverage.json')['publication_ready'])

    def test_body_manifest_runtime_review_and_historical_hashes_align(self):
        manifest = {entry['id']: entry for entry in read('localization/manifest.json')['entries']}
        for item_id in ITEM_IDS:
            with self.subTest(item=item_id):
                item = self.evidence_items[item_id]
                path = item['target_path']
                body_bytes = (ROOT / path).read_bytes()
                body_sha = hashlib.sha256(body_bytes).hexdigest()
                review_path = f'localization/reviews/{item_id}.json'
                review_bytes = (ROOT / review_path).read_bytes()
                review = json.loads(review_bytes)
                entry = manifest[item_id]
                record = self.records[item_id]
                self.assertEqual(body_sha, item['after_sha256'])
                self.assertEqual(body_sha, review['target_sha256'])
                self.assertEqual(body_bytes.decode(), self.items[item_id]['body'])
                self.assertEqual(entry['verified_at'], self.evidence['reviewed_at'])
                self.assertEqual(set(entry['sources']), {self.sources[source_id]['url'] for source_id in item['source_ids']})
                self.assertEqual(record['before_sha256'], item['before_sha256'])
                self.assertEqual(record['after_sha256'], item['after_sha256'])
                self.assertEqual(record['prior_revision'], BASE)
                self.assertEqual(record['source_ids'], item['source_ids'])
                self.assertEqual(record['reviewed_at'], self.evidence['reviewed_at'])
                self.assertEqual(record['review_due_at'], self.evidence['review_due_at'])
                self.assertEqual(record['status'], 'ai_source_rechecked_professional_pending')
                prior_body = subprocess.check_output(['git', 'show', item['prior_body_git_ref']], cwd=ROOT)
                prior_review = subprocess.check_output(['git', 'show', item['prior_review_git_ref']], cwd=ROOT)
                self.assertEqual(hashlib.sha256(prior_body).hexdigest(), item['before_sha256'])
                self.assertEqual(hashlib.sha256(prior_review).hexdigest(), item['prior_review_sha256'])
                self.assertEqual(review['reviewed_at'], self.evidence['reviewed_at'])
                self.assertEqual(review['review_due_at'], self.evidence['review_due_at'])
                self.assertEqual(record['limits'], review['limits'])
                self.assertEqual(self.items[item_id]['limits'], review['limits'][0])
                validate_recheck_history(ROOT, record, self.items[item_id])
                self.assertTrue(review['source_checks'])
                self.assertTrue(record['limits'])

    def test_sources_are_additive_and_preserve_prior_source_records(self):
        prior_runtime = {source['id']: source for source in old('localization/tw-edition/runtime.json')['sources']}
        prior_registry = {row[0]: row for row in old('localization/tw-edition/sources/16-skills.json')['sources']}
        registry_rows = {row[0]: row for row in read('localization/tw-edition/sources/16-skills.json')['sources']}
        evidence_sources = {source['id']: source for source in self.evidence['sources_added']}
        self.assertEqual(set(evidence_sources), NEW_SOURCE_IDS)
        self.assertEqual(self.evidence['sources_retired'], [])
        self.assertTrue(set(prior_runtime).issubset(self.sources))
        for source_id, previous in prior_runtime.items():
            self.assertEqual(self.sources[source_id], previous)
        self.assertEqual(set(registry_rows), set(prior_registry) | NEW_SOURCE_IDS)
        self.assertEqual(set(self.sources), set(prior_runtime) | NEW_SOURCE_IDS)
        for source_id, source in evidence_sources.items():
            self.assertEqual(self.sources[source_id], source)
            self.assertEqual(registry_rows[source_id][2], source['url'])
            self.assertGreater(len(source['retrieval_method']), 20)

    def test_mortality_estimates_keep_outcome_and_population_scope(self):
        stats = {stat['id']: stat for stat in self.evidence['statistics']}
        meta = stats['education_mortality_global_meta']
        self.assertEqual(meta['source_id'], 'ch23_mortality')
        self.assertEqual(meta['value'], 1.9)
        self.assertEqual(meta['numerator'], None)
        self.assertEqual(meta['denominator'], None)
        self.assertEqual(meta['observations'], 10355)
        self.assertIn('不是樣本參與者人數', meta['limitations'])
        taiwan = stats['education_mortality_taiwan_elder_cohort']
        self.assertEqual(taiwan['source_id'], 'ch23_taiwan_elder_mortality_2011')
        self.assertEqual(taiwan['sample_size'], 4049)
        self.assertEqual(taiwan['numerator'], None)
        self.assertEqual(taiwan['denominator'], None)
        body = self.items['TW-23-002']['body']
        for phrase in ('1.9%', '1.8%至2.0%', '10,355筆觀察值，不是10,355名參與者', '4,049名老人', '1989至2003年', '不具統計顯著性', '不能當成個人的發生機率'):
            self.assertIn(phrase, body)

    def test_education_and_salary_statistics_record_denominators_and_selection_limits(self):
        stats = {stat['id']: stat for stat in self.evidence['statistics']}
        edu = stats['registered_population_education_2025']
        self.assertEqual((edu['numerator'], edu['denominator']), (10602000, 20617000))
        self.assertEqual(edu['value'], 51.4)
        age_group = stats['registered_population_education_age_25_34_2025']
        self.assertEqual(age_group['value'], 81.9)
        self.assertIsNone(age_group['numerator'])
        self.assertIsNone(age_group['denominator'])
        self.assertIn('官方報告未刊出此年齡組人數與分母', age_group['limitations'])
        wage = stats['initial_full_time_employee_salary_2025']
        self.assertEqual(wage['population_count'], 138000)
        self.assertIn('描述統計，不是教育造成的薪資因果效果', wage['limitations'])
        self.assertIn('薪資中位數依級距中點估算', wage['limitations'])
        body = self.items['TW-23-003']['body']
        self.assertIn('10,602,000', body)
        self.assertIn('20,617,000', body)
        self.assertIn('25至34歲', body)
        salary_body = self.items['TW-23-006']['body']
        for phrase in ('13.8萬', '平均月薪3.9萬元', '中位數3.6萬元', '大學畢業者平均3.6萬元', '研究所平均5.3萬元', '17.2%', '不是教育造成的薪資因果效果'):
            self.assertIn(phrase, salary_body)

    def test_education_return_debate_and_taiwan_reform_estimate_are_not_overclaimed(self):
        stats = {stat['id']: stat for stat in self.evidence['statistics']}
        meta = stats['causal_schooling_returns_2026_meta']
        self.assertEqual(meta['source_id'], 'ch23_returns_causal_meta_2026')
        self.assertEqual((meta['papers'], meta['estimates'], meta['reforms']), (53, 79, 46))
        self.assertEqual((meta['unweighted_mean'], meta['random_effects_weighted'], meta['fixed_effects_weighted']), (8.2, 6.0, 6.2))
        comment = stats['causal_schooling_returns_2026_comment']
        self.assertEqual(comment['source_id'], 'ch23_returns_comment_2026')
        self.assertEqual(comment['estimated_range'], '5%–6%')
        taiwan = stats['schooling_returns_taiwan_1968_reform']
        self.assertEqual(taiwan['source_id'], 'ch23_returns_tw_schooling_2020')
        self.assertEqual(taiwan['estimate'], 5.6)
        self.assertIn('1955年出生界線', taiwan['limitations'])
        self.assertIn('不代表2026年所有升學、科系或短期課程', taiwan['limitations'])
        body = self.items['TW-23-007']['body']
        for phrase in ('8.2%', '6.0%', '6.2%', '0%至3%', '5%至6%', '5.6%', '1955年出生界線', '不同修正方法仍有爭議', '短期課程'):
            self.assertIn(phrase, body)


if __name__ == '__main__':
    unittest.main()

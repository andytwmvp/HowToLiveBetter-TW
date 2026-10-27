"""第23章招生、技能、職缺薪資與會計資格四篇歷史再審契約。"""
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

BASE = 'eda74bc4428cff38e3e41cd1c680dd7bc50792c6'
EVIDENCE_PATH = 'localization/ch23-job-credentials-recheck-20261027.json'
ITEM_IDS = {'TW-23-005', 'TW-23-011', 'TW-23-012', 'TW-23-021'}
NEW_SOURCE_IDS = {
    'ch23_admission_116_portal_20261027',
    'ch23_admission_116_choices_20260803',
    'ch23_skill_cooking_qualification_20260722',
    'ch23_vacancies_11506_recheck_20261027',
    'ch23_salary_114_recheck_20261027',
    'ch23_cpa_act_20260805',
    'ch23_cpa_act_amendment_20260805',
    'ch23_taiwanjobs_job_search_20261027',
}


def read(path):
    return load_json(ROOT / path)


def old(path):
    return json.loads(subprocess.check_output(['git', 'show', f'{BASE}:{path}'], cwd=ROOT, text=True))


class Ch23JobCredentialsRecheckTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.evidence = read(EVIDENCE_PATH)
        cls.runtime = validate_runtime()
        cls.items = {entry['id']: entry for entry in cls.runtime['items']}
        cls.sources = {source['id']: source for source in cls.runtime['sources']}
        cls.register = read('localization/retroactive-review-register-20261019.json')
        cls.records = {record['id']: record for record in cls.register['substantive_rechecks']}
        cls.evidence_items = {item['id']: item for item in cls.evidence['items']}

    def test_batch_counts_and_publication_boundary(self):
        coverage = read('localization/tw-edition/coverage.json')
        self.assertEqual(self.evidence['base_main_sha'], BASE)
        self.assertEqual(self.evidence['new_core_entries'], [])
        self.assertEqual({item['id'] for item in self.evidence['items']}, ITEM_IDS)
        self.assertEqual(self.evidence['counts_before']['substantive_rechecks'], 198)
        self.assertEqual(self.evidence['counts_after']['substantive_rechecks'], 202)
        self.assertEqual(self.evidence['counts_after']['substantive_rechecks'], self.evidence['counts_before']['substantive_rechecks'] + 4)
        self.assertEqual(self.evidence['counts_after']['runtime_sources'], self.evidence['counts_before']['runtime_sources'] + len(NEW_SOURCE_IDS))
        self.assertEqual(self.evidence['counts_after']['source_registry'], self.evidence['counts_before']['source_registry'] + len(NEW_SOURCE_IDS))
        self.assertEqual(self.evidence['counts_after']['json_files_checked'], self.evidence['counts_before']['json_files_checked'] + 1)
        # This evidence is an immutable snapshot; later batches can add files and sources.
        self.assertGreaterEqual(coverage['json_files_checked'], self.evidence['counts_after']['json_files_checked'])
        self.assertGreaterEqual(coverage['registry_sources'], self.evidence['counts_after']['source_registry'])
        self.assertEqual(coverage['unique_draft_entries'], 498)
        self.assertEqual(self.evidence['counts_after']['core_completed'], self.evidence['counts_before']['core_completed'])
        self.assertEqual(coverage['publication_completed_entries'], 278)
        self.assertEqual(coverage['publication_total_entries'], 765)
        self.assertEqual(len(coverage['unresolved_source_ids']), 115)
        self.assertEqual(coverage['unresolved_reference_occurrences'], 306)
        self.assertFalse(self.evidence['publication_ready'])
        self.assertFalse(coverage['publication_ready'])

    def test_body_runtime_manifest_reviews_and_historical_hashes_align(self):
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
                record = self.records[item_id]
                entry = manifest[item_id]
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

    def test_sources_are_additive_and_prior_records_unchanged(self):
        prior_runtime = {source['id']: source for source in old('localization/tw-edition/runtime.json')['sources']}
        prior_registry = {row[0]: row for row in old('localization/tw-edition/sources/16-skills.json')['sources']}
        registry_rows = {row[0]: row for row in read('localization/tw-edition/sources/16-skills.json')['sources']}
        evidence_sources = {source['id']: source for source in self.evidence['sources_added']}
        self.assertEqual(set(evidence_sources), NEW_SOURCE_IDS)
        retired = self.evidence['sources_retired']
        self.assertEqual({row['id'] for row in retired}, {'ch23_admission', 'ch23_vacancies', 'ch23_salary'})
        self.assertTrue(set(prior_runtime).issubset(self.sources))
        for source_id, previous in prior_runtime.items():
            self.assertEqual(self.sources[source_id], previous)
        self.assertTrue(set(prior_registry).issubset(registry_rows))
        for source_id, previous in prior_registry.items():
            with self.subTest(prior_registry_source=source_id):
                self.assertEqual(registry_rows[source_id], previous)
        self.assertTrue((set(prior_runtime) | NEW_SOURCE_IDS).issubset(self.sources))
        for row in retired:
            with self.subTest(retired_source=row['id']):
                prior_source = prior_runtime[row['id']]
                digest = hashlib.sha256(json.dumps(prior_source, ensure_ascii=False, sort_keys=True).encode('utf-8')).hexdigest()
                self.assertTrue(row['preserved_in_runtime'])
                self.assertEqual(row['prior_source_sha256'], digest)
                self.assertEqual(self.sources[row['id']], prior_source)
                replacements = set(row['replacement_ids'])
                self.assertTrue(replacements)
                register_record = next(
                    record for record in self.records.values()
                    if any(retired_record['id'] == row['id'] for retired_record in record.get('retired_sources', []))
                )
                register_retired = next(value for value in register_record['retired_sources'] if value['id'] == row['id'])
                self.assertEqual(register_retired['prior_source_sha256'], row['prior_source_sha256'])
                self.assertEqual(register_retired['replacement_ids'], row['replacement_ids'])
                self.assertEqual(register_retired['reason'], row['reason'])
                current_item = self.items[register_record['id']]
                self.assertNotIn(row['id'], current_item['source_ids'])
                self.assertTrue(replacements.issubset(set(current_item['source_ids'])))
        for source_id, source in evidence_sources.items():
            with self.subTest(source=source_id):
                self.assertEqual(self.sources[source_id], source)
                self.assertEqual(registry_rows[source_id][1], source['title'])
                self.assertEqual(registry_rows[source_id][2], source['url'])
                self.assertEqual(registry_rows[source_id][3], source['supports'])
                self.assertGreater(len(source['retrieval_method']), 20)

    def test_vacancy_and_salary_statistics_record_scope_denominator_and_limits(self):
        stats = {stat['id']: stat for stat in self.evidence['statistics']}
        vacancies = stats['vacancies_2026q2_national']
        self.assertEqual((vacancies['value'], vacancies['numerator'], vacancies['denominator']), (296143, 296143, None))
        self.assertEqual((vacancies['sample_size'], vacancies['accessed_at']), (4004, '2026-10-27'))
        self.assertEqual(vacancies['period'], '115年6月底')
        self.assertIn('職缺', vacancies['event_definition'])
        self.assertIn('工業及服務業', vacancies['population'])
        self.assertIn('不是求職者', ' '.join(vacancies['limitations']))
        rate = stats['vacancy_rate_2026q2_national']
        self.assertEqual((rate['value'], rate['numerator'], rate['denominator']), (3.3, 296143, 8880825))
        self.assertIn('8,584,682', rate['denominator_definition'])
        self.assertIn('不是求職者', ' '.join(rate['limitations']))
        duration = stats['recruitment_time_2026q2_full_time']
        self.assertEqual((duration['value'], duration['unit'], duration['sample_size']), (3.1, '月（全時職缺平均）', 4004))
        salary = stats['occupational_salary_survey_2025']
        self.assertEqual((salary['sample_size'], salary['numerator'], salary['denominator']), (9977, None, None))
        self.assertEqual(salary['unit'], '家有效事業單位樣本')
        self.assertIn('不是9,977名員工', ' '.join(salary['limitations']))
        body = self.items['TW-23-012']['body']
        for phrase in ('296,143個職缺', '8,584,682人', '4,004家有效樣本', '職缺數＋受僱員工人數', '不是求職者', '9,977家有效事業單位樣本', '不能直接推算個人的錄取機率'):
            self.assertIn(phrase, body)

    def test_admission_choices_and_future_skill_rule_have_narrow_scope(self):
        admission = self.items['TW-23-005']['body']
        for phrase in ('115學年度', '116學年度', '特殊選才', '技優甄審', '由5個調整為6個', '不能推成所有招生管道', '不能給出全臺通用的個人錄取機率'):
            self.assertIn(phrase, admission)
        skills = self.items['TW-23-011']['body']
        for phrase in ('年滿15歲或國民中學畢業', '2026年7月14日發布、7月22日更新', '2027年7月1日生效', '尚未到生效日', '不能說某級證照必然提高個人薪資'):
            self.assertIn(phrase, skills)
        notice = next(s for s in self.evidence['sources_added'] if s['id']=='ch23_skill_cooking_qualification_20260722')
        self.assertEqual(notice['published_at'], '2026-07-14')
        self.assertIn('2027-07-01', notice['supports'])
        self.assertIn('更新日期2026-07-22', notice['supports'])
        self.assertEqual(notice['url'], 'https://www.wdasec.gov.tw/News_Content.aspx?n=F240F6BB01FE46BA&s=73338FF0B7B02094&sms=DD855C7DF840A224')
        self.assertEqual(notice['url'], 'https://www.wdasec.gov.tw/News_Content.aspx?n=F240F6BB01FE46BA&s=73338FF0B7B02094&sms=DD855C7DF840A224')

    def test_taiwanjobs_portal_is_a_traced_official_search_source(self):
        source_id = 'ch23_taiwanjobs_job_search_20261027'
        source = self.sources[source_id]
        self.assertEqual(source['url'], 'https://job.taiwanjobs.gov.tw/internet/index/index.aspx')
        self.assertIn('工作地點', source['supports'])
        self.assertIn('工作職稱、工作內容與技能專長', source['supports'])
        self.assertIn(source_id, self.items['TW-23-012']['source_ids'])
        review_checks = {check['url']: check for check in read('localization/reviews/TW-23-012.json')['source_checks']}
        evidence_checks = {check['url']: check for check in self.evidence_items['TW-23-012']['source_checks']}
        self.assertIn(source['url'], review_checks)
        self.assertIn(source['url'], evidence_checks)
        for check in (review_checks[source['url']], evidence_checks[source['url']]):
            self.assertIn('關鍵字', check['claim'])
            self.assertIn('工作職稱、工作內容、技能專長', check['supporting_passage'])

    def test_cpa_reform_separates_assistant_eligibility_and_practice_years(self):
        body = self.items['TW-23-021']['body']
        for phrase in ('2026年8月5日', '10學分以上', '高等或普通考試會計、審計人員及格', '高級商業職業學校畢業', '永續資訊簽證工作的助理不受這四款資格限制', '二年以上經驗', '兩項不同規定', '公會', '不包括受委任辦理稅捐查核簽證申報'):
            self.assertIn(phrase, body)
        self.assertIn('登錄後還須加入記帳士公會', body)
        self.assertIn('全國聯合會擬訂並報主管機關核定', body)
        self.assertIn('考選部當年度考試動態詳頁本次直接讀取逾時', body)
        self.assertIn('未取得獨立法律、會計或考選專業簽證', body)


if __name__ == '__main__':
    unittest.main()

"""第23章學術資格、職稱、工資與訓練成本四篇回溯再審契約。"""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from reader_copy_test_support import assert_body_version_matches_review_or_cleanup, assert_reader_limits_match_review_or_cleanup
from content_validation import load_json
from ci_language_policy import audit_drafts
from retroactive_audit import validate_recheck_history
from review_contract import ROOT, validate_runtime

BASE = '07623ea84390cb0474f2a326710354bd0ef499ec'
EVIDENCE_PATH = 'localization/ch23-credentials-title-wage-training-recheck-20261027.json'
ITEM_IDS = {'TW-23-013', 'TW-23-020', 'TW-23-022', 'TW-23-023'}
NEW_SOURCE_IDS = {
    'ch23_degree_act_recheck_20261027',
    'ch23_moe_ghostwriting_penalty_recheck_20261027',
    'ch23_teacher_qualification_recheck_20261027',
    'ch23_certificate_recheck_20261027',
    'ch23_labor_act_recheck_20261027',
    'ch23_training_scheme_recheck_20261027',
    'ch23_training_cap_faq_20261027',
}
RETIRED_SOURCE_IDS = {
    'ch23_training', 'ch23_certificate', 'ch23_teacher', 'ch23_degree', 'ch23_labor'
}


def read(path):
    return load_json(ROOT / path)


def old(path):
    return json.loads(subprocess.check_output(['git', 'show', f'{BASE}:{path}'], cwd=ROOT, text=True))


class Ch23CredentialsTitleWageTrainingRecheckTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.evidence = read(EVIDENCE_PATH)
        cls.runtime = validate_runtime()
        cls.items = {item['id']: item for item in cls.runtime['items']}
        cls.sources = {source['id']: source for source in cls.runtime['sources']}
        cls.manifest = {item['id']: item for item in read('localization/manifest.json')['entries']}
        cls.register = read('localization/retroactive-review-register-20261019.json')
        cls.records = {item['id']: item for item in cls.register['substantive_rechecks']}
        cls.evidence_items = {item['id']: item for item in cls.evidence['items']}

    def test_batch_progress_and_publication_boundary(self):
        coverage = read('localization/tw-edition/coverage.json')
        self.assertEqual(self.evidence['base_main_sha'], BASE)
        self.assertEqual(self.evidence['new_core_entries'], [])
        self.assertEqual({item['id'] for item in self.evidence['items']}, ITEM_IDS)
        self.assertEqual(self.evidence['counts_before']['core_completed'], 278)
        self.assertEqual(self.evidence['counts_before']['substantive_rechecks'], 202)
        self.assertEqual(self.evidence['counts_after']['substantive_rechecks'], 206)
        self.assertEqual(self.evidence['counts_after']['substantive_rechecks'], 202 + len(ITEM_IDS))
        self.assertEqual(self.evidence['counts_before']['runtime_sources'], 820)
        self.assertEqual(self.evidence['counts_after']['runtime_sources'], 827)
        self.assertEqual(self.evidence['counts_before']['source_registry'], 901)
        self.assertEqual(self.evidence['counts_after']['source_registry'], 908)
        self.assertEqual(self.evidence['counts_before']['json_files_checked'], 476)
        self.assertEqual(self.evidence['counts_after']['json_files_checked'], 477)
        self.assertGreaterEqual(
            coverage['json_files_checked'],
            self.evidence['counts_after']['json_files_checked'],
        )
        self.assertGreaterEqual(
            coverage['registry_sources'],
            self.evidence['counts_after']['source_registry'],
        )
        self.assertEqual(coverage['publication_total_entries'], 765)
        self.assertEqual(coverage, audit_drafts())
        self.assertFalse(self.evidence['publication_ready'])
        self.assertFalse(coverage['publication_ready'])

    def test_body_runtime_manifest_reviews_and_prior_hashes_align(self):
        for item_id in ITEM_IDS:
            with self.subTest(item=item_id):
                item_evidence = self.evidence_items[item_id]
                body_path = ROOT / item_evidence['target_path']
                body_bytes = body_path.read_bytes()
                body_sha = hashlib.sha256(body_bytes).hexdigest()
                review_path = f'localization/reviews/{item_id}.json'
                review_bytes = (ROOT / review_path).read_bytes()
                review = json.loads(review_bytes)
                record = self.records[item_id]
                manifest_item = self.manifest[item_id]
                markdown_title = body_bytes.decode('utf-8').splitlines()[0].removeprefix('# ')
                assert_body_version_matches_review_or_cleanup(self, item_id, item_evidence['after_sha256'], body_sha)
                self.assertEqual(body_sha, review['target_sha256'])
                self.assertEqual(body_bytes.decode('utf-8'), self.items[item_id]['body'])
                self.assertEqual(markdown_title, self.items[item_id]['title'])
                self.assertEqual(manifest_item['verified_at'], self.evidence['reviewed_at'])
                self.assertEqual(set(manifest_item['sources']), {self.sources[sid]['url'] for sid in item_evidence['source_ids']})
                self.assertEqual(record['before_sha256'], item_evidence['before_sha256'])
                self.assertEqual(record['after_sha256'], item_evidence['after_sha256'])
                self.assertEqual(record['prior_revision'], BASE)
                self.assertEqual(record['source_ids'], item_evidence['source_ids'])
                self.assertEqual(record['reviewed_at'], self.evidence['reviewed_at'])
                self.assertEqual(record['review_due_at'], self.evidence['review_due_at'])
                self.assertEqual(record['status'], 'ai_source_rechecked_professional_pending')
                prior_body = subprocess.check_output(['git', 'show', item_evidence['prior_body_git_ref']], cwd=ROOT)
                prior_review = subprocess.check_output(['git', 'show', item_evidence['prior_review_git_ref']], cwd=ROOT)
                self.assertEqual(hashlib.sha256(prior_body).hexdigest(), item_evidence['before_sha256'])
                self.assertEqual(hashlib.sha256(prior_review).hexdigest(), item_evidence['prior_review_sha256'])
                self.assertEqual(review['reviewed_at'], self.evidence['reviewed_at'])
                self.assertEqual(review['review_due_at'], self.evidence['review_due_at'])
                self.assertEqual(record['limits'], review['limits'])
                assert_reader_limits_match_review_or_cleanup(self, item_id, review['limits'][0])
                self.assertEqual(review['source_checks'], item_evidence['source_checks'])
                validate_recheck_history(ROOT, record, self.items[item_id])

    def test_sources_are_additive_and_previous_objects_are_preserved(self):
        prior_runtime = {source['id']: source for source in old('localization/tw-edition/runtime.json')['sources']}
        prior_registry = {row[0]: row for row in old('localization/tw-edition/sources/16-skills.json')['sources']}
        current_registry = read('localization/tw-edition/sources/16-skills.json')['sources']
        current_registry_by_id = {row[0]: row for row in current_registry}
        evidence_sources = {source['id']: source for source in self.evidence['sources_added']}
        self.assertEqual(set(evidence_sources), NEW_SOURCE_IDS)
        self.assertEqual({row['id'] for row in self.evidence['sources_retired']}, RETIRED_SOURCE_IDS)
        self.assertTrue(set(prior_runtime).issubset(self.sources))
        for source_id, previous in prior_runtime.items():
            self.assertEqual(self.sources[source_id], previous)
        self.assertTrue(set(prior_registry).issubset(current_registry_by_id))
        for source_id, previous in prior_registry.items():
            self.assertEqual(current_registry_by_id[source_id], previous)
        for row in self.evidence['sources_retired']:
            with self.subTest(retired_source=row['id']):
                old_source = prior_runtime[row['id']]
                source_sha = hashlib.sha256(json.dumps(old_source, ensure_ascii=False, sort_keys=True).encode('utf-8')).hexdigest()
                self.assertTrue(row['preserved_in_runtime'])
                self.assertEqual(row['prior_source_sha256'], source_sha)
                self.assertEqual(self.sources[row['id']], old_source)
                self.assertTrue(set(row['replacement_ids']).issubset(set(source['id'] for source in self.evidence['sources_added'])))
                associated = [record for record in self.records.values() if any(old['id'] == row['id'] for old in record.get('retired_sources', []))]
                self.assertTrue(associated)
                self.assertTrue(any(row['replacement_ids'] and set(row['replacement_ids']).issubset(set(self.items[r['id']]['source_ids'])) for r in associated))
        for source_id, source in evidence_sources.items():
            with self.subTest(source=source_id):
                self.assertEqual(self.sources[source_id], source)
                self.assertEqual(current_registry_by_id[source_id][1], source['title'])
                self.assertEqual(current_registry_by_id[source_id][2], source['url'])
                self.assertEqual(current_registry_by_id[source_id][3], source['supports'])
                self.assertEqual(source['accessed_at'], '2026-10-27')

    def test_no_statistics_are_misrepresented_as_personal_rates(self):
        self.assertEqual(self.evidence['statistics'], [])
        self.assertFalse(self.evidence['frequency_policy']['used_event_frequency_statistics'])
        for item_id in ITEM_IDS:
            with self.subTest(item=item_id):
                evidence_item = self.evidence_items[item_id]
                self.assertEqual(evidence_item['statistics_assessed'], [])
                self.assertIn('未找到', evidence_item['frequency_assessment'])
                self.assertTrue(
                    '不估' in evidence_item['frequency_assessment']
                    or '不能推算' in evidence_item['frequency_assessment']
                )

    def test_degree_ghostwriting_law_separates_student_and_provider_liability(self):
        body = self.items['TW-23-022']['body']
        for phrase in ('第17條', '第18條', '第20條', '30萬至100萬元', '不能簡化成「購買者一律依第18條受相同罰鍰」', '資料不足，不估個人違規或被查獲機率'):
            self.assertIn(phrase, body)
        sources = set(self.items['TW-23-022']['source_ids'])
        self.assertEqual(sources, {'ch23_degree_act_recheck_20261027', 'ch23_moe_ghostwriting_penalty_recheck_20261027'})
        self.assertEqual(self.sources['ch23_degree_act_recheck_20261027']['published_at'], '2018-11-28')
        self.assertIn('行為人或負責人', self.sources['ch23_degree_act_recheck_20261027']['supports'])
        self.assertIn(self.sources['ch23_degree_act_recheck_20261027']['url'], body)

    def test_titles_and_certificates_are_distinct_taiwan_systems(self):
        teacher = self.items['TW-23-020']['body']
        for phrase in ('公司內部職級', '學校聘任且實際任教', '由服務學校提出資格審定申請', '技能檢定後由中央主管機關發給', '未找到可代表臺灣各類職稱／證照詐欺的全國事件數'):
            self.assertIn(phrase, teacher)
        cert = self.items['TW-23-013']['body']
        self.assertIn('課程結訓證明本身不等於技術士證', cert)
        self.assertEqual(set(self.items['TW-23-020']['source_ids']), {'ch23_teacher_qualification_recheck_20261027', 'ch23_certificate_recheck_20261027'})

    def test_training_subsidy_terms_have_dates_scopes_and_eligibility_limits(self):
        body = self.items['TW-23-013']['body']
        for phrase in ('80%', '100%', '三年最高補助新臺幣10萬元', '2025年1月1日起實施', '按首次參與指定相關方案課程的開訓日起算', '期滿後下一次符合方案的課程開訓日重新起算', '此方案須符合在職身分、保險及其他法定資格', '失業、待業或轉業者應另查職前訓練方案', '資格以開訓日', '部分班別須先繳全額', '0800-777-888', '不保證課程適合或能找到工作'):
            self.assertIn(phrase, body)
        self.assertIn('2026-06-16', self.sources['ch23_training_cap_faq_20261027']['supports'])
        self.assertEqual(self.sources['ch23_training_cap_faq_20261027']['published_at'], '2024-03-09')
        self.assertIn(self.sources['ch23_training_cap_faq_20261027']['url'], body)
        self.assertIn('失業者職前訓練', self.sources['ch23_training_scheme_recheck_20261027']['supports'])

    def test_labor_law_distinguishes_wage_and_training_bond_rules(self):
        body = self.items['TW-23-023']['body']
        for phrase in ('第21條', '第15-1條', '基本工資', '合理範圍', '不可歸責於勞工', '不估證照帶來加薪的個人機率'):
            self.assertIn(phrase, body)
        self.assertIn('2024-07-31', self.sources['ch23_labor_act_recheck_20261027']['published_at'])


if __name__ == '__main__':
    unittest.main()

"""2026-11-02高風險醫療、長者照護及就醫權益再審契約。"""
import hashlib
import json
import re
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from review_contract import ROOT, publication_report, validate_runtime
from retroactive_audit import validate_recheck_history
from ci_language_policy import audit_drafts


BASE = '41fe7b26fc9643e4ed077d17f70909cc78a72f21'
DATE = '2026-11-02'
DUE = '2027-02-02'
IDS = {
    'TW-16-012', 'TW-17-013', 'TW-17-009', 'TW-17-005',
    'TW-24-003', 'TW-16-002', 'TW-24-004',
}
BATCH = 'localization/medical-eldercare-recheck-20261102.json'


def load(path):
    return json.loads((ROOT / path).read_text(encoding='utf-8'))


def digest(value):
    return hashlib.sha256(value.encode('utf-8')).hexdigest()


class MedicalEldercareRecheckTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.runtime = validate_runtime()
        cls.items = {item['id']: item for item in cls.runtime['items']}
        cls.sources = {source['id']: source for source in cls.runtime['sources']}
        cls.manifest = {entry['id']: entry for entry in load('localization/manifest.json')['entries']}
        cls.register = load('localization/retroactive-review-register-20261019.json')
        cls.batch = load(BATCH)
        cls.correction = load('localization/medical-eldercare-correction-20261103.json')
        cls.following_batch = load('localization/ch13-p0-emergency-recheck-20261103.json')
        cls.rows = {}
        for item_id in IDS:
            review = load(f'localization/reviews/{item_id}.json')
            matches = [row for row in cls.register['substantive_rechecks']
                       if row.get('id') == item_id
                       and row.get('reviewed_at') == review.get('reviewed_at')
                       and row.get('after_sha256') == review.get('source_reviewed_sha256')
                       and row.get('source_checks') == review.get('source_checks')]
            if len(matches) == 1:
                cls.rows[item_id] = matches[0]

    def test_review_body_runtime_manifest_and_history_match(self):
        self.assertEqual(set(self.rows), IDS)
        self.assertEqual(set(self.batch['review_history']), IDS)
        for item_id in IDS:
            item = self.items[item_id]
            review = load(f'localization/reviews/{item_id}.json')
            row = self.rows[item_id]
            history = self.batch['review_history'][item_id]
            body_path = ROOT / item['target_path']
            body_sha = digest(item['body'])
            self.assertEqual(body_path.read_text(encoding='utf-8'), item['body'])
            self.assertEqual(review['jurisdiction'], 'TW')
            self.assertEqual(review['reviewed_at'], row['reviewed_at'])
            expected_due = '2027-02-03' if review['reviewed_at'] == '2026-11-03' else DUE
            self.assertEqual(review['review_due_at'], expected_due)
            self.assertEqual(review['target_sha256'], body_sha)
            self.assertEqual(review['source_reviewed_sha256'], body_sha)
            self.assertEqual(row['before_sha256'], history['before_body_sha256'])
            self.assertEqual(row['after_sha256'], body_sha)
            self.assertEqual(row['prior_revision'], BASE)
            self.assertEqual(row['prior_review_sha256'], history['prior_review_sha256'])
            self.assertEqual(row['status'], 'ai_source_rechecked_professional_pending')
            self.assertEqual(self.manifest[item_id]['sources'], item['source_ids'])
            self.assertEqual(self.manifest[item_id]['verified_at'], review['reviewed_at'])
            self.assertEqual(review['source_checks'], row['source_checks'])
            self.assertEqual(review['limits'], row['limits'])
            self.assertEqual(
                {check['url'] for check in review['source_checks']},
                {self.sources[source_id]['url'] for source_id in item['source_ids']},
            )
            for check in review['source_checks']:
                self.assertGreaterEqual(len(check['supporting_passage']), 50)
                self.assertIn('非逐字', check['supporting_passage'])
                self.assertLessEqual(check['accessed_at'], review['reviewed_at'])
            validate_recheck_history(ROOT, row, item)

    def test_history_and_source_objects_are_append_only(self):
        old_register = json.loads(subprocess.check_output(
            ['git', 'show', f'{BASE}:localization/retroactive-review-register-20261019.json'], cwd=ROOT
        ))
        old_runtime = json.loads(subprocess.check_output(
            ['git', 'show', f'{BASE}:localization/tw-edition/runtime.json'], cwd=ROOT
        ))
        self.assertEqual(
            self.register['substantive_rechecks'][:len(old_register['substantive_rechecks'])],
            old_register['substantive_rechecks'],
        )
        current_sources = {source['id']: source for source in self.runtime['sources']}
        for source in old_runtime['sources']:
            self.assertEqual(current_sources[source['id']], source)
        self.assertEqual(len(self.batch['new_source_ids']), 16)
        self.assertTrue({
            'care_ltc_residential_subsidy_2026',
            'care_ltc_residential_subsidy_notice_20260914',
            'care_ltc_residential_subsidy_faq_20261019',
        }.issubset(self.batch['new_source_ids']))
        self.assertEqual(self.batch['source_counts']['runtime_sources_before'], len(old_runtime['sources']))
        self.assertEqual(self.batch['source_counts']['runtime_sources_after'], len(old_runtime['sources']) + 16)
        followup = load('localization/ch01-flu-refresh-20261103.json')
        coverage = load('localization/tw-edition/coverage.json')
        correction = self.correction
        self.assertEqual(followup['source_counts']['runtime_before'], self.batch['core_progress']['after']['runtime_sources'])
        self.assertEqual(followup['source_counts']['registry_before'], self.batch['core_progress']['after']['registry_sources'])
        self.assertEqual(followup['source_counts']['runtime_after'], correction['source_counts']['runtime_sources_before'])
        self.assertEqual(followup['source_counts']['registry_after'], correction['source_counts']['registry_sources_before'])
        self.assertEqual(
            correction['source_counts']['runtime_sources_after'],
            self.following_batch['counts_before']['runtime_sources_before'],
        )
        self.assertEqual(
            correction['source_counts']['registry_sources_after'],
            self.following_batch['counts_before']['registry_sources_before'],
        )
        self.assertGreaterEqual(len(self.runtime['sources']), self.following_batch['counts_after']['runtime_sources'])
        self.assertGreaterEqual(coverage['registry_sources'], self.following_batch['counts_after']['registry_sources'])
        self.assertGreaterEqual(coverage['json_files_checked'], self.following_batch['counts_after']['json_files'])
        self.assertEqual(
            correction['source_counts']['json_files_after'],
            self.following_batch['counts_before']['json_files_before'],
        )
        self.assertEqual(self.batch['source_counts']['references_retired'], 8)
        for item_id, row in self.rows.items():
            previous = next(item for item in old_runtime['items'] if item['id'] == item_id)
            self.assertEqual(row['previous_source_ids'], previous['source_ids'])
            self.assertEqual(row['previous_body'], previous['body'])
            for retired in row['retired_sources']:
                prior = next(source for source in old_runtime['sources'] if source['id'] == retired['id'])
                self.assertEqual(current_sources[retired['id']], prior)
                self.assertEqual(
                    retired['prior_source_sha256'],
                    hashlib.sha256(json.dumps(prior, ensure_ascii=False, sort_keys=True).encode()).hexdigest(),
                )

    def test_followup_corrections_are_traced_to_current_reader_text(self):
        corrections = {row['id']: row for row in self.correction['corrections']}
        self.assertEqual(set(corrections), {'TW-16-002', 'TW-17-005', 'TW-17-013'})
        for item_id, correction in corrections.items():
            item = self.items[item_id]
            review = load(f'localization/reviews/{item_id}.json')
            body_path = ROOT / item['target_path']
            body_sha = hashlib.sha256(body_path.read_bytes()).hexdigest()
            self.assertEqual(correction['source_accessed_at'], '2026-11-03')
            self.assertEqual(correction['final_sha256'], body_sha)
            self.assertEqual(review['target_sha256'], body_sha)
            self.assertIn(correction['supporting_source_url'], {row['url'] for row in review['source_checks']})
            if item_id == 'TW-17-005':
                self.assertIn(correction['corroborating_source_url'], {row['url'] for row in review['source_checks']})
                self.assertIn(correction['corroborating_source_id'], item['source_ids'])
            self.assertEqual(correction['professional_review'], 'pending')
        self.assertIn('不會只因跨縣市就必須回原院所', self.items['TW-16-002']['body'])
        subsidy_correction = corrections['TW-17-005']
        self.assertIn('住院期間若機構保留床位，原則上可將住院日計入住期', self.items['TW-17-005']['body'])
        self.assertIn(subsidy_correction['supporting_source_id'], self.items['TW-17-005']['source_ids'])
        self.assertIn(subsidy_correction['corroborating_source_id'], self.items['TW-17-005']['source_ids'])
        self.assertIn('全年齡失智且失能者', self.items['TW-17-013']['body'])
        self.assertNotIn('49歲以下失智者', self.items['TW-17-013']['body'])

    def test_correction_reuses_the_existing_faq_source_identity(self):
        faq_url = 'https://www.mohw.gov.tw/dl-102600-e2676cd5-c570-41fd-8f29-0e1921ca8efe.html'
        existing_id = 'care_ltc_residential_subsidy_faq_20261019'
        duplicate_id = 'care_ltc_residential_subsidy_faq_transition_hospital_20261103'
        faq_sources = [source for source in self.runtime['sources'] if source['url'] == faq_url]
        self.assertEqual(len(faq_sources), 1)
        self.assertEqual(faq_sources[0]['id'], existing_id)
        self.assertEqual(faq_sources[0]['accessed_at'], '2026-11-03')
        self.assertIn('Q23', faq_sources[0]['supports'])
        self.assertIn('Q30', faq_sources[0]['supports'])
        review = load('localization/reviews/TW-17-005.json')
        faq_checks = [row for row in review['source_checks'] if row['url'] == faq_url]
        self.assertEqual({row['accessed_at'] for row in faq_checks}, {'2026-11-02', '2026-11-03'})

        correction = next(row for row in self.correction['corrections'] if row['id'] == 'TW-17-005')
        item = self.items['TW-17-005']
        self.assertEqual(correction['supporting_source_id'], existing_id)
        self.assertIn(existing_id, item['source_ids'])
        self.assertNotIn(duplicate_id, item['source_ids'])
        self.assertNotIn(duplicate_id, self.correction['new_source_ids'])
        self.assertIn(existing_id, self.correction['reused_source_ids'])
        source_evidence = load('localization/tw-edition/sources/medical-eldercare-correction-20261103.json')
        source_evidence_ids = [row[0] for row in source_evidence['sources']]
        self.assertEqual(set(source_evidence_ids), set(self.correction['new_source_ids']))
        self.assertNotIn(duplicate_id, source_evidence_ids)

        coverage = load('localization/tw-edition/coverage.json')
        self.assertEqual(
            self.correction['source_counts']['runtime_sources_after'],
            self.following_batch['counts_before']['runtime_sources_before'],
        )
        self.assertEqual(
            self.correction['source_counts']['registry_sources_after'],
            self.following_batch['counts_before']['registry_sources_before'],
        )
        self.assertEqual(self.correction['source_counts']['runtime_sources_after'], 1042)
        self.assertEqual(self.correction['source_counts']['registry_sources_after'], 1125)

        register_row = next(
            row for row in reversed(self.register['substantive_rechecks'])
            if row.get('id') == 'TW-17-005' and row.get('after_sha256') == self.correction['corrections'][2]['final_sha256']
        )
        self.assertIn(existing_id, register_row['source_ids'])
        self.assertNotIn(duplicate_id, register_row['source_ids'])

    def test_taiwan_frequency_and_legal_boundaries_are_precise(self):
        batch = self.batch
        dementia = batch['statistics'][0]
        self.assertEqual(dementia['value'], 7.99)
        self.assertEqual(dementia['measure'], '盛行率')
        self.assertEqual(dementia['period'], '2020至2023')
        self.assertEqual((dementia['numerator'], dementia['denominator']), (None, None))
        copd = batch['statistics'][1]
        self.assertIn('不作個人風險', copd['limitations'])
        self.assertTrue(batch['frequency_assessments']['TW-17-013']['credible_taiwan_rate_found'])
        self.assertFalse(any(row['credible_taiwan_rate_found'] for item_id, row in batch['frequency_assessments'].items() if item_id != 'TW-17-013'))
        self.assertIn('7.99%', self.items['TW-17-013']['body'])
        self.assertIn('第37條', self.items['TW-17-005']['body'])
        self.assertIn('不得兼營營利行為', self.items['TW-17-005']['body'])
        self.assertIn('第39條', self.items['TW-17-005']['body'])
        self.assertIn('不是當然的信託', self.items['TW-17-005']['body'])
        self.assertIn('第5-1條', self.items['TW-17-005']['body'])
        self.assertIn('第29-1條', self.items['TW-17-005']['body'])
        self.assertIn('不是每項預付款、服務契約或投資約定都違法', self.items['TW-17-005']['body'])
        self.assertIn('每月最高補助新臺幣1萬5,000元、全年最高18萬元', self.items['TW-17-005']['body'])
        self.assertIn('當月實際入住達該月日曆天數一半以上', self.items['TW-17-005']['body'])
        self.assertIn('112年1月1日前已實際入住並持續住到補助計算期間', self.items['TW-17-005']['body'])
        self.assertIn('每月補助5,000元，全年最高6萬元', self.items['TW-17-005']['body'])
        self.assertIn('2026年9月30日前已入住者，最晚可於12月16日前提出申請', self.items['TW-17-005']['body'])
        self.assertIn('2026年10月1日後新入住者，原則上從提出申請日起算', self.items['TW-17-005']['body'])
        self.assertIn('當年度更換住宿機構（包括跨縣市）須重新申請', self.items['TW-17-005']['body'])
        self.assertIn('不會因簽約自動核定或直接折抵月費', self.items['TW-17-005']['body'])
        subsidy = next(row for row in batch['policy_evidence']
                       if row['id'] == 'care_ltc_residential_subsidy_2026')
        self.assertEqual(subsidy['announced_at'], '2026-09-14')
        self.assertEqual(subsidy['effective_at'], '2026-01-01（追溯適用）')
        self.assertIn('長照需要等級第4級以上或持中度以上身心障礙證明', subsidy['eligibility'])
        self.assertIn('每月最高新臺幣1萬5,000元', subsidy['amount'])
        self.assertIn('達該月日曆天數二分之一以上', subsidy['monthly_recognition'])
        self.assertIn('2026-12-16前', subsidy['application_window'])
        self.assertIn('既有住民', subsidy['eligibility'])
        self.assertIn('曾於2025年度核定領取本方案12萬元者', self.items['TW-17-005']['body'])
        self.assertIn('2026年1月1日至8月31日實際入住累計達180日', self.items['TW-17-005']['body'])
        self.assertIn('未曾於2025年度核定領取本方案12萬元或不符合過渡保障條件者', self.items['TW-17-005']['body'])
        self.assertIn('當月住院日數達該月日曆天數一半以上', self.items['TW-17-005']['body'])
        self.assertIn('180日', subsidy['transition_rule'])
        self.assertIn('住院日數達當月日曆天數二分之一以上', subsidy['monthly_recognition'])
        trust = next(row for row in batch['legal_evidence'] if row['law'] == '信託法第1、2及86條')
        self.assertEqual(trust['announced_at'], '1996-01-26（制定公布）；2009-12-30（98年修正條文公布）')
        self.assertEqual(trust['effective_at'], '1996-01-26（本法）；2009-11-23（98年修正條文）')
        bank_act = next(row for row in batch['legal_evidence'] if row['law'] == '銀行法第5-1、29及29-1條')
        self.assertEqual(bank_act['announced_at'], '1981-07-17（第29條修正公布）；1989-07-17（增訂第5-1、29-1條公布）')
        self.assertIsNone(bank_act['effective_at'])
        self.assertNotIn('另辦另辦', self.items['TW-16-002']['body'])
        self.assertIn('《醫療法》第61條', self.items['TW-24-003']['body'])
        self.assertIn('不能只看「代掛」字眼', self.items['TW-24-003']['body'])
        self.assertEqual(batch['professional_review'], 'pending')
        self.assertFalse(publication_report()['publication_ready'])
        self.assertEqual(audit_drafts(), load('localization/tw-edition/coverage.json'))

    def test_reader_copy_has_no_batch_or_editorial_review_notes(self):
        forbidden = ('本批', 'AI來源實質再審', '專業審閱仍待取得', '臺灣改寫與來源重核')
        for item_id in IDS:
            body = self.items[item_id]['body']
            for phrase in forbidden:
                self.assertNotIn(phrase, body)
            # 「累計入住日數」可以是讀者採取行動所需的資格條件；只攔截編輯進度式篇數統計。
            self.assertIsNone(re.search(r'累計\s*[0-9]+\s*(?:篇|條|則)', body))


if __name__ == '__main__':
    unittest.main()

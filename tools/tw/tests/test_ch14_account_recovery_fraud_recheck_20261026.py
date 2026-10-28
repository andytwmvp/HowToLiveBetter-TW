"""Chapter 14 account, card-dispute and phone-number re-review evidence contract."""
import hashlib
import json
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from reader_copy_test_support import assert_body_version_matches_review_or_cleanup, assert_professional_review_pending
from review_contract import ROOT, publication_report, validate_runtime
from ci_language_policy import audit_drafts

BASE = '899a5daf61da708b74b0223a22b019cae7436f50'
IDS = {'TW-14-004', 'TW-14-005', 'TW-14-011', 'TW-14-012'}
NEW_SOURCE_IDS = {
    'cib_lost_phone_faq_2026',
    'cib_phone_forwarding_financial_takeover_2026',
    'ncc_telecom_complaint_process_current',
    'ncc_tcmc_complaint_portal_current',
    'foi_bank_dispute_categories_2026_q1',
    'foi_creditcard_otp_case_2025',
    'jcic_access_fee_faq_current',
    'jcic_credit_report_fee_schedule_current',
    'google_android_find_lost_current',
    'jcic_credit_data_correction_current',
}


def file_sha(data):
    return hashlib.sha256(data).hexdigest()


def object_sha(value):
    return file_sha(json.dumps(value, ensure_ascii=False, sort_keys=True).encode('utf-8'))


def git_show(path):
    return subprocess.check_output(['git', 'show', f'{BASE}:{path}'], cwd=ROOT)


class Chapter14AccountRecoveryRecheckTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.runtime = validate_runtime()
        cls.items = {item['id']: item for item in cls.runtime['items']}
        cls.sources = {source['id']: source for source in cls.runtime['sources']}
        cls.manifest = json.loads((ROOT / 'localization/manifest.json').read_text())
        cls.entries = {entry['id']: entry for entry in cls.manifest['entries']}
        cls.register = json.loads((ROOT / 'localization/retroactive-review-register-20261019.json').read_text())
        cls.rechecks = {item['id']: item for item in cls.register['substantive_rechecks']}
        cls.evidence = json.loads((ROOT / 'localization/ch14-account-recovery-fraud-recheck-20261026.json').read_text())

    def test_article_runtime_review_manifest_and_history_hashes_align(self):
        self.assertTrue(IDS.issubset(self.items))
        evidence_items = {item['id']: item for item in self.evidence['items']}
        for item_id in IDS:
            item = self.items[item_id]
            entry = self.entries[item_id]
            path = entry['target_path']
            raw = (ROOT / path).read_bytes()
            review_path = ROOT / f'localization/reviews/{item_id}.json'
            review_raw = review_path.read_bytes()
            review = json.loads(review_raw)
            recheck = self.rechecks[item_id]
            evidence = evidence_items[item_id]

            self.assertEqual(raw.decode('utf-8'), item['body'])
            self.assertEqual(item['review_status'], 'source_checked')
            self.assertEqual(item['reviewed_at'], '2026-10-26')
            self.assertEqual(item['review_due_at'], '2027-01-31')
            self.assertEqual(file_sha(raw), review['target_sha256'])
            assert_body_version_matches_review_or_cleanup(self, item_id, recheck['after_sha256'], file_sha(raw))
            self.assertEqual(recheck['after_sha256'], evidence['after_sha256'])
            self.assertEqual(review['target_path'], path)
            self.assertEqual(review['jurisdiction'], 'TW')
            assert_professional_review_pending(self, review['reviewer'])
            self.assertEqual(recheck['prior_revision'], BASE)
            self.assertEqual(recheck['prior_review_kind'], 'review_file')
            self.assertEqual(file_sha(git_show(path)), recheck['before_sha256'])
            self.assertEqual(file_sha(git_show(f'localization/reviews/{item_id}.json')), recheck['prior_review_sha256'])
            self.assertEqual(recheck['before_sha256'], evidence['before_sha256'])
            self.assertEqual(recheck['prior_review_sha256'], evidence['prior_review_sha256'])
            self.assertEqual(entry['verified_at'], '2026-10-26')
            self.assertEqual(item['source_ids'], recheck['source_ids'])
            expected_urls = [self.sources[source_id]['url'] for source_id in item['source_ids']]
            self.assertEqual(entry['sources'], item['source_ids'])
            self.assertEqual([check['url'] for check in review['source_checks']], expected_urls)
            self.assertEqual(review['limits'], recheck['limits'])
            self.assertTrue(all(check.get('retrieval_method') for check in review['source_checks']))
            self.assertTrue(all(check.get('supporting_passage') for check in review['source_checks']))
            self.assertEqual(len([line for line in item['body'].splitlines() if line.startswith('## ')]), 5)
            self.assertIn('ai_source_rechecked_professional_pending', recheck['status'])

    def test_old_sources_are_immutable_and_retirements_are_auditable(self):
        old_runtime = json.loads(git_show('localization/tw-edition/runtime.json'))
        old_sources = {source['id']: source for source in old_runtime['sources']}
        for source_id, old_source in old_sources.items():
            self.assertEqual(self.sources[source_id], old_source)

        for item_id in IDS:
            current_ids = set(self.items[item_id]['source_ids'])
            for retired in self.rechecks[item_id]['retired_sources']:
                self.assertNotIn(retired['id'], current_ids)
                self.assertEqual(retired['prior_source_sha256'], object_sha(old_sources[retired['id']]))
                self.assertIn(retired['id'], self.sources)

        registry = json.loads((ROOT / 'localization/tw-edition/sources/ch14.json').read_text())
        registry_rows = {row[0]: row for row in registry['sources']}
        batch_ids = {source['id'] for source in self.evidence['sources_added']}
        self.assertEqual(batch_ids, NEW_SOURCE_IDS)
        self.assertTrue(batch_ids.issubset(registry_rows))
        self.assertTrue(batch_ids.issubset(self.sources))
        for source_id in NEW_SOURCE_IDS:
            source = self.sources[source_id]
            row = registry_rows[source_id]
            self.assertEqual(row, [source_id, source['title'], source['url'], source['supports']])

    def test_taiwan_frequency_scope_procedures_and_professional_limits(self):
        self.assertEqual(self.evidence['statistics'][0]['period_start'], '2026-01-01')
        self.assertEqual(self.evidence['statistics'][0]['period_end'], '2026-03-31')
        self.assertEqual(self.evidence['statistics'][0]['numerator'], 101)
        self.assertEqual(self.evidence['statistics'][0]['denominator'], 235)
        self.assertEqual(self.evidence['statistics'][0]['reported_share_percent'], 42.98)
        self.assertTrue(any('不是全體刷卡交易' in x for x in self.evidence['statistics'][0]['limitations']))
        self.assertIn('單一', self.evidence['official_case_examples'][0]['definition'])
        self.assertIn('不能推估個人機率', self.evidence['official_case_examples'][0]['limitation'])
        self.assertEqual(len(self.evidence['legal_effective_dates']), 1)
        self.assertEqual(self.evidence['legal_effective_dates'][0]['effective_date_of_latest_amendment'], '2024-02-01')
        self.assertIn('不包括第13條', self.evidence['legal_effective_dates'][0]['latest_amendment_scope'])

        expected_by_item = {
            'TW-14-004': ('15日內回覆', '30日內', '未達新臺幣2,000元', '0800-034-580', '260萬元', '105萬元', '165'),
            'TW-14-005': ('收受申訴後30日內', '60日內', '2026年第1季', '101件', '235件'),
            'TW-14-011': ('15日內回覆', '30日內', '未達新臺幣2,000元', '0800-034-580', '年滿18歲', '1至2個工作日', '線上查閱與書面申請每年度', '新臺幣80元', '新臺幣100元'),
            'TW-14-012': ('15日內回覆', '30日內', '未達新臺幣2,000元', '0800-034-580', '7天'),
        }
        for item_id, phrases in expected_by_item.items():
            with self.subTest(item=item_id):
                for phrase in phrases:
                    self.assertIn(phrase, self.items[item_id]['body'])
        self.assertFalse(self.evidence['publication_ready'])
        report = publication_report()
        self.assertFalse(report['publication_ready'])
        self.assertEqual(report['publication_completed_entries'], 278)
        self.assertEqual(report['publication_total_entries'], 765)

    def test_coverage_and_baseline_counts_remain_truthful(self):
        coverage = json.loads((ROOT / 'localization/tw-edition/coverage.json').read_text())
        self.assertEqual(self.evidence['counts_before']['substantive_rechecks'], 178)
        self.assertEqual(self.evidence['counts_after']['substantive_rechecks'], 182)
        self.assertGreaterEqual(coverage['json_files_checked'], self.evidence['counts_after']['json_files_checked'])
        self.assertGreaterEqual(coverage['registry_sources'], self.evidence['counts_after']['source_registry'])
        self.assertEqual(coverage['publication_completed_entries'], 278)
        self.assertEqual(coverage['publication_total_entries'], 765)
        self.assertEqual(coverage['topics_with_any_content'], 498)
        self.assertEqual(coverage['topics_without_content'], 267)
        self.assertEqual(coverage, audit_drafts())
        self.assertFalse(coverage['publication_ready'])
        self.assertGreaterEqual(len(self.runtime['items']), self.evidence['counts_after']['reader_items'])
        self.assertGreaterEqual(len(self.runtime['sources']), self.evidence['counts_after']['runtime_sources'])


if __name__ == '__main__':
    unittest.main()

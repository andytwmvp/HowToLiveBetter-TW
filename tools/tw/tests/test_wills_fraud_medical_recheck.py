"""遺囑、防詐、家醫照護與急症分流的歷史再審契約。"""
import copy
import hashlib
import json
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from review_contract import ROOT, publication_report, validate_runtime
from retroactive_audit import (
    _registered_history_connects,
    assert_preserved_or_rechecked,
    documented_revision,
    validate_recheck_history,
    validate_reader_copy_cleanup_history,
)

BASE = 'c5e5608bc3cd47da9693878b7e69684393f22312'
IDS = {'TW-17-002', 'TW-17-004', 'TW-16-006', 'TW-24-001'}
BATCH = 'localization/legal-fraud-care-recheck-20261025.json'
OLDER_REVIEW_BASE = '48433c16d9efedabf9f5775d33f06a0597b94750'


def load(path):
    return json.loads((ROOT / path).read_text(encoding='utf-8'))


class WillsFraudMedicalRecheckTests(unittest.TestCase):
    def test_historical_hashes_review_records_and_source_links(self):
        runtime = validate_runtime()
        items = {item['id']: item for item in runtime['items']}
        sources = {source['id']: source for source in runtime['sources']}
        rows = load('localization/retroactive-review-register-20261019.json')['substantive_rechecks']
        manifest = {row['id']: row for row in load('localization/manifest.json')['entries']}
        for key in IDS:
            item = items[key]
            review = load(f'localization/reviews/{key}.json')
            body_sha = hashlib.sha256(item['body'].encode()).hexdigest()
            current_records = [
                row for row in rows
                if row['id'] == key and row.get('reviewed_at') == '2026-10-25'
            ]
            self.assertEqual(len(current_records), 1, key)
            cleanup = next((row for row in load('localization/retroactive-review-register-20261019.json')['reader_copy_cleanups']
                            if row['id'] == key and row.get('after_sha256') == body_sha), None)
            if cleanup:
                previous = validate_reader_copy_cleanup_history(ROOT, cleanup, item)
                self.assertEqual(hashlib.sha256(previous['body'].encode()).hexdigest(), current_records[0]['after_sha256'])
            else:
                self.assertEqual(body_sha, current_records[0]['after_sha256'])
            self.assertEqual((ROOT / item['target_path']).read_text(encoding='utf-8'), item['body'])
            self.assertEqual(review['target_sha256'], hashlib.sha256(item['body'].encode()).hexdigest())
            self.assertEqual(review['source_checks'], current_records[0]['source_checks'])
            for check in review['source_checks']:
                self.assertGreaterEqual(len(check['supporting_passage']), 50)
                self.assertNotEqual(check['supporting_passage'], check['claim'])
                self.assertNotIn(check['claim'], check['supporting_passage'])
                self.assertIn('非逐字', check['supporting_passage'])
            self.assertEqual({check['url'] for check in review['source_checks']}, {sources[src]['url'] for src in item['source_ids']})
            self.assertEqual(manifest[key]['sources'], item['source_ids'])
            self.assertEqual(item['reviewed_at'], '2026-10-25')

    def test_old_items_and_source_objects_are_preserved(self):
        old = json.loads(subprocess.check_output(['git', 'show', BASE + ':localization/tw-edition/runtime.json'], cwd=ROOT))
        runtime = validate_runtime()
        items = {item['id']: item for item in runtime['items']}
        sources = {source['id']: source for source in runtime['sources']}
        self.assertEqual([item['id'] for item in old['items']], [item['id'] for item in runtime['items']])
        for item in old['items']:
            assert_preserved_or_rechecked(self, item, items[item['id']])
        for source in old['sources']:
            self.assertEqual(source, sources[source['id']])

    def test_older_recheck_history_remains_valid_after_a_newer_review(self):
        old = json.loads(subprocess.check_output([
            'git', 'show', OLDER_REVIEW_BASE + ':localization/tw-edition/runtime.json'
        ], cwd=ROOT))
        prior = next(item for item in old['items'] if item['id'] == 'TW-24-001')
        current = next(item for item in validate_runtime()['items'] if item['id'] == 'TW-24-001')
        assert_preserved_or_rechecked(self, prior, current)

    def test_history_chain_rejects_same_body_with_unrecorded_metadata(self):
        current = next(item for item in validate_runtime()['items'] if item['id'] == 'TW-07-014')
        altered = copy.deepcopy(current)
        altered['title'] += ' 未登錄的標題異動'
        self.assertEqual(hashlib.sha256(altered['body'].encode()).hexdigest(),
                         hashlib.sha256(current['body'].encode()).hexdigest())
        self.assertNotEqual(altered, current)
        current_sha = hashlib.sha256(current['body'].encode()).hexdigest()
        record = next(
            row for row in load('localization/retroactive-review-register-20261019.json')['substantive_rechecks']
            if row['id'] == 'TW-07-014' and row.get('after_sha256') == current_sha
        )
        self.assertFalse(_registered_history_connects(ROOT, altered, current, record))

    def test_taiwan_will_law_announcement_effective_date_and_transition(self):
        item = next(item for item in validate_runtime()['items'] if item['id'] == 'TW-17-002')
        body = item['body']
        batch = load(BATCH)
        evidence = batch['legal_evidence'][0]
        self.assertEqual((evidence['announced_at'], evidence['effective_at']), ('2026-08-17', '2027-02-17'))
        self.assertIn('公布六個月後', body)
        self.assertIn('2027-02-17起施行', body)
        self.assertIn('施行前立的遺囑若在施行後才發生效力', body)
        self.assertIn('兄弟姊妹的法定繼承順位未因這次修法消失', body)
        self.assertIn('未取得同期間、同法域且有有效立遺囑人分母', load(BATCH)['frequency_assessments']['TW-17-002'])

    def test_fraud_statistics_do_not_claim_personal_incidence(self):
        batch = load(BATCH)
        values = {(row['value'], row['unit'], row['period']) for row in batch['statistics']}
        self.assertIn((10775, '件', '2026年9月'), values)
        self.assertIn((39.3, '新臺幣億元以上', '2026年9月'), values)
        for stat in batch['statistics']:
            self.assertIsNone(stat['denominator'])
            self.assertIn('行政', stat['method'])
            self.assertTrue('不能' in stat['limitations'] or '不得' in stat['limitations'])
        fraud = next(item for item in validate_runtime()['items'] if item['id'] == 'TW-17-004')
        self.assertIn('不是獨立被害人數', fraud['body'])
        self.assertIn('不能換算你的個人受騙機率', fraud['body'])
        self.assertLess(fraud['body'].index('用銀行官方客服聯絡轉出銀行'), fraud['body'].index('2026-10-14合作備忘錄公告內文引述165打詐儀錶板'))
        self.assertIn('不要提供', fraud['body'])
        self.assertIn('追回', fraud['body'])
        self.assertIn('合作備忘錄公告內文所載2026年9月', fraud['body'])
        self.assertIn('110報案服務', fraud['body'])
        row = next(x for x in load('localization/retroactive-review-register-20261019.json')['substantive_rechecks'] if x['id'] == 'TW-17-004')
        self.assertEqual(row['retired_sources'][0]['id'], 'ch17_npa_110_20250728')
        self.assertEqual(row['retired_sources'][0]['replacement_ids'], ['violence_npa_110'])

    def test_emergency_action_precedes_routine_care_and_cost(self):
        item = next(item for item in validate_runtime()['items'] if item['id'] == 'TW-24-001')
        body = item['body']
        self.assertLess(body.index('立即撥119'), body.index('一般西醫門診基本部分負擔'))
        self.assertLess(body.index('立即撥119'), body.index('成本與可期待的效益'))
        self.assertIn('不要等待基層門診、轉診文件或費用比較', body)
        self.assertIn('勿自行駕駛前往', body)
        self.assertIn('hpa_emergency', item['source_ids'])
        self.assertIn('50元', body)
        self.assertIn('420元', body)

    def test_family_doctor_plan_distinguishes_provider_payment_and_patient_cost(self):
        item = next(item for item in validate_runtime()['items'] if item['id'] == 'TW-16-006')
        body = item['body']
        self.assertIn('2026-01-01', body)
        self.assertIn('2026-07-01', body)
        self.assertIn('不等於發給個人的補助金', body)
        self.assertIn('若民眾不同意', body)
        self.assertIn('不保證有個人醫師24小時接聽', body)
        self.assertIn('查詢名單不保證當下仍收案、可掛號或符合本人資格', body)
        self.assertIn('目前沒有2026年全國同口徑的參與人數與需整合照護總數', body)

    def test_professional_review_remains_pending(self):
        batch = load(BATCH)
        self.assertEqual(batch['new_core_ids'], [])
        self.assertEqual(batch['professional_review'], 'pending')
        self.assertFalse(publication_report()['publication_ready'])
        for key in IDS:
            review = load(f'localization/reviews/{key}.json')
            self.assertIn('未取得獨立', review['reviewer'])
            self.assertIn('2027-', review['review_due_at'])

    def test_progress_report_uses_live_base_and_worktree_metrics(self):
        progress = load(BATCH)['progress_before_after']
        self.assertEqual(progress['before'], progress['after'])
        self.assertEqual(progress['before']['core_verified'], 278)
        self.assertEqual(progress['before']['core_total'], 765)
        self.assertEqual(progress['before']['unresolved_source_ids'], 115)
        self.assertEqual(progress['before']['unresolved_reference_occurrences'], 306)
        self.assertEqual(progress['batch_delta']['new_core_entries'], 0)
        self.assertEqual(progress['batch_delta']['substantive_recheck_events'], 4)
        self.assertFalse(progress['after']['publication_ready'])

    def test_next_review_date_must_match_historical_register(self):
        key = 'TW-17-002'
        runtime = validate_runtime()
        item = copy.deepcopy(next(row for row in runtime['items'] if row['id'] == key))
        record = next(row for row in load('localization/retroactive-review-register-20261019.json')['substantive_rechecks'] if row['id'] == key)
        changed = copy.deepcopy(item)
        changed['body'] += '\n\n僅供契約測試的正文差異。'
        changed['review_due_at'] = '2027-03-01'
        self.assertFalse(documented_revision(item, changed, record))
        matching_record = copy.deepcopy(record)
        matching_record['review_due_at'] = changed['review_due_at']
        matching_record['before_sha256'] = hashlib.sha256(item['body'].encode()).hexdigest()
        matching_record['after_sha256'] = hashlib.sha256(changed['body'].encode()).hexdigest()
        self.assertTrue(documented_revision(item, changed, matching_record))


if __name__ == '__main__':
    unittest.main()

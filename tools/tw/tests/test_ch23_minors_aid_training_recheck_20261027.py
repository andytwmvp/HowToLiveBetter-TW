"""2026-10-27第23章四篇高風險歷史再審的證據與資料契約。"""
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

BASE = '9e164aa7840be5e34b63acd41f683467aeee414c'
EVIDENCE_PATH = 'localization/ch23-minors-aid-training-recheck-20261027.json'
ITEM_IDS = {'TW-23-001', 'TW-23-004', 'TW-23-008', 'TW-23-009'}
NEW_SOURCE_IDS = {
    'ch23_mol_student_inspection_114',
    'ch23_certificate_exam_schedule_current',
    'ch23_training_q_and_a_115',
}


def read(path):
    return load_json(ROOT / path)


def old(path):
    return json.loads(subprocess.check_output(['git', 'show', f'{BASE}:{path}'], cwd=ROOT, text=True))


class Ch23MinorsAidTrainingRecheckTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.evidence = read(EVIDENCE_PATH)
        cls.runtime = validate_runtime()
        cls.items = {entry['id']: entry for entry in cls.runtime['items']}
        cls.sources = {source['id']: source for source in cls.runtime['sources']}
        cls.register = read('localization/retroactive-review-register-20261019.json')
        cls.records = {record['id']: record for record in cls.register['substantive_rechecks']}

    def test_batch_identity_counts_and_publication_boundary(self):
        self.assertEqual(self.evidence['base_main_sha'], BASE)
        self.assertEqual(self.evidence['new_core_entries'], [])
        self.assertEqual({item['id'] for item in self.evidence['items']}, ITEM_IDS)
        self.assertEqual(self.evidence['counts_after']['substantive_rechecks'], self.evidence['counts_before']['substantive_rechecks'] + 4)
        self.assertEqual(self.evidence['counts_after']['runtime_sources'], self.evidence['counts_before']['runtime_sources'] + 3)
        self.assertEqual(self.evidence['counts_after']['source_registry'], self.evidence['counts_before']['source_registry'] + 3)
        self.assertEqual(self.evidence['counts_after']['json_files_checked'], self.evidence['counts_before']['json_files_checked'] + 1)
        self.assertEqual(len(self.records), self.evidence['counts_after']['substantive_rechecks'])
        self.assertFalse(self.evidence['publication_ready'])
        self.assertFalse(read('localization/tw-edition/coverage.json')['publication_ready'])
        self.assertEqual(self.evidence['counts_after']['core_completed'], self.evidence['counts_before']['core_completed'])

    def test_body_manifest_runtime_review_and_historical_hashes_align(self):
        manifest = {entry['id']: entry for entry in read('localization/manifest.json')['entries']}
        evidence_items = {item['id']: item for item in self.evidence['items']}
        for item_id in ITEM_IDS:
            with self.subTest(item=item_id):
                item = evidence_items[item_id]
                body_path = item['target_path']
                body_bytes = (ROOT / body_path).read_bytes()
                body_sha = hashlib.sha256(body_bytes).hexdigest()
                review_path = f'localization/reviews/{item_id}.json'
                review_bytes = (ROOT / review_path).read_bytes()
                review = json.loads(review_bytes)
                entry = manifest[item_id]
                record = self.records[item_id]
                self.assertEqual(body_sha, item['after_sha256'])
                self.assertEqual(body_sha, review['target_sha256'])
                self.assertEqual(body_bytes.decode(), self.items[item_id]['body'].encode().decode())
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

    def test_supplemental_sources_are_additive_and_old_sources_unchanged(self):
        prior_runtime = {source['id']: source for source in old('localization/tw-edition/runtime.json')['sources']}
        prior_registry = {row[0]: row for row in old('localization/tw-edition/sources/16-skills.json')['sources']}
        registry_rows = {row[0]: row for row in read('localization/tw-edition/sources/16-skills.json')['sources']}
        evidence_sources = {source['id']: source for source in self.evidence['sources_added']}
        self.assertEqual(set(evidence_sources), NEW_SOURCE_IDS)
        self.assertEqual(self.evidence['sources_retired'], [])
        self.assertEqual(set(prior_runtime).issubset(self.sources), True)
        for source_id, previous in prior_runtime.items():
            self.assertEqual(self.sources[source_id], previous)
        self.assertEqual(set(registry_rows), set(prior_registry) | NEW_SOURCE_IDS)
        self.assertEqual(set(self.sources), set(prior_runtime) | NEW_SOURCE_IDS)
        for source_id, source in evidence_sources.items():
            self.assertEqual(self.sources[source_id], source)
            self.assertEqual(registry_rows[source_id][2], source['url'])
            self.assertGreater(len(source['retrieval_method']), 20)

    def test_labor_inspection_statistic_keeps_denominator_and_selection_limits(self):
        statistic = self.evidence['statistics'][0]
        self.assertEqual(statistic['source_id'], 'ch23_mol_student_inspection_114')
        self.assertEqual(statistic['period'], '114年度（2025年）')
        self.assertNotIn('period_start', statistic)
        self.assertNotIn('period_end', statistic)
        self.assertEqual((statistic['numerator'], statistic['denominator']), (465, 1852))
        self.assertEqual(statistic['unit'], '家；被選列受檢事業中任一勞動法令違規占比')
        self.assertAlmostEqual(statistic['numerator'] / statistic['denominator'] * 100, 25.11, places=2)
        self.assertIn('非機率抽樣', statistic['method'])
        self.assertTrue(any('不能轉成個人發生機率' in limit for limit in statistic['limitations']))
        body = self.items['TW-23-001']['body']
        for phrase in ('1,852家', '465家', '特定業別', '不是隨機抽樣', '不能推成全臺雇主'):
            self.assertIn(phrase, body)

    def test_training_absence_exceptions_require_regional_branch_recognition(self):
        body = self.items['TW-23-009']['body']
        for phrase in (
            '天然災害停止上班及上課',
            '國防部召集規則',
            '勞工請假規則',
            '百日內',
            '公職人員選舉',
            '全國性公民投票日',
            '辦訓地所屬轄區分署認列',
        ):
            self.assertIn(phrase, body)
        self.assertIn('非自動扣除', self.items['TW-23-009']['limits'])
        item = next(entry for entry in self.evidence['items'] if entry['id'] == 'TW-23-009')
        q_and_a = next(source for source in item['source_checks'] if '2d14b503-e267-4c3c-942b-a889a84dab2f.pdf' in source['url'])
        self.assertIn('轄區分署認列', q_and_a['supporting_passage'])
        self.assertIn('第6頁問26', q_and_a['retrieval_method'])


if __name__ == '__main__':
    unittest.main()

"""再審必須有證據與雜湊；不允許以狀態字串跳過歷史保全。"""
import copy
import hashlib
import sys
import unittest
from unittest.mock import patch
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import retroactive_audit as audit

class SubstantiveReviewTests(unittest.TestCase):
    def fixture(self):
        old = {'id': 'TW-13-001', 'body': 'old', 'title': 'title', 'reviewed_at': '2026-10-17'}
        new = dict(old, body='new', reviewed_at='2026-10-19')
        record = {'id': old['id'], 'before_sha256': hashlib.sha256(b'old').hexdigest(),
                  'after_sha256': hashlib.sha256(b'new').hexdigest(),
                  'reviewed_at': '2026-10-19', 'review_due_at': '2026-12-31',
                  'status': 'ai_source_rechecked_professional_pending',
                  'prior_revision': '6b85081cd806bea348523d486bf9e87efb686117',
                  'prior_review_sha256': 'a'*64,
                  'taiwan_context': '家中倒地', 'frequency_assessment': '缺臺灣暴露母數',
                  'changes': '補充統計界線', 'limits': ['非專業簽證'],
                  'source_checks': [{'url':'https://www.119.gov.taipei/',
                                     'claim':'求援', 'supporting_passage':'119求援',
                                     'accessed_at':'2026-10-19'}]}
        return old, new, record

    def test_documented_revision_is_accepted(self):
        old, new, record = self.fixture()
        self.assertTrue(audit.documented_revision(old, new, record))

    def test_unrecorded_body_metadata_and_missing_evidence_are_rejected(self):
        old, new, record = self.fixture()
        for field in ('before_sha256','after_sha256','source_checks','limits','frequency_assessment','prior_review_sha256'):
            bad = copy.deepcopy(record); bad.pop(field)
            with self.subTest(field=field):
                self.assertFalse(audit.documented_revision(old,new,bad))
        self.assertFalse(audit.documented_revision(old, dict(new, title='silent change'), record))
        self.assertFalse(audit.documented_revision(old, dict(new, body='tampered'), record))

    def test_audit_exposes_ai_rechecks_without_professional_completion(self):
        report = audit.audit()
        records = report.get('ai_source_rechecks', [])
        self.assertGreaterEqual(len(records), 4)
        self.assertTrue(all(r['status'] == 'ai_source_rechecked_professional_pending' for r in records))
        self.assertFalse(report['summary']['publication_ready'])

    def test_audit_rejects_well_formed_but_false_history_hash(self):
        original = audit.load
        def altered(root, path):
            data = original(root, path)
            if path == 'localization/retroactive-review-register-20261019.json':
                data['substantive_rechecks'][0]['prior_review_sha256'] = 'a' * 64
            return data
        with patch.object(audit, 'load', side_effect=altered):
            with self.assertRaisesRegex(ValueError, '原始審閱 SHA'):
                audit.audit()

    def test_date_only_update_never_counts_as_substantive_review(self):
        old, new, record = self.fixture()
        unchanged = dict(old, reviewed_at='2026-10-19')
        record['after_sha256'] = record['before_sha256']
        self.assertFalse(audit.documented_revision(old, unchanged, record))

if __name__ == '__main__': unittest.main()

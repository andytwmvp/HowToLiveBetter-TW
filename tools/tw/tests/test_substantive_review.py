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

    def test_emergency_question_exception_is_bound_to_chemical_eye_review(self):
        old, new, record = self.fixture()
        old['question'] = '舊的化學眼傷自查問題嗎？'
        new['question'] = '我已瞭解液體化學品入眼時要立即沖洗、成分不明粉末要避免揉挖並立即求助、已知物質依眼睛專屬指示、眼球穿刺傷勿沖洗，以及聯絡毒物中心、立即就醫與撥119的分流時機嗎？'
        record['question_change_reason'] = (
            '原自查問題未分清液體化學品沖洗與未知粉末未定分流，也未涵蓋已知物質眼睛專屬指示、'
            '眼球穿刺傷和求援時機；依正文同步補上立即求助及就醫限制。'
        )
        self.assertFalse(audit.documented_revision(old, new, record))
        old['id'] = new['id'] = record['id'] = 'TW-13-021'
        self.assertTrue(audit.documented_revision(old, new, record))
        bad_reason = dict(record, question_change_reason='任意理由')
        self.assertFalse(audit.documented_revision(old, new, bad_reason))

    def test_topic_fidelity_question_change_requires_a_bound_restoration_decision(self):
        old, new, record = self.fixture()
        old['question'] = '原先涵蓋夜間職場安全與通勤的問題嗎？'
        new['title'] = '夜班與心血管風險'
        new['body'] = '# 夜班與心血管風險\n\n新正文'
        record['after_sha256'] = hashlib.sha256(new['body'].encode('utf-8')).hexdigest()
        new['question'] = '夜班工作與心血管風險有哪些研究證據？'
        record['topic_fidelity_review'] = {
            'question_change': {
                'decision': 'realign_with_restored_core_topic',
                'previous_question': old['question'],
                'current_question': new['question'],
                'reason': '恢復原題核心研究主題後，同步調整自查問題。',
            }
        }
        self.assertTrue(audit.documented_revision(old, new, record))
        for key, value in (
            ('decision', 'unreviewed_change'),
            ('previous_question', 'different prior question'),
            ('current_question', 'different new question'),
            ('reason', ''),
        ):
            bad = copy.deepcopy(record)
            bad['topic_fidelity_review']['question_change'][key] = value
            with self.subTest(key=key):
                self.assertFalse(audit.documented_revision(old, new, bad))

    def test_removed_out_of_scope_claim_does_not_require_a_false_replacement_source(self):
        old, new, record = self.fixture()
        old['source_ids'] = ['prior_stop_work_claim']
        new['source_ids'] = []
        record['retired_sources'] = [{
            'id': 'prior_stop_work_claim',
            'disposition': 'claim_removed_from_scope',
            'reason': '本篇不再提出該主張，改由職場安全專篇處理。',
            'replacement_ids': [],
            'prior_source_sha256': 'a' * 64,
        }]
        self.assertTrue(audit.documented_revision(old, new, record))
        bad = copy.deepcopy(record)
        bad['retired_sources'][0]['disposition'] = 'replaced'
        self.assertFalse(audit.documented_revision(old, new, bad))

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
            with self.assertRaisesRegex(ValueError, 'SHA 不符'):
                audit.audit()

    def test_recheck_may_append_sources_but_never_remove_or_reorder_prior_sources(self):
        old, new, record = self.fixture()
        old['source_ids'] = ['prior_a', 'prior_b']
        new['source_ids'] = ['prior_a', 'prior_b', 'new_statistics']
        self.assertTrue(audit.documented_revision(old, new, record))
        for ids in (['prior_b', 'prior_a'], ['prior_a'], ['prior_a', 'prior_b', 'prior_a']):
            with self.subTest(ids=ids):
                self.assertFalse(audit.documented_revision(old, dict(new, source_ids=ids), record))

    def test_appended_source_must_exist_and_match_manifest_and_review(self):
        record = next(r for r in audit.load(audit.ROOT, 'localization/retroactive-review-register-20261019.json')['substantive_rechecks'] if r['id'] == 'TW-23-010')
        item = next(i for i in audit.load(audit.ROOT, 'localization/tw-edition/runtime.json')['items'] if i['id'] == record['id'])
        original = audit.load
        for target in ('registry', 'manifest', 'review'):
            def altered(root, path):
                data = original(root, path)
                if target == 'registry' and path == 'localization/tw-edition/runtime.json':
                    data['sources'] = [s for s in data['sources'] if s['id'] != item['source_ids'][-1]]
                if target == 'manifest' and path == 'localization/manifest.json':
                    next(e for e in data['entries'] if e['id'] == item['id'])['sources'] = item['source_ids'][:-1]
                if target == 'review' and path == 'localization/reviews/' + item['id'] + '.json':
                    data['source_checks'] = data['source_checks'][:-1]
                return data
            with self.subTest(target=target), patch.object(audit, 'load', side_effect=altered):
                with self.assertRaisesRegex(ValueError, '追加來源'):
                    audit.validate_recheck_history(audit.ROOT, record, item)

    def test_date_only_update_never_counts_as_substantive_review(self):
        old, new, record = self.fixture()
        unchanged = dict(old, reviewed_at='2026-10-19')
        record['after_sha256'] = record['before_sha256']
        self.assertFalse(audit.documented_revision(old, unchanged, record))

if __name__ == '__main__': unittest.main()

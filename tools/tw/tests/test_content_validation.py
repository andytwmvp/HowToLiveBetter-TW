"""同一份反例同時跑Python與實際瀏覽器驗證函式，避免兩邊放行條件分歧。"""
from __future__ import annotations
import copy
from datetime import date, datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import content_validation as validation
import review_contract as contract
import edition

TODAY = date(2026, 10, 15)
ROOT = contract.ROOT


def fixture():
    return json.loads(subprocess.check_output(['git', 'show', '37d33f484ee85736170694754528f4392e8ee94d:localization/tw-edition/runtime.json'], cwd=ROOT, text=True))


class RuntimeValidationTests(unittest.TestCase):
    def test_shared_python_and_browser_rejections(self):
        original = fixture()
        edits = [
            ('家族史字串', ('items', 8, 'eligibility', 'family_history'), 'false'),
            ('家族史數字', ('items', 8, 'eligibility', 'family_history'), 1),
            ('未知條件', ('items', 0, 'eligibility'), {'unsupported': True}),
            ('年齡布林值', ('items', 3, 'eligibility', 'min_age'), True),
            ('年齡字串', ('items', 3, 'eligibility', 'min_age'), '40'),
            ('年齡小數', ('items', 3, 'eligibility', 'min_age'), 40.5),
            ('倒置年齡', ('items', 3, 'eligibility', 'max_age'), 39),
            ('指定年齡重複', ('items', 6, 'eligibility', 'ages'), [35, 35]),
            ('指定年齡空集合', ('items', 6, 'eligibility', 'ages'), []),
            ('沒有條件物件', ('items', 0, 'eligibility'), None),
            ('來源沒有主機', ('sources', 0, 'url'), 'https:///missing-host'),
            ('來源含帳密', ('sources', 0, 'url'), 'https://user:secret@example.org/path'),
            ('來源非HTTPS', ('sources', 0, 'url'), 'http://example.org/path'),
            ('來源反斜線', ('sources', 0, 'url'), 'https://example.org\\evil'),
            ('來源編碼損壞', ('sources', 0, 'url'), 'https://example.org/%GG'),
            ('來源只有空白', ('sources', 0, 'supports'), '  \t'),
            ('來源陣列錯型', ('sources',), {'id': 'bad'}),
            ('空閱讀清單', ('items',), []),
            ('資料版本布林', ('schema_version',), True),
            ('未核對狀態', ('items', 0, 'review_status'), 'draft'),
            ('標題空白', ('items', 0, 'title'), '   '),
            ('零年日期', ('sources', 0, 'published_at'), '0000-01-01'),
            ('日期不存在', ('items', 0, 'reviewed_at'), '2026-02-30'),
            ('緊湊日期', ('items', 0, 'reviewed_at'), '20261015'),
            ('未來查核', ('items', 0, 'reviewed_at'), '2026-10-16'),
            ('資料集逾期', ('review_due_at',), '2026-10-14'),
            ('單條逾期', ('items', 0, 'review_due_at'), '2026-10-14'),
            ('先審後查來源', ('items', 0, 'reviewed_at'), '2026-10-14'),
            ('來源發布日晚於查閱', ('sources', 0, 'published_at'), '2026-10-16'),
            ('來源ID字串代替陣列', ('items', 0, 'source_ids'), 'hpa_emergency'),
            ('重複條目來源', ('items', 0, 'source_ids'), ['hpa_emergency', 'hpa_emergency']),
            ('未知來源', ('items', 0, 'source_ids'), ['does_not_exist']),
            ('條目ID損壞', ('items', 0, 'id'), '../bad'),
            ('資料標題缺漏', ('title',), None),
        ]
        cases = [dict(name='有效資料', data=original, expected=True)]
        for name, path, value in edits:
            data = copy.deepcopy(original); target = data
            for part in path[:-1]: target = target[part]
            target[path[-1]] = value
            cases.append(dict(name=name, data=data, expected=False))
        for key in ('sources', 'items'):
            data = copy.deepcopy(original); data[key].append(copy.deepcopy(data[key][0]))
            cases.append(dict(name=key+'重複ID', data=data, expected=False))
        edge = copy.deepcopy(original); edge['review_due_at'] = TODAY.isoformat()
        for item in edge['items']: item['review_due_at'] = TODAY.isoformat()
        cases.append(dict(name='複查當日有效', data=edge, expected=True))
        numeric = copy.deepcopy(original); numeric['items'][3]['eligibility']['min_age'] = 40.0
        cases.append(dict(name='JSON整數值相容', data=numeric, expected=True))
        script = r'''
const fs=require('fs'); const {validate}=require('./assets/tw-runtime.js');
const input=JSON.parse(fs.readFileSync(0,'utf8'));
process.stdout.write(JSON.stringify(input.map(c=>{try{validate(c.data,'2026-10-15');return true;}catch(_){return false;}})));
'''
        result = subprocess.run(['node', '-e', script], cwd=ROOT, input=json.dumps(cases), text=True, capture_output=True, check=True)
        browser = json.loads(result.stdout)
        for case, accepted in zip(cases, browser, strict=True):
            with self.subTest(name=case['name']):
                try: validation.validate_runtime_data(case['data'], TODAY); python = True
                except ValueError: python = False
                self.assertEqual(python, case['expected'])
                self.assertEqual(accepted, case['expected'])

    def test_taipei_midnight_is_consistent(self):
        stamps = ['2026-10-15T15:59:59+00:00', '2026-10-15T16:00:00+00:00']
        expected = ['2026-10-15', '2026-10-16']
        self.assertEqual([validation.taipei_today(datetime.fromisoformat(s)).isoformat() for s in stamps], expected)
        script = "const {taipeiToday}=require('./assets/tw-runtime.js');console.log(JSON.stringify(process.argv.slice(1).map(s=>taipeiToday(new Date(s)))));"
        out = subprocess.check_output(['node', '-e', script, *stamps], cwd=ROOT, text=True)
        self.assertEqual(json.loads(out), expected)

    def test_invalid_anchor_does_not_break_validation(self):
        script = "const {decodeTarget}=require('./assets/tw-runtime.js');console.log(JSON.stringify(['#%EF','#TW-NAV-001','#other','#%54W-NAV-002'].map(decodeTarget)));"
        self.assertEqual(json.loads(subprocess.check_output(['node', '-e', script], cwd=ROOT, text=True)), [None, 'TW-NAV-001', None, 'TW-NAV-002'])

    def test_export_helpers_refuse_invalid_data_before_writing(self):
        data = fixture(); data['items'][8]['eligibility']['family_history'] = 'false'
        with tempfile.TemporaryDirectory() as d:
            output = Path(d) / 'should-not-exist'
            for builder in (edition.build_html, edition.build_epub, edition.build_anki):
                with self.subTest(builder=builder.__name__):
                    with self.assertRaises(ValueError): builder(output, data)
                    self.assertFalse(output.exists())

    def test_duplicate_json_fields_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'bad.json'; p.write_text('{"items": [], "items": [1]}')
            with self.assertRaises(ValueError): validation.load_json(p)


class ReviewBoundaryTests(unittest.TestCase):
    def make_review(self, root):
        path = root / 'locales/zh-TW/item.md'; path.parent.mkdir(parents=True)
        path.write_text('<!-- TW-ID: TW-01-001 -->\n測試正文。', encoding='utf-8')
        e = dict(id='TW-01-001', status='verified', target_path='locales/zh-TW/item.md', verified_at=TODAY.isoformat())
        review = dict(id=e['id'], reviewer='test-fixture', jurisdiction='TW', reviewed_at=TODAY.isoformat(), review_due_at='2027-01-15', target_path=e['target_path'], target_sha256=hashlib.sha256(path.read_bytes()).hexdigest(), source_checks=[dict(url='https://example.org/evidence', claim='測試主張', supporting_passage='測試段落，非實際來源證據', accessed_at=TODAY.isoformat())])
        target = root / 'localization/reviews/TW-01-001.json'; target.parent.mkdir(parents=True)
        target.write_text(json.dumps(review), encoding='utf-8')
        return e, review, target

    def test_paths_cannot_leave_namespace_inside_repo(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); self.make_review(root)
            (root / 'README.md').write_text('outside namespace')
            with self.assertRaises(ValueError): contract.safe_path(root, 'locales/zh-TW/../../README.md', 'locales/zh-TW/')
            link = root / 'locales/zh-TW/link.md'; link.symlink_to(root / 'README.md')
            with self.assertRaises(ValueError): contract.safe_path(root, 'locales/zh-TW/link.md', 'locales/zh-TW/')

    def test_review_directory_cannot_be_redirected(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); outside = root / 'other'; outside.mkdir(); (outside / 'x.json').write_text('{}')
            (root / 'localization').mkdir(); (root / 'localization/reviews').symlink_to(outside, target_is_directory=True)
            with self.assertRaises(ValueError): contract.safe_path(root, 'localization/reviews/x.json', 'localization/reviews/')

    def test_blank_and_malformed_evidence_is_rejected(self):
        modifications = [dict(reviewer=' '), dict(source_checks='not-an-array'), dict(source_checks=[{}]), dict(reason=' ', status='not_applicable')]
        for change in modifications:
            with self.subTest(change=change), tempfile.TemporaryDirectory() as d:
                root = Path(d); e, review, p = self.make_review(root)
                if 'status' in change: e['status'] = change['status']
                review.update(change); p.write_text(json.dumps(review))
                with self.assertRaises(ValueError): contract.validate_entry(e, root, TODAY)

    def test_source_cannot_be_checked_after_review(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); e, review, p = self.make_review(root)
            e['verified_at'] = review['reviewed_at'] = '2026-10-14'; p.write_text(json.dumps(review))
            with self.assertRaises(ValueError): contract.validate_entry(e, root, TODAY)

    def test_publication_rejects_duplicate_runtime_or_unreviewed_source(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); e, _, _ = self.make_review(root)
            data = fixture(); data['sources'] = [dict(id='test', title='測試來源', supports='測試範圍', url='https://example.org/evidence', accessed_at=TODAY.isoformat(), published_at=None)]
            item = data['items'][0]; item.update(id=e['id'], target_path=e['target_path'], body=(root/e['target_path']).read_text(), source_ids=['test'])
            data['items'] = [item]
            target = root / 'localization/tw-edition/runtime.json'; target.parent.mkdir(parents=True)
            target.write_text(json.dumps(data))
            self.assertTrue(contract.publication_report(root, {'entries':[e]})['publication_ready'])
            data['items'].append(copy.deepcopy(item)); target.write_text(json.dumps(data))
            self.assertFalse(contract.publication_report(root, {'entries':[e]})['publication_ready'])
            data['items'].pop(); data['sources'][0]['url'] = 'https://example.org/different'; target.write_text(json.dumps(data))
            self.assertFalse(contract.publication_report(root, {'entries':[e]})['publication_ready'])

    def test_malformed_review_reports_blocker_not_traceback(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); e, _, p = self.make_review(root); p.write_text('[]')
            report = contract.publication_report(root, {'entries':[e]})
            self.assertFalse(report['publication_ready']); self.assertTrue(report['publication_blockers'])



class RawJsonTests(unittest.TestCase):
    def assert_parsers(self, examples):
        script = "const fs=require('fs');const {parseRuntimeJson}=require('./assets/tw-runtime.js');const rows=JSON.parse(fs.readFileSync(0,'utf8'));console.log(JSON.stringify(rows.map(x=>{try{parseRuntimeJson(x[0]);return true;}catch(_){return false;}})));"
        output = subprocess.check_output(['node', '-e', script], input=json.dumps(examples), cwd=ROOT, text=True)
        results = json.loads(output)
        with tempfile.TemporaryDirectory(prefix='tw-raw-json-') as folder:
            path = Path(folder) / 'case.json'
            for (raw, expected), accepted in zip(examples, results, strict=True):
                with self.subTest(raw=raw):
                    path.write_text(raw, encoding='utf-8')
                    try: validation.load_json(path); python = True
                    except ValueError: python = False
                    self.assertEqual(python, expected)
                    self.assertEqual(accepted, expected)

    def test_unique_nested_keys_and_escaped_strings(self):
        sample = {'outer': {'id': 1}, 'list': [{'id': 2}, {'id': 3}], 'text': '文字包含 "quoted" : {} [] \\ 與換行\n，不是欄位'}
        self.assert_parsers([(json.dumps(sample), True), ('{"a":1,"A":2,"\\u03b1":3}', True)])

    def test_duplicate_root_keys(self):
        self.assert_parsers([('{"status":"draft","status":"source_checked"}', False)])

    def test_duplicate_nested_keys(self):
        self.assert_parsers([('{"items":[{"id":"a","id":"b"}]}', False)])

    def test_escaped_equivalent_keys(self):
        self.assert_parsers([(r'{"id":1,"\u0069d":2}', False), (r'{"a":1,"\u0061":2}', False)])

    def test_overflow_rejected_but_finite_numbers_allowed(self):
        self.assert_parsers([('{"x":1e309}', False), ('{"x":[-1e400]}', False), ('{"x":1e308,"small":1e-308}', True)])

    def test_invalid_json_syntax(self):
        self.assert_parsers([('{"a":NaN}', False), ('{"a":Infinity}', False), ('{"a":1,}', False), ('{"a":"unterminated}', False)])

if __name__ == '__main__': unittest.main()

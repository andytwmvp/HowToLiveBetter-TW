"""稽核修復：安全入口、日常查核狀態、替代文字及輸出驗收。"""
from contextlib import closing
import copy
import hashlib
import json
import sqlite3
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch
from xml.etree import ElementTree as ET
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import review_contract as contract
import edition
import image_copy
ROOT=contract.ROOT

class ReviewTests(unittest.TestCase):
    def fixture(self,folder):
        root=Path(folder);target='locales/zh-TW/item.md'
        path=root/target;path.parent.mkdir(parents=True);path.write_text('<!-- TW-ID: TW-01-001 -->\n測試正文。',encoding='utf-8')
        (root/'localization/reviews').mkdir(parents=True)
        e={'id':'TW-01-001','status':'verified','target_path':target,'verified_at':'2026-10-15'}
        review={'id':e['id'],'reviewer':'test-fixture','jurisdiction':'TW','reviewed_at':'2026-10-15','review_due_at':'2099-01-01','target_path':target,'target_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'source_checks':[{'url':'https://example.org/source','claim':'測試用主張','supporting_passage':'測試用支持段落，不是實際查核','accessed_at':'2026-10-15'}]}
        (root/'localization/reviews/TW-01-001.json').write_text(json.dumps(review),encoding='utf-8')
        return root,e,review
    def test_draft_target_is_allowed(self):
        with tempfile.TemporaryDirectory() as d:
            root,e,_=self.fixture(d);e.update(status='draft',verified_at=None)
            self.assertFalse(contract.validate_entry(e,root))
    def test_verified_status_can_advance(self):
        with tempfile.TemporaryDirectory() as d:
            root,e,_=self.fixture(d);self.assertTrue(contract.validate_entry(e,root))
    def test_verified_without_evidence_fails(self):
        with tempfile.TemporaryDirectory() as d:
            root,e,_=self.fixture(d);(root/'localization/reviews/TW-01-001.json').unlink()
            with self.assertRaises(ValueError):contract.validate_entry(e,root)
    def test_changed_body_fails_review(self):
        with tempfile.TemporaryDirectory() as d:
            root,e,_=self.fixture(d);(root/e['target_path']).write_text('changed')
            with self.assertRaises(ValueError):contract.validate_entry(e,root)
    def test_path_escape_fails(self):
        with tempfile.TemporaryDirectory() as d:
            root,e,_=self.fixture(d);e['target_path']='locales/zh-TW/../../../../etc/passwd'
            with self.assertRaises(ValueError):contract.validate_entry(e,root)
    def test_readiness_is_computed(self):
        with tempfile.TemporaryDirectory() as d:
            root,e,_=self.fixture(d);p=root/'localization/tw-edition/runtime.json';p.parent.mkdir(parents=True)
            data=copy.deepcopy(contract.validate_runtime())
            data['sources']=[{'id':'test','url':'https://example.org/source','title':'測試來源','supports':'測試範圍','accessed_at':'2026-10-15','published_at':None}]
            item=data['items'][0];item.update(id=e['id'],target_path=e['target_path'],body=(root/e['target_path']).read_text(),source_ids=['test'],reviewed_at=e['verified_at'])
            data['items']=[item];p.write_text(json.dumps(data))
            self.assertTrue(contract.publication_report(root,{'entries':[e]})['publication_ready'])
            p.write_text('{"items":[]}')
            self.assertFalse(contract.publication_report(root,{'entries':[e]})['publication_ready'])
    def test_real_book_is_not_complete(self):self.assertFalse(contract.publication_report()['publication_ready'])

class ImageTests(unittest.TestCase):
    def wrong_alt(self,key):
        original=image_copy.read
        def replaced(path):
            text=original(path)
            if path=='index.html':
                from html import escape
                alt=escape(image_copy.load_spec()['alt'],quote=True)
                text=text.replace(f'{key}" content="{alt}"',f'{key}" content="不一致的替代文字"')
            return text
        with patch.object(image_copy,'read',side_effect=replaced):
            with self.assertRaises(RuntimeError):image_copy.check()
    def test_wrong_og_alt_fails(self):self.wrong_alt('og:image:alt')
    def test_wrong_twitter_alt_fails(self):self.wrong_alt('twitter:image:alt')
    def test_image_check_does_not_freeze_manifest(self):
        original=image_copy.git
        def guarded(*args):
            if 'localization/manifest.json' in args:raise RuntimeError('圖片檢查不應鎖住內容進度')
            return original(*args)
        with patch.object(image_copy,'git',side_effect=guarded):image_copy.check()
    def test_runtime_metadata(self):
        import re
        page=(ROOT/'index.html').read_text();meta=json.loads(re.search(r'<script type="application/ld\+json">(.*?)</script>',page,re.S)[1])
        self.assertNotIn('numberOfPages',meta);self.assertEqual(meta['name'],image_copy.load_spec()['title'])
        self.assertNotIn('失業兜底',json.dumps(meta,ensure_ascii=False))

class RuntimeTests(unittest.TestCase):
    def test_runtime_checked_sources(self):
        data=contract.validate_runtime();self.assertGreaterEqual(len(data['items']),21)
        self.assertTrue(({f'TW-NAV-{n:03}' for n in range(1,10)}|{f'TW-14-{n:03}' for n in range(1,13)}).issubset({e['id'] for e in data['items']}))
    def test_missing_source_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);p=root/'localization/tw-edition/runtime.json';p.parent.mkdir(parents=True)
            data=copy.deepcopy(contract.validate_runtime());data['items'][0]['source_ids']=['missing'];p.write_text(json.dumps(data))
            with self.assertRaises(ValueError):contract.validate_runtime(root)
    def test_active_skill_is_taiwan_only(self):
        text=(ROOT/'skills/life-decision-guide/SKILL.md').read_text()
        self.assertIn('1925',text);self.assertIn('119',text);self.assertNotIn('12356',text)
        self.assertNotIn('eternity4719/HowToLiveBetter.git',text)
        self.assertIn('runtime.json',text)
    def test_screening_boundaries_data(self):
        rows={e['id']:e for e in contract.validate_runtime()['items']}
        self.assertEqual(rows['TW-NAV-004']['eligibility'],{'sex':'f','min_age':40,'max_age':74})
        self.assertEqual(rows['TW-NAV-005']['eligibility'],{'sex':'f','min_age':25,'max_age':29})
        self.assertEqual(rows['TW-NAV-006']['eligibility'],{'sex':'f','min_age':30})
    def test_exports_use_same_catalog_ids(self):
        data=contract.validate_runtime();ids={e['id'] for e in data['items']}
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            edition.build_html(root/'tw.html',data)
            html=(root/'tw.html').read_text();self.assertNotIn('window.__CORPUS__=',html)
            self.assertIn('window.__TW_RUNTIME__=',html)
            self.assertIn('內容最後確認日期',html);self.assertIn('建議再次確認日期',html)
            edition.build_epub(root/'tw.epub',data)
            with zipfile.ZipFile(root/'tw.epub') as z:
                self.assertEqual(z.namelist()[0],'mimetype');self.assertEqual(z.getinfo('mimetype').compress_type,zipfile.ZIP_STORED)
                for p in z.namelist():
                    if p.endswith(('.xml','.xhtml','.opf')):ET.fromstring(z.read(p))
                tree=ET.fromstring(z.read('OEBPS/content.xhtml'))
                self.assertEqual({e.attrib['id'] for e in tree.findall('.//{http://www.w3.org/1999/xhtml}section')},ids)
                epub_text=z.read('OEBPS/content.xhtml').decode()
                self.assertIn('內容最後確認日期',epub_text);self.assertIn('建議再次確認日期',epub_text)
            edition.build_anki(root/'tw.apkg',data)
            with zipfile.ZipFile(root/'tw.apkg') as z:(root/'deck.sqlite').write_bytes(z.read('collection.anki2'))
            with closing(sqlite3.connect(root/'deck.sqlite')) as db:
                self.assertEqual(db.execute('PRAGMA integrity_check').fetchone()[0],'ok')
                rows=db.execute('SELECT guid,data,flds FROM notes').fetchall()
                self.assertEqual({r[1] for r in rows},ids)
                self.assertTrue(all(r[0] == 'hltb-tw-' + r[1] for r in rows))
                self.assertTrue(all('https://' in r[2] for r in rows))
                self.assertTrue(all('內容最後確認日期' in r[2] and '建議再次確認日期' in r[2] for r in rows))

if __name__=='__main__':unittest.main()

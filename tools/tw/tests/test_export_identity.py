"""本fork來源匯出的識別碼須與上游、臺灣導航隔離，重複建置保持穩定。"""
from contextlib import closing
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from xml.etree import ElementTree as ET
from zipfile import ZipFile
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from review_contract import ROOT,validate_runtime
from edition import build_anki,build_epub,freshness_copy

class ExportIdentityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory(prefix='tw-export-identity-')
        cls.addClassCleanup(cls.temp.cleanup)
        cls.folder=Path(cls.temp.name)
        for kind,suffix in [('anki','apkg'),('epub','epub')]:
            for name in ('first','second'):
                subprocess.run(['node',f'tools/{kind}/build.mjs','--source-preview',str(cls.folder/f'{name}.{suffix}')],cwd=ROOT,check=True,stdout=subprocess.DEVNULL)
        build_anki(cls.folder/'nav.apkg',validate_runtime())
        build_epub(cls.folder/'nav.epub',validate_runtime())

    def deck(self,name):
        with ZipFile(self.folder/name) as z:
            p=self.folder/(name+'.sqlite');p.write_bytes(z.read('collection.anki2'))
        with closing(sqlite3.connect(p)) as db:
            self.assertEqual(db.execute('PRAGMA integrity_check').fetchone()[0],'ok')
            notes=db.execute('SELECT id,guid,mid FROM notes ORDER BY id').fetchall()
            cards=db.execute('SELECT id,nid,did FROM cards ORDER BY id').fetchall()
            models,decks=db.execute('SELECT models,decks FROM col').fetchone()
        return notes,cards,json.loads(models),json.loads(decks)

    def epub_metadata(self,name):
        with ZipFile(self.folder/name) as z:
            opf=ET.fromstring(z.read('OEBPS/content.opf'))
            uid=opf.find('{http://www.idpf.org/2007/opf}metadata/{http://purl.org/dc/elements/1.1/}identifier').text
            title=opf.find('{http://www.idpf.org/2007/opf}metadata/{http://purl.org/dc/elements/1.1/}title').text
            ncx=z.read('OEBPS/toc.ncx').decode() if 'OEBPS/toc.ncx' in z.namelist() else ''
        return uid,title,ncx

    def test_freshness_copy_keeps_a_future_due_date_reminder_in_static_exports(self):
        entry={'reviewed_at':'2026-10-27','review_due_at':'2026-10-29'}
        before=freshness_copy(entry,'2026-10-28')
        due=freshness_copy(entry,'2026-10-29')
        self.assertIn('內容最後確認日期：2026-10-27',before)
        self.assertIn('建議再次確認日期：2026-10-29',before)
        self.assertIn('到建議再次確認日期後',before)
        self.assertNotIn('已到再次確認日期',before)
        self.assertIn('已到再次確認日期',due)
        self.assertIn('向主管機關或服務單位確認最新資訊',due)

    def test_source_anki_namespace_and_repeatability(self):
        first=self.deck('first.apkg');second=self.deck('second.apkg');nav=self.deck('nav.apkg')
        self.assertEqual(len(first[0]),765)
        self.assertEqual(first[0],second[0]);self.assertEqual(first[1],second[1])
        self.assertTrue(all(guid.startswith('hltb-tw-source-v1-') for _,guid,_ in first[0]))
        for index,position in [(0,0),(0,1),(0,2),(1,0),(1,2)]:
            self.assertFalse({row[position] for row in first[index]} & {row[position] for row in nav[index]})
        self.assertNotIn('1759900000001',first[2])
        self.assertNotIn('1759900000100',first[3])

    def test_source_anki_displays_scope_and_import_guidance(self):
        _,_,models,decks=self.deck('first.apkg')
        for model in models.values():
            for template in model['tmpls']:
                for key in ('qfmt','afmt'):
                    self.assertIn('原作內容對照卡',template[key])
                    self.assertIn('閱讀說明',template[key])
        root=decks['1792060000100']
        self.assertIn('原作繁體中文對照預覽',root['name'])
        self.assertIn('不代表臺灣現行制度或生活建議',root['desc'])
        self.assertIn('閱讀說明',root['desc'])
        self.assertIn('獨立識別碼',root['desc'])
        self.assertIn('匯入前請先備份',root['desc'])
        self.assertIn('不會自動搬移',root['desc'])
        self.assertNotIn('生成於',root['desc'])
        self.assertNotIn('正文提交',root['desc'])

    def test_source_epub_identity_is_stable_and_separate(self):
        first=self.epub_metadata('first.epub');second=self.epub_metadata('second.epub');nav=self.epub_metadata('nav.epub')
        self.assertEqual(first[0],second[0])
        self.assertEqual(first[0],'urn:uuid:cee8db2b-5e19-59ea-ad9f-b3f59b53f469')
        self.assertNotEqual(first[0],nav[0])
        self.assertNotEqual(first[0],'urn:uuid:5c0c1c0e-6a5c-4d2b-9b1e-7d1f0a4e8c31')
        self.assertIn('原作繁體中文對照預覽',first[1]);self.assertIn(first[0],first[2])

if __name__=='__main__':unittest.main()

"""防止錯誤網址拼接、HTML屬性遺失及EPUB內部跳轉失效再次漏檢。"""
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest
from zipfile import ZipFile,ZIP_STORED
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from check_export_integrity import check_html,check_epub,HtmlReferences
from traditionalize import ROOT

class ExportIntegrityTests(unittest.TestCase):
    def html_fixture(self,value):
        with tempfile.TemporaryDirectory(prefix='tw-link-test-') as folder:
            p=Path(folder)/'sample.html';p.write_text(value,encoding='utf-8');return check_html(p)
    def test_concatenated_document_url_rejected(self):
        with self.assertRaises(ValueError):self.html_fixture('<a href="https://github.com/a/b/blob/main/REPOSITORY_GUIDE.mdselfcheck.html">自查</a>')
    def test_lost_href_attribute_rejected(self):
        with self.assertRaises(ValueError):self.html_fixture('<a https://github.com/a/b>回報</a>')
    def test_offline_relative_dependency_rejected(self):
        with self.assertRaises(ValueError):self.html_fixture('<script src="missing.js"></script>')
    def test_offline_remote_script_rejected(self):
        with self.assertRaises(ValueError):self.html_fixture('<script src="https://example.org/remote.js"></script>')
    def test_offline_remote_stylesheet_rejected(self):
        with self.assertRaises(ValueError):self.html_fixture('<link rel="stylesheet" href="https://example.org/main.css">')
    def test_valid_absolute_and_fragment(self):
        self.assertEqual(self.html_fixture('<a href="#cards">目錄</a><a href="https://example.org/guide">說明</a>')['html_references'],2)
    def test_source_html_real_output(self):
        with tempfile.TemporaryDirectory(prefix='tw-source-links-') as folder:
            output=Path(folder)/'source.html'
            subprocess.run(['node','tools/offline/build.mjs','--source-preview',str(output)],cwd=ROOT,check=True,stdout=subprocess.DEVNULL)
            check_html(output)
            text=output.read_text(encoding='utf-8');parser=HtmlReferences();parser.feed(text)
            self.assertTrue(any(value.endswith('/SUPPORT.md') for _,_,value in parser.links))
            match=re.search(r'window\.__CORPUS__=(.*)</script>\n<script>',text)
            self.assertIsNotNone(match)
            data=json.loads(match[1]);self.assertEqual(len(data['parts']),34)
            self.assertEqual(sum(len(re.findall(r'^### ',part,re.M)) for part in data['parts'].values()),765)
    def make_epub(self,path,reference):
        with ZipFile(path,'w') as z:
            z.writestr('mimetype','application/epub+zip',compress_type=ZIP_STORED)
            z.writestr('OEBPS/a.xhtml',f'<html xmlns="http://www.w3.org/1999/xhtml"><body><h1 id="topic">主題</h1><a href="{reference}">跳轉</a></body></html>')
    def test_epub_anchor_rejected(self):
        with tempfile.TemporaryDirectory(prefix='tw-epub-link-') as d:
            p=Path(d)/'test.epub';self.make_epub(p,'#missing')
            with self.assertRaises(ValueError):check_epub(p)
    def test_epub_file_rejected(self):
        with tempfile.TemporaryDirectory(prefix='tw-epub-link-') as d:
            p=Path(d)/'test.epub';self.make_epub(p,'missing.xhtml')
            with self.assertRaises(ValueError):check_epub(p)
    def test_epub_valid_anchor(self):
        with tempfile.TemporaryDirectory(prefix='tw-epub-link-') as d:
            p=Path(d)/'test.epub';self.make_epub(p,'#topic')
            self.assertEqual(check_epub(p)['internal_references'],1)

if __name__=='__main__':unittest.main()

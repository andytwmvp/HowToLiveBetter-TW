#!/usr/bin/env python3
"""驗證實際離線HTML及EPUB內部路徑／錨點，不以成功打包當成連結可用。"""
from __future__ import annotations
import argparse
import json
from html.parser import HTMLParser
from pathlib import Path, PurePosixPath
import posixpath
from urllib.parse import unquote, urlsplit
from xml.etree import ElementTree as ET
from zipfile import ZipFile, ZIP_STORED

class HtmlReferences(HTMLParser):
    def __init__(self):
        super().__init__();self.links=[];self.invalid=[]
    def handle_starttag(self,tag,attrs):
        values=dict(attrs)
        if any(key.startswith(('https:','http:')) for key in values):
            self.invalid.append('URL被寫成HTML屬性名稱，而不是href或src')
        for key in ('href','src'):
            value=values.get(key)
            if value is not None:self.links.append((tag,key,value))

def check_html(path: Path) -> dict:
    parser=HtmlReferences();parser.feed(path.read_text(encoding='utf-8'))
    errors=list(parser.invalid)
    for tag,key,value in parser.links:
        if not value or value.startswith('#'):continue
        parts=urlsplit(value)
        if not parts.scheme:errors.append('離線HTML仍依賴相對外部檔案：'+value)
        elif parts.scheme not in {'https','http','mailto','data'}:errors.append('不支援的離線連結協定：'+value)
        if '.mdselfcheck.html' in parts.path or '.mdsource.html' in parts.path:
            errors.append('文件URL被錯當成網站根目錄：'+value)
    if errors:raise ValueError(str(path)+':\n'+'\n'.join(errors))
    return {'file':str(path),'html_references':len(parser.links)}

def check_epub(path: Path) -> dict:
    with ZipFile(path) as archive:
        names=archive.namelist()
        if not names or names[0]!='mimetype' or archive.getinfo('mimetype').compress_type!=ZIP_STORED or archive.read('mimetype')!=b'application/epub+zip':
            raise ValueError('EPUB mimetype順序或內容不正確')
        if len(names)!=len(set(names)) or any(n.startswith('/') or '..' in PurePosixPath(n).parts for n in names):
            raise ValueError('EPUB含重複或越界檔名')
        xml={name:ET.fromstring(archive.read(name)) for name in names if name.endswith(('.xhtml','.xml','.opf','.ncx'))}
        ids={}
        for name,tree in xml.items():
            keys=[node.get('id') or node.get('{http://www.w3.org/XML/1998/namespace}id') for node in tree.iter()]
            keys=[key for key in keys if key]
            if len(keys)!=len(set(keys)):raise ValueError('EPUB同一文件有重複ID：'+name)
            ids[name]=set(keys)
        checked=0
        for name,tree in xml.items():
            for node in tree.iter():
                for key in ('href','src','full-path'):
                    value=node.get(key)
                    if value is None:continue
                    parts=urlsplit(value)
                    if parts.scheme or parts.netloc:continue
                    if key=='full-path':target=unquote(parts.path)
                    else:target=posixpath.normpath(posixpath.join(posixpath.dirname(name),unquote(parts.path))) if parts.path else name
                    if target not in names:raise ValueError(f'EPUB內部檔案不存在：{name} -> {value}')
                    if parts.fragment and unquote(parts.fragment) not in ids.get(target,set()):
                        raise ValueError(f'EPUB錨點不存在：{name} -> {value}')
                    checked+=1
    return {'file':str(path),'xml_documents':len(xml),'internal_references':checked}

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('files',nargs='+',type=Path);parser.add_argument('--report',type=Path);args=parser.parse_args()
    results=[]
    for path in args.files:
        if not path.is_file():raise FileNotFoundError('缺少應驗證的輸出：'+str(path))
        if path.suffix=='.epub':results.append(check_epub(path))
        elif path.suffix in {'.html','.htm'}:results.append(check_html(path))
        else:raise ValueError('只接受HTML或EPUB')
    text=json.dumps({'checks':results,'scope':'檔案結構與內部連結；不等於外站HTTP或全書內容查核'},ensure_ascii=False,indent=2)
    if args.report:args.report.parent.mkdir(parents=True,exist_ok=True);args.report.write_text(text+'\n',encoding='utf-8')
    print(text)

if __name__=='__main__':main()

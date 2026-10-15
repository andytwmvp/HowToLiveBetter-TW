#!/usr/bin/env python3
"""檢查實際匯出物內的repo目的地，避免模板正確但產物連回上游或不存在路徑。"""
from review_contract import validate_runtime
from contextlib import closing
from html import unescape
import json
import sqlite3
import tempfile
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET
from urllib.parse import urlsplit
from link_policy import ROOT,CONFIG,read,HtmlLinks,own_target,upstream_kind

def check_references(text,label,policy):
    parser=HtmlLinks();parser.feed(text);count=0
    for value in parser.links:
        u=urlsplit(unescape(value))
        if u.scheme in {'http','https'}:
            if upstream_kind(value,policy):raise ValueError(label+':匯出物仍含上游導覽')
            own_target(value,policy,ROOT);count+=1
        elif not u.scheme and u.path and label.endswith('.html'):
            raise ValueError(label+':離線單檔殘留相對外部檔案連結 '+value)
    return count

def main():
    policy=json.loads(read(CONFIG));counts={}
    runtime_ids={e['id'] for e in validate_runtime()['items']}
    for name in ('tw-source-preview.html','HowToLiveBetter-TW.html'):
        path=ROOT/'dist'/name
        if not path.is_file():raise ValueError('尚未生成：'+name)
        counts[name]=check_references(path.read_text(),name,policy)
    for name,expected in [('HowToLiveBetter-source-preview.epub',None),('HowToLiveBetter-TW.epub',len(runtime_ids))]:
        count=0;sections=0;section_ids=[]
        with zipfile.ZipFile(ROOT/'dist'/name) as z:
            for path in z.namelist():
                if path.endswith(('.xml','.opf','.xhtml')):
                    tree=ET.fromstring(z.read(path))
                    if path.endswith('.xhtml'):
                        count+=check_references(z.read(path).decode(),name+'/'+path,policy)
                        elements=tree.findall('.//{http://www.w3.org/1999/xhtml}section')
                        sections+=len(elements);section_ids.extend(e.get('id') for e in elements)
        if expected is not None and (sections!=expected or set(section_ids)!=runtime_ids):raise ValueError('臺灣EPUB項目數不同步')
        counts[name]=count
    for name,expected in [('HowToLiveBetter-source-preview.apkg',765),('HowToLiveBetter-TW.apkg',len(runtime_ids))]:
        with tempfile.TemporaryDirectory(prefix='htlb-link-output-') as temp:
            database=Path(temp)/'collection.anki2'
            with zipfile.ZipFile(ROOT/'dist'/name) as z:database.write_bytes(z.read('collection.anki2'))
            with closing(sqlite3.connect(database)) as db:
                if db.execute('PRAGMA integrity_check').fetchone()[0]!='ok':raise ValueError('Anki資料庫不完整')
                rows=db.execute('SELECT flds FROM notes').fetchall()
                if name=='HowToLiveBetter-TW.apkg' and {r[0] for r in db.execute('SELECT data FROM notes')}!=runtime_ids:raise ValueError('臺灣Anki條目ID與閱讀資料不一致')
                if len(rows)!=expected:raise ValueError('Anki條目數不同步')
                count=sum(check_references(row[0],name,policy) for row in rows)
                metadata=db.execute('SELECT decks FROM col').fetchone()[0]
                count+=check_references(' '.join(str(d.get('desc','')) for d in json.loads(metadata).values()),name,policy)
            counts[name]=count
    print('PASS：匯出物repo連結、離線相對路徑、EPUB/XML及Anki來源目標：'+json.dumps(counts,ensure_ascii=False))

if __name__=='__main__':main()

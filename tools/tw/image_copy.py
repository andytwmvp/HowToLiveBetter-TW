#!/usr/bin/env python3
"""圖片臺灣文案與實際資產的唯讀驗證，不凍結正文編修進度。"""
from __future__ import annotations
import argparse
import hashlib
import html
import json
import re
import subprocess
from urllib.parse import quote
from html.parser import HTMLParser
from traditionalize import ROOT, read, git
START='510111a8bd1003fff5e9adef8b95f6ffc489afba'
SPEC='localization/image-copy.zh-TW.json'
REPORT='localization/image-copy-report.json'

def load_spec(): return json.loads(read(SPEC))

def statistics():
    chapters=sorted((ROOT/'book').glob('*.md'))
    counts={'entries':0,'A':0,'B':0,'C':0,'links':0}
    for chapter in chapters:
        for line in chapter.read_text(encoding='utf-8').splitlines():
            if line.startswith('### '): counts['entries']+=1
            match=re.match(r'^- 證據等級：([ABC])',line)
            if match: counts[match[1]]+=1
            if re.match(r'^- (來源|備註)：',line): counts['links']+=len(re.findall(r'https?://',line))
    if not chapters or counts['entries']!=sum(counts[g] for g in 'ABC'): raise RuntimeError('原作統計不一致')
    return counts

def badge_lines(spec,counts):
    result=[]
    for badge in spec['badges']:
        message=badge['message'].format(**counts);label=badge['label']
        url='https://img.shields.io/badge/'+quote(label,safe='')+'-'+quote(message,safe='')+'-'+badge['color']+'?style=flat-square'
        result.append(f"[![{label}：{message}]({url})]({badge['destination']})")
    return result

class Metadata(HTMLParser):
    def __init__(self): super().__init__();self.values={}
    def handle_starttag(self,tag,attrs):
        values=dict(attrs)
        if tag=='meta':
            key=values.get('property') or values.get('name')
            self.values.setdefault(key,[]).append(values.get('content'))

def check():
    spec=load_spec();counts=statistics();template=read('tools/og.html')
    for value in [spec['title'],*spec['headline'],*spec['topics']]:
        if html.escape(value) not in template: raise RuntimeError('模板文案未同步：'+value)
    for token in ('性價比','長壽防病','法律紅線','失業兜底','戀愛婚育','換回壽命'):
        if token in template: raise RuntimeError('舊圖片用語殘留：'+token)
    if any(token in template for token in ('data-stat=', '原作統計不代表臺灣現況')): raise RuntimeError('封面不應呈現原作數字或維護狀態說明')
    md=read('README.md')
    for line in badge_lines(spec,counts):
        if line not in md: raise RuntimeError('徽章文案或來源範圍不同步')
    if html.escape(spec['alt'],quote=True) not in md: raise RuntimeError('README alt未同步')
    for page_name in ('index.html','selfcheck.html'):
        page=read(page_name);metadata=Metadata();metadata.feed(page)
        for key in ('og:image:alt','twitter:image:alt'):
            if metadata.values.get(key)!=[spec['alt']]: raise RuntimeError('分享圖片替代文字不同步、缺漏或重複：'+key)
        for key in ('og:title','og:description','twitter:title','twitter:description'):
            values=metadata.values.get(key,[])
            if len(values)!=1 or not values[0]: raise RuntimeError('分享文案缺漏或重複：'+key)
            if any(token in values[0] for token in ('性價比','失業兜底','戀愛婚育','法律紅線')): raise RuntimeError('分享文案殘留舊用語')
    # 原始授權與圖片來源保持可追溯；manifest進度由內容審閱契約驗證。
    for path in ('LICENSE','LICENSE-CODE'):
        if (ROOT/path).read_bytes()!=git('show',f'{START}:{path}'): raise RuntimeError('授權檔不應被圖片工作變更')
    raw=(ROOT/'og.png').read_bytes()
    if raw==git('show',f'{START}:og.png'): raise RuntimeError('實際圖片尚未重新產生')
    report=json.loads(read(REPORT));digest=lambda data:hashlib.sha256(data).hexdigest()
    if report['image_sha256']!=digest(raw) or report['template_sha256']!=digest(template.encode()): raise RuntimeError('模板與實際圖片版本對不上')
    if report['spec_sha256']!=digest((ROOT/SPEC).read_bytes()): raise RuntimeError('圖片規格變更後尚未重新產圖')
    subprocess.run(['node','tools/sync-stats.mjs','--check'],cwd=ROOT,check=True,stdout=subprocess.DEVNULL)
    print('PASS：臺灣圖片文案、三個徽章、實際替代文字值、PNG／模板／規格雜湊、原作統計及授權一致。')

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--check',action='store_true');args=parser.parse_args()
    if not args.check: parser.error('只接受--check；一次性寫入入口已退休')
    check()

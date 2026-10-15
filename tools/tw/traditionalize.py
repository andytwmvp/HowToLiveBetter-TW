#!/usr/bin/env python3
"""唯讀來源保全與內容契約檢查；舊版自動轉字遷移已退休。"""
from __future__ import annotations
import argparse
from functools import lru_cache
import json
import re
import subprocess
from collections import Counter
from html import unescape
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote
ROOT = Path(__file__).resolve().parents[2]
BASE = '1271250f082732b50b1fda851453d4b4b8f1eefd'
UPSTREAM = '3f59f98be11305902681a8f20ed073c4c4588eee'
REPO = 'andytwmvp/HowToLiveBetter-TW'
BRANCH = 'tw/zh-hant-ui-and-assets'
SUFFIXES = {'.css', '.yml', '.html', '.xml', '.svg', '.md', '.js', '.txt', '.py', '.typ', '.json', '.mjs', '.yaml'}
IMAGE_SUFFIXES = {'.jpg', '.gif', '.svg', '.ico', '.jpeg', '.avif', '.png', '.webp'}
NOTICE = '> **繁體字形轉換稿，非台灣制度定稿。** 本頁保留原作的論述、數字與來源；中國大陸法規、補助、客服電話及醫療制度尚未完成台灣查核，不可直接當作台灣現行依據。來源引文亦經字形轉換，精確原文請查固定版本與所附來源。\n\n'
UI_WORDS = {'鏈接': '連結', '軟件': '軟體', '硬件': '硬體', '網絡': '網路', '登錄': '登入', '默認': '預設', '加載': '載入', '鼠標': '滑鼠', '服務器': '伺服器', '用戶': '使用者', '文檔': '文件', '視頻': '影片', '在線': '線上', '緩存': '快取', '信息': '資訊', '短信': '簡訊', '創建': '建立', '身份證': '身分證', '睡眠質量': '睡眠品質'}
URL = re.compile('https?://(?:[^\\s<>"\'`()\\[\\]{}，。；：、（）「」『』\\\\]+|\\([^()\\s<>]*\\))+')


def git(*args): return subprocess.check_output(['git',*args],cwd=ROOT)
def read(path): return (ROOT/path).read_text(encoding='utf-8')
def write(path,text):
    dest=ROOT/path;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_text(text.rstrip()+'\n',encoding='utf-8')
def dump(path,value): write(path,json.dumps(value,ensure_ascii=False,indent=2))
def current_files():
    return sorted({p for p in git('ls-files','-z','--cached','--others','--exclude-standard').decode().split('\0') if p and (ROOT/p).is_file()})
@lru_cache(maxsize=1)
def cc():
    from opencc import OpenCC
    return OpenCC('s2tw.json')
def ui(text):
    for old,new in UI_WORDS.items():text=text.replace(old,new)
    return text

class Links(HTMLParser):
    def __init__(self):
        super().__init__();self.links=[];self.scripts=[];self.active=False;self.buffer=[]
    def handle_starttag(self,tag,attrs):
        values=dict(attrs)
        for key in ('href','src'):
            if key in values:self.links.append(values[key])
        if tag=='script':
            self.active='src' not in values and values.get('type','') not in ('application/ld+json','application/json')
            self.buffer=[]
    def handle_data(self,text):
        if self.active:self.buffer.append(text)
    def handle_endtag(self,tag):
        if tag=='script' and self.active:self.scripts.append(''.join(self.buffer));self.active=False

def check() -> None:
    manifest = json.loads(read('localization/manifest.json'))
    assert len(manifest['chapters']) == 34 and len(manifest['entries']) == 765
    assert len({e['id'] for e in manifest['entries']}) == 765
    original = json.loads(git('show', f'{BASE}:localization/manifest.json'))
    by_id = {e['id']: e for e in original['entries']}
    count = 0
    for chapter in manifest['chapters']:
        old = unquote(chapter['source_path_uri']); new = chapter['display_path']
        before = git('show', f'{UPSTREAM}:{old}').decode()
        after = read(new)
        assert Counter(URL.findall(before)) == Counter(URL.findall(after)), f'來源網址有變：{new}'
        assert re.findall(r'\d+(?:\.\d+)?', before) == re.findall(r'\d+(?:\.\d+)?', after.replace(NOTICE, '')), f'數字有變：{new}'
        a = len(re.findall(r'^###\s+\d+\.', after, re.M)); count += a
        assert a == chapter['entry_count'], new
        assert NOTICE.strip() in after, new
    assert count == 765
    for e in manifest['entries']:
        o = by_id[e['id']]
        assert unquote(e['upstream_path_uri']) == o['upstream_path']
        assert e['upstream_text_sha256'] == o['upstream_text_sha256']
        from review_contract import validate_entry
        validate_entry(e, ROOT)
        assert (ROOT / e['display_path']).is_file()
    for p in ('LICENSE', 'LICENSE-CODE'):
        assert (ROOT / p).read_bytes() == git('show', f'{BASE}:{p}'), p
    errors = []
    js_count = 0; local_count = 0
    for p in current_files():
        if p.startswith('tools/tw/') or p.endswith('package-lock.json'): continue
        if Path(p).suffix not in SUFFIXES: continue
        text = read(p)
        if Path(p).suffix in {'.mjs', '.js'}:
            subprocess.run(['node', '--check', p], cwd=ROOT, check=True); js_count += 1
        if Path(p).suffix == '.html':
            parser = Links(); parser.feed(text)
            for part in parser.scripts:
                subprocess.run(['node', '--check'], input=part, text=True, cwd=ROOT, check=True); js_count += 1
        if p in ('index.html', 'selfcheck.html'):
            assert 'lang="zh-TW"' in text
            assert not re.search(r'googletagmanager\.com|google-analytics\.com|G-NTPGXCLMP6|4\.mcyyy\.com|ads/wechat|id="tip-mask"', text), p
        if Path(p).suffix not in {'.md', '.html'}: continue
        if p.startswith('docs/') and '/'+cc().convert('\u6838\u5b9e\u8bb0\u5f55')+'/' in p: continue
        if p in {'CLAUDE.md'}: continue
        candidates = re.findall(r'!?\[[^\]\n]*\]\(([^\s)]+)\)', text) if p.endswith('.md') else []
        if p.endswith('.html'):
            parser = Links(); parser.feed(text); candidates += parser.links
        for link in candidates:
            link = unescape(link).strip('<>')
            if not link or link.startswith(('#', 'http:', 'https:', 'mailto:', 'data:', 'javascript:')) or '${' in link or '<' in link: continue
            target = unquote(link.split('#')[0].split('?')[0])
            if not target: continue
            resolved = (ROOT / Path(p).parent / target).resolve()
            if not resolved.is_relative_to(ROOT): continue
            local_count += 1
            if not resolved.exists(): errors.append(f'{p} -> {target}')
    if errors: raise RuntimeError('相對連結不存在：\n' + '\n'.join(errors[:30]))
    assert not (ROOT / '.github/FUNDING.yml').exists()
    subprocess.run(['git', 'diff', '--check'], cwd=ROOT, check=True)
    print(f'PASS：34 章／765 條，來源網址與數字、原始雜湊、授權、{js_count} 組腳本語法、{local_count} 個相對連結及廣告檢查。')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check',action='store_true')
    args=parser.parse_args()
    if not args.check:parser.error('此工具只接受--check；初始化遷移已退休')
    check()

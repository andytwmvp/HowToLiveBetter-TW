#!/usr/bin/env python3
"""一次性遷移修整：修正有效連結、產生文件用字與測試中的語境誤判。"""
from __future__ import annotations
import json
import re
from urllib.parse import quote, unquote
from traditionalize import ROOT, BASE, BRANCH, REPO, URL, cc, git, read, write


def refine() -> None:
    if git('branch', '--show-current').decode().strip() != BRANCH:
        raise RuntimeError('僅允許在繁體化工作分支修整')
    origin = git('remote', 'get-url', 'origin').decode().strip().removesuffix('.git').rstrip('/')
    if origin not in {f'https://github.com/{REPO}', f'git@github.com:{REPO}'}:
        raise RuntimeError('非授權 fork，停止')
    assert (ROOT / 'localization/traditionalization-report.json').exists()
    # HTML 解析器內的 Markdown 示意字串不是實際相對網址。
    # HTML 檢查真實 href/src；Markdown 檢查其連結語法；動態連結另做瀏覽器測試。
    path = 'tools/tw/traditionalize.py'
    text = read(path)
    for line in text.splitlines():
        if line.strip().startswith('candidates = re.findall(') and "if p.endswith('.md')" not in line:
            text = text.replace(line, line + " if p.endswith('.md') else []")
    if '@lru_cache(maxsize=1)\ndef cc()' not in text:
        text = text.replace('from collections import Counter', 'from collections import Counter\nfrom functools import lru_cache')
        text = text.replace('\ndef cc():', '\n@lru_cache(maxsize=1)\ndef cc():')
    write(path, text)
    # 新增的圖片提示也走相同轉換器，不只處理原模板。
    path = 'tools/tw/assets_and_browser.py'
    text = read(path).replace("write('tools/og.html', text)", "write('tools/og.html', cc().convert(text))")
    write(path, text)
    generated = ['AGENTS.md', 'CLAUDE.md', 'PROJECT_STATE.md', 'ATTRIBUTION.md', 'localization/zh-TW-style-guide.md', 'locales/zh-TW/README.md']
    for path in generated: write(path, cc().convert(read(path)))

    mapping = json.loads(read('localization/path-map.json'))['files']
    pairs = [(unquote(item['source_path_uri']), item['path']) for item in mapping]
    def own_url(match):
        value = match.group()
        for prefix in [f'https://github.com/{REPO}/blob/main/', f'https://github.com/{REPO}/tree/main/', f'https://raw.githubusercontent.com/{REPO}/main/']:
            if not value.startswith(prefix): continue
            tail = unquote(value[len(prefix):])
            for old, new in sorted(pairs, key=lambda p:len(p[0]), reverse=True):
                if tail.startswith(old) and (len(tail) == len(old) or tail[len(old)] in '#?)'):
                    tail = new + tail[len(old):]
                    break
            return prefix + quote(tail, safe='/#?=&%()')
        return value
    # 僅修正本 fork 的活動連結；外部來源、固定原作連結與授權網址不動。
    for path in ['README.md', 'index.html', 'selfcheck.html']:
        text = URL.sub(own_url, read(path))
        if path == 'index.html':
            pattern = r'<p role="note"[^>]*>.*?</p>'
            notice = '<p role="note" style="padding:12px;border:1px solid currentColor;margin-bottom:16px"><strong>繁體中文工作稿：</strong>全書已轉為繁體字形；台灣法規、醫療與福利制度仍待逐條查核，不可直接視為台灣現行依據。<a href="https://github.com/andytwmvp/HowToLiveBetter-TW/blob/main/locales/zh-TW/README.md">台灣版工作區</a></p>'
            text, count = re.subn(pattern, lambda _: notice, text, count=1, flags=re.S)
            assert count == 1, '找不到閱讀頁適用性提示'
            # 上一批刪除打賞彈窗後，鍵盤快捷鍵仍引用已不存在的 TIP；移除懸空引用。
            text = text.replace('if (!DM.mask.hidden || !TIP.hidden) return;', 'if (!DM.mask.hidden) return;')
            assert not re.search(r'\bTIP\b', text), '仍有已移除打賞視窗的程式引用'
        write(path, text)
    print('已修整：生成文案、封面文字、中文路徑、HTML 假連結與打賞殘留事件引用。')


if __name__ == '__main__':
    refine()

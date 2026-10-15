#!/usr/bin/env python3
"""以既有 HTML 模板重製封面，盤點圖片，並驗證桌機／手機／離線頁面。"""
from __future__ import annotations
import argparse
import contextlib
import hashlib
import json
import os
import re
import socket
import struct
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import unquote
from urllib.request import urlopen
from traditionalize import ROOT, BASE, REPO, IMAGE_SUFFIXES, current_files, read, write, dump, cc, ui


def prepare_template() -> None:
    text = read('tools/og.html')
    if '<!-- tw-cover-layout-v1 -->' not in text:
        text = text.replace('<!doctype html><meta charset="utf-8">', '<!doctype html><html lang="zh-TW"><meta charset="utf-8">')
        override = '''<!-- tw-cover-layout-v1 -->
<style>
body{font-family:"Noto Sans CJK TC","Microsoft JhengHei","PingFang TC",sans-serif}
.in{padding:48px 64px 66px}
.brand{font-size:22px}
h1{margin-top:30px;font-size:57px;line-height:1.24;letter-spacing:0}
p{margin-top:20px;font-size:20px;white-space:normal;line-height:1.7;max-width:1072px}
.chips{gap:10px;margin-bottom:0}
.c{font-size:18px;padding:10px 16px}
.tw-note{position:absolute;bottom:24px;left:64px;right:64px;font-size:17px;color:#565a5f}
</style>
'''
        text = text.replace('</style>', '</style>\n' + override, 1)
        text += '\n<div class="tw-note">繁體中文工作稿｜台灣制度查核中；非官方改編，非正式出版定稿。</div>\n</html>\n'
        write('tools/og.html', cc().convert(text))


def audit_assets(rendered: bool) -> None:
    files = current_files()
    pictures = []
    for path in files:
        if Path(path).suffix.lower() not in IMAGE_SUFFIXES: continue
        raw = (ROOT / path).read_bytes()
        item = {'path': path, 'sha256': hashlib.sha256(raw).hexdigest(), 'status': 'needs_review'}
        if path == 'og.png':
            assert raw[:8] == b'\x89PNG\r\n\x1a\n', '封面不是 PNG'
            width, height = struct.unpack('>II', raw[16:24])
            assert (width, height) == (1200, 630), (width, height)
            item.update({'width': width, 'height': height, 'contains_text': True, 'locale': 'zh-TW', 'source_template': 'tools/og.html', 'status': 'regenerated_from_traditional_template' if rendered else 'existing_traditional_asset'})
        elif path.endswith('.svg'):
            text = raw.decode()
            item.update({'contains_text': bool(re.search(r'<(?:text|tspan)\b', text)), 'status': 'vector_source_checked'})
        else:
            raise RuntimeError(f'發現未分類的點陣圖片：{path}；不能宣稱圖片全部完成')
        pictures.append(item)
    badges = []; inline = []
    for path in files:
        if not path.endswith(('.md', '.html')): continue
        text = read(path)
        for match in re.finditer(r'https://img\.shields\.io/badge/[^\s<>"\)]+', text):
            value = match.group(); decoded = unquote(value)
            assert cc().convert(decoded) == decoded, f'徽章內仍有待轉字內容：{path}: {decoded}'
            badges.append({'path': path, 'url': value, 'status': 'encoded_text_traditionalized'})
        for match in re.finditer(r'<svg\b.*?</svg>', text, re.S):
            contains = bool(re.search(r'<(?:text|tspan)\b', match.group()))
            inline.append({'path': path, 'contains_text': contains, 'status': 'text_checked' if contains else 'no_text_icon'})
    dump('localization/assets-inventory.json', {'scope': 'Git 追蹤與本次新增的圖片、HTML 內嵌 SVG、Shields 動態徽章', 'raster_and_vector_files': pictures, 'dynamic_badges': badges, 'inline_svg': inline, 'note': '沒有任意恢復已刪除廣告。圖片文字的語系與台灣制度查核不同；尚未完成人工內容精校。'})


@contextlib.contextmanager
def server():
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0)); port = sock.getsockname()[1]
    proc = subprocess.Popen([sys.executable, '-m', 'http.server', str(port), '--bind', '127.0.0.1', '--directory', str(ROOT)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    url = f'http://127.0.0.1:{port}/'
    try:
        for _ in range(100):
            try:
                with urlopen(url, timeout=1) as response:
                    if response.status == 200: break
            except OSError: time.sleep(.1)
        else: raise RuntimeError('測試伺服器未啟動')
        yield url
    finally:
        proc.terminate()
        try: proc.wait(timeout=5)
        except subprocess.TimeoutExpired: proc.kill(); proc.wait()


def run(render: bool, browser_test: bool) -> None:
    from playwright.sync_api import sync_playwright
    review = Path(os.environ.get('TW_REVIEW_DIR', '/tmp/howtolivebetter-tw-review'))
    review.mkdir(parents=True, exist_ok=True)
    result = {'scope': '工程／介面驗證，不代表台灣制度查核', 'checks': [], 'errors': []}
    errors = []
    with sync_playwright() as pw, server() as url:
        browser = pw.chromium.launch()
        context = browser.new_context(viewport={'width': 1440, 'height': 1000}, locale='zh-TW')
        context.route('**/*', lambda route: route.continue_() if route.request.url.startswith((url, 'file:', 'data:')) else route.abort())
        page = context.new_page()
        page.on('pageerror', lambda error: errors.append(str(error)))
        if render:
            prepare_template()
            page.set_viewport_size({'width': 1200, 'height': 630})
            page.goto(url + 'tools/og.html', wait_until='networkidle')
            page.evaluate('document.fonts.ready')
            cover_text = page.locator('body').inner_text()
            assert cc().convert(cover_text) == cover_text, '封面文字仍有待轉字內容'
            overflow = page.evaluate('''() => {
              const out=[]; const walker=document.createTreeWalker(document.body,NodeFilter.SHOW_TEXT);
              while(walker.nextNode()) { const n=walker.currentNode; if(!n.textContent.trim() || /^(STYLE|SCRIPT)$/.test(n.parentElement.tagName))continue;
                const r=document.createRange();r.selectNodeContents(n);
                for(const b of r.getClientRects())if(b.left < -1||b.right>1201||b.top< -1||b.bottom>631)out.push(n.textContent.trim());
              } return out;
            }''')
            assert not overflow, f'封面文字超出圖片：{overflow}'
            boxes = [page.locator(s).bounding_box() for s in ('h1', '.in p', '.chips', '.tw-note')]
            assert all(boxes)
            for a, b in zip(boxes, boxes[1:]): assert a['y'] + a['height'] <= b['y'] + 1, '封面內容相互重疊'
            page.screenshot(path=str(ROOT / 'og.png'), animations='disabled')
            page.screenshot(path=str(review / 'og-zh-TW.png'), animations='disabled')
            result['checks'].append('og.png 已由繁體模板重製；1200×630；文字無超出畫布或區塊重疊')
        audit_assets(rendered=render)
        if browser_test:
            page.set_viewport_size({'width': 1440, 'height': 1000})
            page.goto(url, wait_until='domcontentloaded')
            page.wait_for_function("document.querySelectorAll('.card').length === 765", timeout=120000)
            assert page.locator('html').get_attribute('lang') == 'zh-TW'
            assert page.locator('#tot').inner_text() == '765'
            assert page.locator('.sec-block').count() == 34
            assert not page.locator('#tip-mask').count()
            page.screenshot(path=str(review / 'desktop-zh-TW.png'), animations='disabled')
            page.locator('#q').fill('密碼')
            page.wait_for_function("Number(document.getElementById('cnt').textContent)>0 && Number(document.getElementById('cnt').textContent)<765")
            page.locator('#q').fill('')
            page.wait_for_function("Number(document.getElementById('cnt').textContent)===765")
            page.locator('.chips[data-dim="grade"] button[data-v="A"]').click()
            page.wait_for_function("Number(document.getElementById('cnt').textContent)===495")
            page.locator('#reset').click()
            page.locator('#theme').click()
            page.screenshot(path=str(review / 'desktop-dark-zh-TW.png'), animations='disabled')
            # 長文必須從本 fork 的 main 路徑解析後就地開啟。
            doc = page.locator('.doc-links a[href*="/blob/main/docs/"]').first
            assert doc.count() == 1, '找不到長文入口'
            doc.click()
            page.locator('#doc-mask').wait_for(state='visible')
            page.wait_for_function("document.getElementById('dm-doc').textContent.trim().length>100")
            assert '404' not in page.locator('#dm-doc').inner_text()[:100]
            page.locator('#dm-x').click()
            result['checks'].append('桌機：765 條／34 章、繁體搜尋、A 級 495 條篩選、重設、深色模式與長文彈窗')
            page.set_viewport_size({'width': 390, 'height': 844})
            page.goto(url, wait_until='domcontentloaded')
            page.wait_for_function("document.querySelectorAll('.card').length === 765", timeout=120000)
            page.locator('#menu').click()
            assert 'open' in (page.locator('#sidebar').get_attribute('class') or '')
            page.screenshot(path=str(review / 'mobile-zh-TW.png'), animations='disabled')
            result['checks'].append('手機 390×844：正文載入及側欄開啟')
            page.goto(url + 'selfcheck.html', wait_until='domcontentloaded')
            page.wait_for_selector('.q')
            assert page.locator('html').get_attribute('lang') == 'zh-TW'
            page.locator('.seg button.yes').first.click()
            assert page.locator('.seg button.yes').first.get_attribute('aria-pressed') == 'true'
            result['checks'].append('生活自查頁：繁體語系與選項操作')
            page.set_viewport_size({'width': 1440, 'height': 1000})
            page.goto((ROOT / 'dist/tw-source-preview.html').as_uri(), wait_until='domcontentloaded')
            page.wait_for_function("document.querySelectorAll('.card').length === 765", timeout=120000)
            result['checks'].append('離線 HTML：765 條完整內嵌並正常載入')
        context.close(); browser.close()
    result['errors'] = errors
    (review / 'browser-results.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    if errors: raise RuntimeError('瀏覽器 JavaScript 錯誤：' + '\n'.join(errors))
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--render', action='store_true'); parser.add_argument('--browser', action='store_true'); parser.add_argument('--audit', action='store_true')
    args = parser.parse_args()
    if args.render or args.browser: run(args.render, args.browser)
    elif args.audit: audit_assets(rendered=False)
    else: parser.error('請指定 --render、--browser 或 --audit')

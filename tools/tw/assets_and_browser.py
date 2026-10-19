#!/usr/bin/env python3
"""圖片唯讀盤點、既有模板重製，以及臺灣導航與原作來源頁的瀏覽器驗證。"""
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
from traditionalize import ROOT, IMAGE_SUFFIXES, current_files, read, dump, cc


def audit_assets(rendered: bool) -> None:
    files=current_files();pictures=[]
    for path in files:
        if Path(path).suffix.lower() not in IMAGE_SUFFIXES:continue
        raw=(ROOT/path).read_bytes();item={'path':path,'sha256':hashlib.sha256(raw).hexdigest(),'status':'needs_review'}
        if path=='og.png':
            assert raw[:8]==b'\x89PNG\r\n\x1a\n','封面不是PNG'
            width,height=struct.unpack('>II',raw[16:24]);assert (width,height)==(1200,630)
            item.update({'width':width,'height':height,'contains_text':True,'locale':'zh-TW','source_template':'tools/og.html','status':'regenerated_from_traditional_template' if rendered else 'existing_traditional_asset'})
        elif path.endswith('.svg'):
            item.update({'contains_text':bool(re.search(r'<(?:text|tspan)\b',raw.decode())),'status':'vector_source_checked'})
        else:raise RuntimeError('發現未分類圖片，不能宣稱全部完成：'+path)
        pictures.append(item)
    badges=[];inline=[]
    for path in files:
        if not path.endswith(('.md','.html')):continue
        text=read(path)
        for match in re.finditer(r'https://img\.shields\.io/badge/[^\s<>"\)]+',text):
            value=match.group();decoded=unquote(value)
            assert cc().convert(decoded)==decoded,'徽章仍含待轉文字：'+path
            badges.append({'path':path,'url':value,'status':'encoded_text_traditionalized'})
        for match in re.finditer(r'<svg\b.*?</svg>',text,re.S):
            contains=bool(re.search(r'<(?:text|tspan)\b',match.group()))
            inline.append({'path':path,'contains_text':contains,'status':'text_checked' if contains else 'no_text_icon'})
    if not rendered:
        saved=json.loads(read('localization/assets-inventory.json'));old={p['path']:p for p in saved['raster_and_vector_files']}
        if len(old)!=len(pictures):raise RuntimeError('圖片數量與盤點不同')
        for item in pictures:
            prior=old.get(item['path'])
            if prior is None or any(prior.get(k)!=item.get(k) for k in ('sha256','width','height','contains_text')):raise RuntimeError('圖片已變更但盤點未更新：'+item['path'])
        if [(b['path'],b['url']) for b in saved['dynamic_badges']]!=[(b['path'],b['url']) for b in badges]:raise RuntimeError('徽章與盤點不同步')
        if [(v['path'],v['contains_text']) for v in saved['inline_svg']]!=[(v['path'],v['contains_text']) for v in inline]:raise RuntimeError('SVG與盤點不同步')
        print('PASS：圖片稽核一致，沒有覆寫盤點清單。');return
    # 僅明確重製時更新圖片雜湊；保留原先人工審閱狀態。
    saved=json.loads(read('localization/assets-inventory.json'))
    old={p['path']:p for p in saved['raster_and_vector_files']}
    for item in pictures:
        item.update({k:v for k,v in old.get(item['path'],{}).items() if k not in {'sha256','width','height','contains_text'}})
    saved.update({'raster_and_vector_files':pictures,'dynamic_badges':badges,'inline_svg':inline})
    dump('localization/assets-inventory.json',saved)


@contextlib.contextmanager
def server():
    with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
    proc=subprocess.Popen([sys.executable,'-m','http.server',str(port),'--bind','127.0.0.1','--directory',str(ROOT)],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    url=f'http://127.0.0.1:{port}/'
    try:
        for _ in range(100):
            try:
                with urlopen(url,timeout=1) as response:
                    if response.status==200:break
            except OSError:time.sleep(.1)
        else:raise RuntimeError('測試伺服器未啟動')
        yield url
    finally:
        proc.terminate()
        try:proc.wait(timeout=5)
        except subprocess.TimeoutExpired:proc.kill();proc.wait()


def run(render: bool,browser_test: bool) -> None:
    from playwright.sync_api import sync_playwright
    review=Path(os.environ.get('TW_REVIEW_DIR','/tmp/howtolivebetter-tw-review'));review.mkdir(parents=True,exist_ok=True)
    result={'scope':'工程與介面驗證，不代表765條臺灣正文查核完成','checks':[],'errors':[]};errors=[]
    with sync_playwright() as pw,server() as url:
        browser=pw.chromium.launch(**({'executable_path':os.environ['TW_CHROMIUM']} if os.environ.get('TW_CHROMIUM') else {}))
        context=browser.new_context(viewport={'width':1440,'height':1000},locale='zh-TW')
        context.route('**/*',lambda route:route.continue_() if route.request.url.startswith((url,'file:','data:')) else route.abort())
        page=context.new_page();page.on('pageerror',lambda error:errors.append(str(error)))
        if render:
            page.set_viewport_size({'width':1200,'height':630});page.goto(url+'tools/og.html',wait_until='networkidle');page.evaluate('document.fonts.ready')
            cover_text=page.locator('body').inner_text();assert cc().convert(cover_text)==cover_text,'封面文字仍有待轉字內容'
            overflow=page.evaluate('''() => {
              const out=[];const walker=document.createTreeWalker(document.body,NodeFilter.SHOW_TEXT);
              while(walker.nextNode()){const n=walker.currentNode;if(!n.textContent.trim()||/^(STYLE|SCRIPT)$/.test(n.parentElement.tagName))continue;
                const r=document.createRange();r.selectNodeContents(n);
                for(const b of r.getClientRects())if(b.left< -1||b.right>1201||b.top< -1||b.bottom>631)out.push(n.textContent.trim());
              }return out;
            }''');assert not overflow,overflow
            boxes=[page.locator(s).bounding_box() for s in ('h1','.in p','.chips','.tw-note')];assert all(boxes)
            for a,b in zip(boxes,boxes[1:]):assert a['y']+a['height']<=b['y']+1,'封面內容重疊'
            page.screenshot(path=str(ROOT/'og.png'),animations='disabled');page.screenshot(path=str(review/'og-zh-TW.png'),animations='disabled')
            result['checks'].append('封面1200×630已由模板重新產生，文字未超出或重疊；需同步重製紀錄。')
        audit_assets(rendered=render)
        if browser_test:
            from check_navigation import check_navigation
            result['checks'].extend(check_navigation(page,context,url,review))
            from check_prevention_rechecks_browser import check_prevention_rechecks_browser
            result['checks'].extend(check_prevention_rechecks_browser(page,context,url,review))
            from check_crisis_symptoms_browser import check_crisis_symptoms_browser
            from check_hiv_prevention_browser import check_hiv_prevention_browser
            from check_risk_response_browser import check_risk_response_browser
            from check_gambling_prep_bone_browser import check_gambling_prep_bone_browser
            result['checks'].extend(check_crisis_symptoms_browser(page,context,url,review))
            result['checks'].extend(check_hiv_prevention_browser(page,context,url,review))
            result['checks'].extend(check_risk_response_browser(page,context,url,review))
            result['checks'].extend(check_gambling_prep_bone_browser(page,context,url,review))
            from check_ch23_browser import check_ch23_browser
            result['checks'].extend(check_ch23_browser(page,context,url,review))
            from check_ch25_browser import check_ch25_browser
            result['checks'].extend(check_ch25_browser(page,context,url,review))
            from check_ch07_browser import check_ch07_browser
            result['checks'].extend(check_ch07_browser(page,context,url,review))
            from check_ch15_browser import check_ch15_browser
            result['checks'].extend(check_ch15_browser(page,context,url,review))
            from check_ch21_browser import check_ch21_browser
            result['checks'].extend(check_ch21_browser(page,context,url,review))
            from check_ch26_browser import check_ch26_browser
            result['checks'].extend(check_ch26_browser(page,context,url,review))
            from check_ch24_browser import check_ch24_browser
            result['checks'].extend(check_ch24_browser(page,context,url,review))
            page.set_viewport_size({'width':1440,'height':1000});page.goto(url+'source.html',wait_until='domcontentloaded')
            page.wait_for_function("document.querySelectorAll('.card').length === 765",timeout=120000)
            assert page.locator('html').get_attribute('lang')=='zh-TW'
            assert page.locator('#tot').inner_text()=='765';assert page.locator('.sec-block').count()==34
            assert not page.locator('#tip-mask').count()
            page.screenshot(path=str(review/'desktop-zh-TW.png'),animations='disabled')
            page.locator('#q').fill('密碼')
            page.wait_for_function("Number(document.getElementById('cnt').textContent)>0 && Number(document.getElementById('cnt').textContent)<765")
            page.locator('#q').fill('');page.wait_for_function("Number(document.getElementById('cnt').textContent)===765")
            page.locator('.chips[data-dim="grade"] button[data-v="A"]').click();page.wait_for_function("Number(document.getElementById('cnt').textContent)===495")
            page.locator('#reset').click();page.locator('#theme').click()
            page.screenshot(path=str(review/'desktop-dark-zh-TW.png'),animations='disabled')
            doc=page.locator('.doc-links a[href*="/blob/main/docs/"]').first;assert doc.count()==1
            doc.click();page.locator('#doc-mask').wait_for(state='visible')
            page.wait_for_function("document.getElementById('dm-doc').textContent.trim().length>100")
            assert '404' not in page.locator('#dm-doc').inner_text()[:100];page.locator('#dm-x').click()
            result['checks'].append('原作桌機來源稿：765條／34章、搜尋、分級、重設、深色模式及長文彈窗。')
            page.set_viewport_size({'width':390,'height':844});page.goto(url+'source.html',wait_until='domcontentloaded')
            page.wait_for_function("document.querySelectorAll('.card').length === 765",timeout=120000)
            page.locator('#menu').click();assert 'open' in (page.locator('#sidebar').get_attribute('class') or '')
            page.screenshot(path=str(review/'mobile-zh-TW.png'),animations='disabled');result['checks'].append('原作來源稿手機側欄操作。')
            page.goto(url+'selfcheck.html',wait_until='domcontentloaded');page.wait_for_selector('.q')
            assert page.locator('html').get_attribute('lang')=='zh-TW';page.locator('.seg button.yes').first.click()
            assert page.locator('.seg button.yes').first.get_attribute('aria-pressed')=='true'
            page.set_viewport_size({'width':1440,'height':1000});page.goto((ROOT/'dist/tw-source-preview.html').as_uri(),wait_until='domcontentloaded')
            page.wait_for_function("document.querySelectorAll('.card').length === 765",timeout=120000)
            result['checks'].append('明確指定的離線來源預覽：765條完整內嵌。')
        context.close();browser.close()
    result['errors']=errors;(review/'browser-results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    if errors:raise RuntimeError('瀏覽器JavaScript錯誤：'+'\n'.join(errors))
    print(json.dumps(result,ensure_ascii=False))

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--render',action='store_true');parser.add_argument('--browser',action='store_true');parser.add_argument('--audit',action='store_true');args=parser.parse_args()
    if args.render or args.browser:run(args.render,args.browser)
    elif args.audit:audit_assets(False)
    else:parser.error('請指定--render、--browser或--audit')

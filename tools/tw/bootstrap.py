#!/usr/bin/env python3
"""台灣分支一次性初始化；保留原文與授權，移除展示廣告。僅在本 fork 工作分支使用。"""
from __future__ import annotations
import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FORK = 'andytwmvp/HowToLiveBetter-TW'
UPSTREAM = 'eternity4719/HowToLiveBetter'
BASE = '3f59f98be11305902681a8f20ed073c4c4588eee'
BRANCH = 'tw/bootstrap-and-remove-ads'
DATE = '2026-10-15'
MARK = '<!-- tw-bootstrap-v1 -->'

def git(*args: str) -> str:
    return subprocess.check_output(['git', *args], cwd=ROOT, text=True).strip()

def read(path: str) -> str:
    return (ROOT / path).read_text(encoding='utf-8')

def write(path: str, text: str) -> None:
    dest = ROOT / path
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(text, encoding='utf-8', newline='\n')

def sub_once(text: str, pattern: str, replacement: str, label: str) -> str:
    result, count = re.subn(pattern, lambda _m: replacement, text, flags=re.S)
    if count != 1:
        raise RuntimeError(f'{label} 預期一處，實際 {count}；停止，請先審查來源差異')
    return result

def inventory() -> dict:
    chapters, entries = [], []
    for path in sorted((ROOT / 'book').glob('*.md')):
        rel = path.relative_to(ROOT).as_posix()
        raw = path.read_bytes()
        text = raw.decode('utf-8')
        number = int(path.name.split('-', 1)[0])
        headings = list(re.finditer(r'^###\s+(\d+)\.\s+(.+)$', text, re.M))
        title = re.search(r'^#\s+(.+)$', text, re.M)
        chapters.append({'chapter': number, 'source_path': rel,
                         'source_title': title.group(1) if title else path.stem,
                         'entry_count': len(headings),
                         'source_blob_sha': hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()})
        for i, match in enumerate(headings):
            end = headings[i+1].start() if i+1 < len(headings) else len(text)
            entries.append({'id': f'TW-{number:02d}-{int(match.group(1)):03d}',
                            'upstream_chapter': number, 'upstream_item': int(match.group(1)),
                            'upstream_title': match.group(2), 'upstream_path': rel,
                            'upstream_commit': BASE,
                            'upstream_text_sha256': hashlib.sha256(text[match.start():end].encode()).hexdigest(),
                            'treatment': 'unclassified', 'status': 'pending',
                            'target_path': None, 'sources': [], 'verified_at': None})
    if len(chapters) != 34 or len(entries) != 765:
        raise RuntimeError(f'固定基線盤點不符：{len(chapters)} 章 / {len(entries)} 條')
    if len({e['id'] for e in entries}) != len(entries):
        raise RuntimeError('條目 ID 重複')
    return {'schema_version': 1, 'fork': FORK, 'upstream': UPSTREAM, 'upstream_commit': BASE,
            'inventory_date': DATE, 'locale': 'zh-TW', 'jurisdiction': 'TW',
            'chapters': chapters, 'entries': entries}

def apply() -> None:
    origin = git('remote', 'get-url', 'origin').removesuffix('.git').rstrip('/')
    if origin not in {f'https://github.com/{FORK}', f'git@github.com:{FORK}'}:
        raise RuntimeError('origin 不是授權的台灣 fork，拒絕寫入')
    if git('branch', '--show-current') != BRANCH:
        raise RuntimeError('不在指定工作分支，拒絕修改 main 或其他分支')
    data = inventory()
    if MARK in read('README.md'):
        print('已初始化；不覆寫後續編輯。')
        return
    # 固定來源版本，避免把不同版本或使用者後續編輯誤當成原始模板。
    for path in ['README.md', 'index.html', 'tools/offline/build.mjs', 'tools/lib/book.mjs', 'AGENTS.md']:
        old = subprocess.check_output(['git', 'show', f'{BASE}:{path}'], cwd=ROOT)
        if (ROOT / path).read_bytes() != old:
            raise RuntimeError(f'{path} 已有其他修改，停止以免覆寫')
    updates = {}
    md = read('README.md')
    md = sub_once(md, r'\n## Star 走势\n.*\Z', '\n', 'README 宣傳與贊助區塊')
    md = sub_once(md, r'<tr><td align="right"><b>交流</b></td><td align="left">.*?</td></tr>\s*', '', '原作者社群招攬')
    md = sub_once(md, r'<tr><td align="right"><b>下载</b></td><td align="left">.*?</td></tr>',
                  '<tr><td align="right"><b>下載</b></td><td align="left">台灣版尚未正式發行。請先閱讀上方的台灣版工作區；原文與台灣版不得混稱。</td></tr>', '上游電子書下載入口')
    notice = ('> **台灣版尚在逐條改寫與查證。** 下方保留的是中國大陸原文工作底稿，'
              '不是台灣現行醫療、法律、金融或福利指南。台灣版內容與查核狀態另見工作區。\n\n')
    md = md.replace('## 这本书想回答的问题\n', '## 这本书想回答的问题\n\n' + notice, 1)
    md = md.replace(f'https://github.com/{UPSTREAM}/issues', f'https://github.com/{FORK}/issues')
    updates['README.md'] = (MARK + '\n# HowToLiveBetter-TW｜台灣在地化工作區\n\n'
        '非官方繁體中文／台灣在地化改編版。對話負責協作，GitHub 負責保存正文、依據與進度。\n\n'
        '[台灣版閱讀說明](locales/zh-TW/README.md) · [工作進度](PROJECT_STATE.md) · '
        '[逐條對照](localization/manifest.json) · [協作規則](AGENTS.md) · [原作與授權](ATTRIBUTION.md)\n\n'
        '**僅在此 fork 維護；禁止向原作者 repo 建立 PR。移除廣告、打賞與原作者追蹤碼，但保留原作署名與授權。**\n\n'
        + notice + '---\n\n' + md)

    page = read('index.html')
    page = sub_once(page, r'/\* 侧栏底部广告位.*?(?=\.hint p)', '', '廣告與打賞 CSS')
    page = sub_once(page, r'<!-- ga:start.*?<!-- ga:end -->', '', '原作者 Google Analytics')
    page = sub_once(page, r'\n  <div class="group ad">.*?\n  </div>\n(?=</aside>)', '\n', '側欄廣告')
    page = sub_once(page, r'\n<div id="tip-mask" hidden>.*?\n</div>\n(?=\n<div id="xref-pop")', '\n', '打賞視窗')
    page = sub_once(page, r'/\* ---------- 赞赏码弹窗 ---------- \*/.*?(?=\(async function init)', '', '打賞事件處理')
    page = page.replace(f'https://github.com/{UPSTREAM}', f'https://github.com/{FORK}')
    page = page.replace(f'https://raw.githubusercontent.com/{UPSTREAM}/', f'https://raw.githubusercontent.com/{FORK}/')
    page = page.replace('https://eternity4719.github.io/HowToLiveBetter/', 'https://andytwmvp.github.io/HowToLiveBetter-TW/')
    banner = ('<p role="note" style="padding:12px;border:1px solid currentColor;margin-bottom:16px">'
              '<strong>台灣 fork／原文工作底稿：</strong>本頁仍顯示未完成台灣查核的原文；不可直接當作台灣現行制度。'
              ' <a href="https://github.com/andytwmvp/HowToLiveBetter-TW/blob/tw/bootstrap-and-remove-ads/locales/zh-TW/README.md">台灣版工作區</a></p>')
    page = page.replace('<div class="doc-head">', '<div class="doc-head">\n' + banner, 1)
    page = page.replace('<div class="foot">', '<div class="foot">非官方台灣在地化分支；已移除展示廣告與原作者追蹤碼。'
                        f'原作：<a href="https://github.com/{UPSTREAM}">高性价比人生指南 / eternity4719 與貢獻者</a>。<br>', 1)
    updates['index.html'] = page
    offline = read('tools/offline/build.mjs')
    offline = sub_once(offline, r'// 统计脚本不能.*?(?=// 相对链接)',
                      '// 台灣 fork 的網頁不含原作者追蹤碼，離線產物亦不得含追蹤端點。\n'
                      "if (/googletagmanager|google-analytics/.test(html)) throw new Error('禁止在離線版帶入追蹤端點');\n\n", '離線 GA 必要標記依賴')
    offline = sub_once(offline, r'// 侧栏广告图和赞赏码.*?(?=// 页脚)', '', '離線廣告圖片內嵌流程')
    offline = offline.replace('readFileSync, ', '').replace('北京时间', '台北時間')
    updates['tools/offline/build.mjs'] = offline
    lib = read('tools/lib/book.mjs').replace(f'https://github.com/{UPSTREAM}', f'https://github.com/{FORK}')
    lib = lib.replace('https://eternity4719.github.io/HowToLiveBetter/', 'https://andytwmvp.github.io/HowToLiveBetter-TW/')
    updates['tools/lib/book.mjs'] = lib.replace('Asia/Shanghai', 'Asia/Taipei').replace('北京时间', '台北時間')
    updates['AGENTS.md'] = '''# 台灣 fork 協作規則

本檔為此 fork 的工作規則。上游 CLAUDE.md 僅為原作編輯背景；與本檔或使用者要求衝突時，不得套用。

## 寫入與發佈邊界

唯一允許寫入的儲存庫是 `andytwmvp/HowToLiveBetter-TW`。原作 `eternity4719/HowToLiveBetter` 僅可讀取、比對；不得建立 PR、issue、留言或推送。不得以「貢獻上游」為理由越界。

PR 僅可在本 fork 內部建立，base repository 必須逐次核對完整名稱。預設使用工作分支；未經明確授權不得合併 main、啟用自動合併、發布 Release 或啟用 Pages。不得假造已推送、已部署或測試通過。

## 接續工作

每次接續先讀 PROJECT_STATE.md、localization/manifest.json、最新分支與 PR；GitHub 是進度依據，不能只靠聊天記憶。分批交付正文，不得以章節摘要冒充全書翻譯。原文 book/ 與 LICENSE、LICENSE-CODE 保留，台灣正文放 locales/zh-TW/。

每條保留原文對應位置與固定 commit，記錄處理方式、來源、查核日期、適用對象、地區與施行日期。處理方式（翻譯／台灣改寫／新增／不適用）與查核狀態分開。法律、醫療、金融與福利不得機械式換詞，必須查核台灣第一手來源；未確認標記待查證。國際研究效果量不得直接當作台灣效果；證據強度不等於法規適用性。

上游更新只建立差異與影響清單，不自動覆蓋台灣內容，不以編號未變推定內容未變。

## 無廣告與隱私

不得恢復原作者廣告、打賞、商務招攬、追蹤碼或贊助配置；不得自行換成其他人的廣告。保留適當署名、原作連結、CC BY 4.0 與 MIT 授權及修改说明；不得暗示原作者背書。教學中討論廣告或詐騙的正文不屬展示廣告，不得一概刪除。

此 fork 為公開儲存庫。不得提交完整私人對話、健康／財務個資、token、密碼或未獲允許的附件。

## 驗證與清理

每批檢查 diff、條目覆蓋與來源、相對連結、網頁腳本語法、離線構建與廣告殘留；未執行的項目如實註明。bootstrap.py 為一次性初始化工具，不得用來覆寫之後的進度。

若在 /mnt/data 或 /tmp 產生檔案，確認後續不再需要時必須刪除；只保留必要交付物。不得刪除使用者原始附件或其他專案檔案。
'''
    updates['ATTRIBUTION.md'] = f'''# 原作、授權與修改說明

原作：《高性价比人生指南》（HowToLiveBetter），eternity4719 與原儲存庫貢獻者。
原作網址：https://github.com/{UPSTREAM}
本分支基線：{BASE}，盤點日期 {DATE}。

正文依原作 CC BY 4.0 授權改編；完整授權與免責聲明保留於 [LICENSE](LICENSE)。授權網址：https://creativecommons.org/licenses/by/4.0/ 。原作程式碼的 MIT 授權與著作權聲明完整保留於 [LICENSE-CODE](LICENSE-CODE)。

本 fork 是非官方台灣在地化改編，並未取得或宣称取得原作者背書。修改包括移除展示廣告、打賞與原作者追蹤碼，以及新增台灣在地化協作規則和逐條查核流程。後續翻譯／改寫均由版本紀錄追蹤。原作可能有錯或過時；本分支也不保證正確，不取代適用的專業評估。
'''
    updates['locales/zh-TW/README.md'] = '''# 台灣版閱讀說明

本版不是簡轉繁，也不是全書摘要。每一條會保留原文對應、重新處理台灣制度與取得可核對來源；原文 book/ 是工作底稿，不能直接作為台灣法律、健保、勞動或福利建議。

目前階段：建立完整盤點、移除原作者廣告、準備分批翻譯。尚未完成的條目會留在清單，不以不存在的譯文充數。第一批優先處理第 14 章帳號與資訊安全，再處理急難應變、勞動、醫療與生活支持等高風險制度差異。

處理方式：保留翻譯、台灣改寫、台灣新增、不適用且附理由。查核狀態：待處理、草稿、來源已核對、待專業審閱、需重新查核。查核日、資料發布日與制度生效日分開記錄；來源未載日期就註明未載，不能以抓取日充當發布日。

[正式工作進度](../../PROJECT_STATE.md) · [逐條清單](../../localization/manifest.json) · [原作與授權](../../ATTRIBUTION.md)
'''
    updates['PROJECT_STATE.md'] = f'''# HowToLiveBetter-TW 工作狀態

基線：`{BASE}`；盤點日期：{DATE}（Asia/Taipei）。
唯一寫入目標：`{FORK}`；工作分支：`{BRANCH}`。不向原作者儲存庫提出 PR、issue 或留言。

## 本批

完成 34 章、765 條原文逐條索引；正文譯文尚為 0 條，不能把盤點數當作翻譯完成數。原文與兩份授權檔保留。

移除 README 商業廣告／微信打賞／商務合作、側欄廣告與打賞視窗／事件處理／樣式、原作者 Google Analytics、廣告素材與贊助配置；同步移除離線 HTML 構建對廣告圖片與 GA 標記的依賴。原文閱讀頁保留功能，但加入未完成台灣查核的醒目提示。

## 下一批

第 14 章第 1～3 條：多因素驗證、獨立密碼、手機與 SIM 防護；重寫舊有簡訊與登入彈窗排序，查核台灣電信 PIN／PUK 流程。法律／醫療／補助相關條目必須另行查證，不能直接搬用。

## 驗證與交付

原文／授權未變、盤點總數、腳本語法、離線構建、廣告殘留與 Git diff 須由本批 CI 實際執行。CI 成敗以 Actions 與 PR 證據為準，本檔不預先宣告通過。尚未合併 main、未啟用 Pages、未發布台灣版 PDF／EPUB。
'''
    updates['localization/manifest.json'] = json.dumps(data, ensure_ascii=False, indent=2) + '\n'
    for path, text in updates.items():
        write(path, text)
    for path in ['.github/FUNDING.yml', 'ads/mcyyy-side.webp', 'ads/mcyyy.webp', 'ads/wechat-reward.png',
                 'tools/ad-mcyyy-bg.webp', 'tools/ad-mcyyy-side.html', 'tools/ad-mcyyy.html']:
        (ROOT / path).unlink(missing_ok=True)
    print('初始化已套用；請先驗證，再提交到本 fork 的工作分支。')

def check() -> None:
    data = json.loads(read('localization/manifest.json'))
    if len(data['entries']) != 765 or len(data['chapters']) != 34:
        raise RuntimeError('盤點總數不符')
    paths = ['LICENSE', 'LICENSE-CODE'] + [c['source_path'] for c in data['chapters']]
    for path in paths:
        base = subprocess.check_output(['git', 'show', f'{BASE}:{path}'], cwd=ROOT)
        if (ROOT / path).read_bytes() != base:
            raise RuntimeError(f'原文或授權已變動：{path}')
    for path in ['README.md', 'index.html', 'selfcheck.html', 'tools/offline/build.mjs']:
        text = read(path)
        for token in ['4.mcyyy.com', 'ads/wechat-reward.png', 'ads/mcyyy', 'id="tip-mask"', 'G-NTPGXCLMP6']:
            if token in text:
                raise RuntimeError(f'原作者廣告或追蹤殘留：{path}: {token}')
    if (ROOT / '.github/FUNDING.yml').exists():
        raise RuntimeError('原作者贊助配置仍存在')
    for path in (ROOT / 'ads').glob('*'):
        if path.is_file():
            raise RuntimeError(f'未處理廣告素材：{path}')
    for path in ['index.html', 'selfcheck.html']:
        from html.parser import HTMLParser
        class Scripts(HTMLParser):
            def __init__(self):
                super().__init__(); self.active = False; self.buffer = []; self.parts = []
            def handle_starttag(self, tag, attrs):
                if tag == 'script':
                    attrs = dict(attrs)
                    self.active = 'src' not in attrs and attrs.get('type', '') not in ['application/ld+json', 'application/json']
                    self.buffer = []
            def handle_data(self, text):
                if self.active: self.buffer.append(text)
            def handle_endtag(self, tag):
                if tag == 'script' and self.active:
                    self.parts.append(''.join(self.buffer)); self.active = False
        scripts = Scripts(); scripts.feed(read(path))
        for part in scripts.parts:
            subprocess.run(['node', '--check'], input=part, text=True, check=True, cwd=ROOT)
    subprocess.run(['git', 'diff', '--check'], cwd=ROOT, check=True)
    print('PASS: 34 章 / 765 條、原文與授權未改、已知廣告殘留、網頁腳本語法與 diff 檢查。')

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    if not args.apply and not args.check: parser.error('請指定 --apply 或 --check')
    if args.apply: apply()
    if args.check: check()

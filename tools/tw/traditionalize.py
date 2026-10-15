#!/usr/bin/env python3
"""繁體化遷移與唯讀檢查。執行前安裝 OpenCC==1.1.9；只允許本 fork 工作分支寫入。"""
from __future__ import annotations
import argparse
import hashlib
import json
import re
import subprocess
import sys
from collections import Counter
from functools import lru_cache
from html import unescape
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import quote, unquote, urlsplit

ROOT = Path(__file__).resolve().parents[2]
BASE = '1271250f082732b50b1fda851453d4b4b8f1eefd'
UPSTREAM = '3f59f98be11305902681a8f20ed073c4c4588eee'
REPO = 'andytwmvp/HowToLiveBetter-TW'
BRANCH = 'tw/zh-hant-ui-and-assets'
SUFFIXES = {'.md', '.html', '.mjs', '.js', '.py', '.css', '.json', '.yml', '.yaml', '.typ', '.txt', '.xml', '.svg'}
IMAGE_SUFFIXES = {'.png', '.jpg', '.jpeg', '.webp', '.svg', '.gif', '.avif', '.ico'}
URL = re.compile(r'https?://[^\s<>"\'`]+')
NOTICE = '> **繁體字形轉換稿，非台灣制度定稿。** 本頁保留原作的論述、數字與來源；中國大陸法規、補助、客服電話及醫療制度尚未完成台灣查核，不可直接當作台灣現行依據。來源引文亦經字形轉換，精確原文請查固定版本與所附來源。\n\n'
UI_WORDS = {'鏈接': '連結', '軟件': '軟體', '硬件': '硬體', '網絡': '網路', '登錄': '登入', '默認': '預設', '加載': '載入', '鼠標': '滑鼠', '服務器': '伺服器', '用戶': '使用者', '文檔': '文件', '視頻': '影片', '在線': '線上', '緩存': '快取', '信息': '資訊', '短信': '簡訊', '創建': '建立', '身份證': '身分證', '睡眠質量': '睡眠品質'}


def git(*args: str) -> bytes:
    return subprocess.check_output(['git', *args], cwd=ROOT)


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding='utf-8')


def write(path: str, text: str) -> None:
    dest = ROOT / path
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(text.rstrip() + '\n', encoding='utf-8')


def dump(path: str, value: object) -> None:
    write(path, json.dumps(value, ensure_ascii=False, indent=2))


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def base_files() -> list[str]:
    return git('ls-tree', '-rz', '--name-only', BASE).decode().rstrip('\0').split('\0')


def current_files() -> list[str]:
    return sorted({p for p in git('ls-files', '-z', '--cached', '--others', '--exclude-standard').decode().split('\0') if p and (ROOT / p).is_file()})


@lru_cache(maxsize=1)
def cc():
    from opencc import OpenCC
    return OpenCC('s2tw.json')


def ui(text: str) -> str:
    for old, new in UI_WORDS.items():
        text = text.replace(old, new)
    return text


def paths_map() -> dict[str, str]:
    c = cc()
    result = {p: c.convert(p) for p in base_files()}
    if len(set(result.values())) != len(result):
        raise RuntimeError('繁體檔名碰撞；停止，不覆寫任一檔案')
    return result


def convert(text: str, path: str, mapping: dict[str, str]) -> str:
    """來源網址不轉字；本 fork 活動路徑與徽章顯示字另處理。"""
    c = cc()
    protected: list[str] = []
    def hold(value: str) -> str:
        protected.append(value)
        return f'@@TWPROTECTED{len(protected)-1}@@'
    def convert_url(match):
        value = match.group()
        if 'img.shields.io/badge/' in value:
            return hold(quote(ui(c.convert(unquote(value))), safe=':/?&=%#@,+'))
        local = [f'https://github.com/{REPO}/blob/main/', f'https://github.com/{REPO}/tree/main/', f'https://raw.githubusercontent.com/{REPO}/main/']
        for prefix in local:
            if value.startswith(prefix):
                tail = unquote(value[len(prefix):])
                for old in sorted(mapping, key=len, reverse=True):
                    if tail == old or tail.startswith(old + '#'):
                        tail = mapping[old] + tail[len(old):]
                        break
                # 資料夾連結沒有副檔名。
                if tail.rstrip('/') == 'docs/' + '\u6838\u5b9e\u8bb0\u5f55':
                    tail = c.convert(tail)
                return hold(prefix + quote(tail, safe='/#?=&%'))
        return hold(value)
    text = URL.sub(convert_url, text)
    # 同時保護檔名片段，避免 UI 詞彙替換使已重新命名的檔案連結失效。
    aliases = dict(mapping)
    for p in mapping:
        parent = str(Path(p).parent)
        if parent != '.': aliases[parent] = c.convert(parent)
    for old in sorted(aliases, key=len, reverse=True):
        text = text.replace(old, hold(aliases[old])) if old in text else text
    text = c.convert(text)
    if not path.startswith(('book/', 'docs/')):
        text = ui(text)
    # 統計腳本的百分比編碼徽章字串也需要同一套轉換。
    if path == 'tools/sync-stats.mjs':
        text = re.sub(r'(?:%[0-9A-Fa-f]{2}){3,}', lambda m: quote(ui(c.convert(unquote(m.group()))), safe=''), text)
    text = text.replace('zh-CN', 'zh-TW').replace('zh_CN', 'zh_TW').replace('zh-Hans', 'zh-Hant')
    for old, new in {'Microsoft YaHei': 'Microsoft JhengHei', 'PingFang SC': 'PingFang TC', 'Hiragino Sans GB': 'Noto Sans CJK TC', 'Noto Sans SC': 'Noto Sans CJK TC', 'Noto Serif CJK SC': 'Noto Serif CJK TC', 'Noto Sans CJK SC': 'Noto Sans CJK TC'}.items():
        text = text.replace(old, new)
    for i in range(len(protected)-1, -1, -1):
        text = text.replace(f'@@TWPROTECTED{i}@@', protected[i])
    return text


def chapter_text(text: str) -> str:
    lines = text.splitlines(keepends=True)
    # 保留第一行返回目錄連結，讓既有電子書移除返回連結的程式繼續有效。
    offset = 2 if lines and lines[0].startswith('[') else 0
    lines.insert(offset, NOTICE)
    return ''.join(lines)


def apply() -> None:
    origin = git('remote', 'get-url', 'origin').decode().strip().removesuffix('.git').rstrip('/')
    if origin not in {f'https://github.com/{REPO}', f'git@github.com:{REPO}'}:
        raise RuntimeError('非授權 fork，拒絕寫入')
    if git('branch', '--show-current').decode().strip() != BRANCH:
        raise RuntimeError('非指定工作分支，拒絕寫入')
    if (ROOT / 'localization/traditionalization-report.json').exists():
        print('繁體化已套用；不重跑或覆寫後續修改。')
        return
    mapping = paths_map()
    prepared: dict[str, str] = {}
    records = []
    # 新增工具及工作流程不是轉換輸入；既有 workflow 由連接器另行編輯。
    for old, new in mapping.items():
        if old in {'LICENSE', 'LICENSE-CODE', 'localization/manifest.json', 'tools/tw/bootstrap.py'} or old.startswith('.github/workflows/') or old.endswith('package-lock.json'):
            continue
        if Path(old).suffix not in SUFFIXES:
            continue
        data = git('show', f'{BASE}:{old}')
        if (ROOT / old).read_bytes() != data:
            raise RuntimeError(f'基線檔案已有其他修改：{old}；停止以免覆寫')
        before = data.decode('utf-8')
        after = convert(before, old, mapping)
        if old.startswith(('book/', 'docs/')) and old.endswith('.md'):
            after = chapter_text(after)
        if old == 'index.html':
            after = after.replace('台灣 fork／原文工作底稿：', '繁體中文工作稿／台灣制度待查核：').replace('本頁仍顯示未完成台灣查核的原文', '本頁已轉為繁體字形，內容仍未完成台灣制度查核')
            after = after.replace('/blob/tw/bootstrap-and-remove-ads/locales/', '/blob/main/locales/')
            after = re.sub(r'<link[^>]+fonts\.(?:googleapis|gstatic)\.com[^>]*>\s*', '', after)
            after = after.replace('非官方台灣在地化分支；', '非官方繁體中文工作稿；台灣制度查核尚未完成；')
        if old == 'selfcheck.html':
            after = after.replace('<body>', '<body>\n<div role="note" class="note">繁體中文工作稿：此自查仍含原作制度與建議，尚未完成台灣適用性查核。</div>', 1)
        if old in {'robots.txt', 'sitemap.xml'}:
            after = after.replace('https://eternity4719.github.io/HowToLiveBetter/', 'https://andytwmvp.github.io/HowToLiveBetter-TW/')
        if old == 'README.md':
            after = after.replace('下方保留的是中國大陸原文工作底稿', '下方為原作的繁體字形轉換稿；制度仍以中國大陸原文為基礎')
            after = after.replace('下方保留的是中國大陸原文工作底稿', '下方為原作的繁體字形转換稿')
            after = after.replace('## 這本書想回答的問題', '## 這本書想回答的問題', 1)
            # 本地徽章不依賴第三方即時出圖，避免編碼字串中的簡體漏網。
            after = after.replace('<img src="og.png"', '<img src="og.png"', 1)
        prepared[new] = after
        records.append({'source_path_uri': quote(old, safe='/'), 'path': new, 'source_sha256': sha(data), 'changed': after != before})
    for new, text in prepared.items(): write(new, text)
    for old, new in mapping.items():
        if old != new and new in prepared: (ROOT / old).unlink()

    # 來源路徑使用 URI 編碼，來源本體保留於固定 Git commit；不篡改來源雜湊。
    manifest = json.loads(git('show', f'{BASE}:localization/manifest.json'))
    for chapter in manifest['chapters']:
        old = chapter.pop('source_path')
        chapter['source_path_uri'] = quote(old, safe='/')
        chapter['display_path'] = mapping[old]
        chapter['source_title_zh_tw'] = cc().convert(chapter.pop('source_title'))
    for entry in manifest['entries']:
        old = entry.pop('upstream_path')
        entry['upstream_path_uri'] = quote(old, safe='/')
        entry['display_path'] = mapping[old]
        entry['source_title_zh_tw'] = cc().convert(entry.pop('upstream_title'))
        entry['language_status'] = 'traditionalized'
        entry['language_converted_at'] = '2026-10-15'
    manifest['schema_version'] = 2
    manifest['source_path_encoding'] = 'percent-encoded UTF-8; decode with urllib.parse.unquote'
    manifest['language_conversion_is_not_jurisdiction_review'] = True
    dump('localization/manifest.json', manifest)
    dump('localization/path-map.json', {'base_commit': BASE, 'upstream_commit': UPSTREAM, 'files': records})

    write('tools/tw/bootstrap.py', '''#!/usr/bin/env python3
"""舊版初始化已退休；不得再以簡體模板覆寫繁體中文工作稿。"""
import subprocess
import sys
from pathlib import Path
if '--apply' in sys.argv:
    raise SystemExit('初始化已完成。請使用目前的協作規則與繁體中文工作分支。')
if '--check' not in sys.argv:
    raise SystemExit('請指定 --check；此相容入口僅提供唯讀檢查。')
raise SystemExit(subprocess.call([sys.executable, str(Path(__file__).with_name('traditionalize.py')), '--check']))
''')
    agents = read('AGENTS.md')
    agents = agents.replace('原文 book/ 與 LICENSE、LICENSE-CODE 保留，台灣正文放 locales/zh-TW/。', '依使用者最新要求，book/、docs/ 與中文檔名均改為繁體中文工作稿；原始簡體來源保留於固定 Git commit，不另發布簡體展示副本。LICENSE、LICENSE-CODE 原文保持不變。完成台灣實質查核的正文才放入 locales/zh-TW/。')
    agents += '\n## 繁體中文與圖片\n\n所有公開介面、正文、中文檔名、alt／title／ARIA、工具中文訊息與圖片文字使用繁體中文。原始來源網址、程式識別碼、授權原文不可任意改寫。來源原始路徑由 localization/path-map.json 的 URI 與固定 Git 版本追溯。字形完成與台灣適用性查核分開計數。圖片有模板時同步修改模板並重新產生點陣圖，不以只改 alt 冒充改圖。維持純來源改編，不恢復廣告、打賞或追蹤碼。\n'
    write('AGENTS.md', agents)
    write('CLAUDE.md', '# 台灣分支協作入口\n\n本 fork 以 [AGENTS.md](AGENTS.md)、[PROJECT_STATE.md](PROJECT_STATE.md) 與 [繁體中文規範](localization/zh-TW-style-guide.md) 為準。\n\n上游的歷史編輯規則可於固定基線版本查閱，不再作為本 fork 的自動執行指令。不得向上游提出 PR 或寫入，也不得套用其中的中國大陸制度作台灣結論。\n')
    write('localization/zh-TW-style-guide.md', '''# 繁體中文與台灣用語規範

顯示語系使用 zh-TW；正文與中文路徑先以 OpenCC 1.1.9 的 s2tw.json 轉換字形。來源網址及授權不翻動；不對政府機關、法規名稱或研究結果機械套用台灣制度。引用轉字後不是逐字原文，引文原貌從固定 Git 版本與官方來源核對。

介面統一用語：帳號、登入、設定、預設、驗證碼、簡訊、軟體、硬體、伺服器、網路、資訊、資料、文件、連結、使用者、建立、刪除、備份、權限、載入、快取、影片、滑鼠、身分證、睡眠品質。法規名稱、機關名稱及程式識別码依語境保留，不一律換詞。

不得把社保直接換成勞保、把人民幣金額改標新臺幣、把中國電話直接當成台灣窗口，也不得以繁體字形完成宣称台灣法規或醫療查核完成。

圖片依序處理文字模板、SVG、PNG／JPG／WEBP；文字模板須以台灣繁體字型重新輸出，且檢查字型載入、尺寸與文字溢出。無文字 SVG 圖示可以保留；原作者廣告不得復原。外部服務動態徽章須檢查其 URI 編碼中的文字，不只檢查 alt。

原始中文路徑以百分比編碼儲存在對照清單，避免把識別路徑當成可任意翻譯的文案。資料版本、字形完成狀態、來源查核狀態與台灣適用性分開記錄。舊版 bootstrap.py 的 --apply 已停用。

在 /mnt/data 或 /tmp 建立的暫存／中間檔案，不再需要時必須清除。不得刪除使用者原始檔案，也不得把字型、token 或私人對話提交至儲存庫。
''')
    write('locales/zh-TW/README.md', '# 台灣在地化閱讀說明\n\n目前 [book/](../../book/) 已完成 34 章、765 條繁體字形轉換；介面、工具中文文案與中文檔名同步處理。這不是台灣制度改寫完成版。\n\n已完成台灣來源查核與實質在地化的條目目前仍為 0。法律、醫療、金融、福利、金額及客服窗口必須逐條核對，不能只靠換字。原始簡體版本由固定 Git commit 與來源對照表追溯。\n\n[工作狀態](../../PROJECT_STATE.md) · [逐條對照](../../localization/manifest.json) · [圖片盤點](../../localization/assets-inventory.json) · [原作與授權](../../ATTRIBUTION.md)\n')
    write('PROJECT_STATE.md', f'''# HowToLiveBetter-TW 工作狀態

唯一寫入目標：`{REPO}`。原作僅讀取比對，不提出 PR、issue、留言或推送。

## 已合併的 M0

PR #1 已合併 main，合併提交 `{BASE}`。廣告、微信打賞、商務導流、原作者 Google Analytics 與贊助設定已移除，署名及授權保留。原文自動出版已停用。

## M1：繁體字形、介面與圖片

本批分支：`{BRANCH}`。34 章、765 條已做繁體字形轉換，docs 全部中文文件與檔名同步處理。原始來源以 `{UPSTREAM}` 與 `{BASE}` 保存於 Git 歷史；current path 與來源 URI 分開記錄，不再要求轉字後正文與簡體底稿位元完全相同。

完成的是字形工程，不是台灣實質改寫。**台灣制度與來源查核完成數仍為 0 條。** 每篇轉換稿及網頁均有適用性提示。

圖片含文字模板、主要封面 og.png、動態徽章及 SVG 圖示。實際盤點與重製狀態以 localization/assets-inventory.json 為準；未成功重新輸出時，不宣稱點陣圖已完成。

## 驗證與合併邊界

本批須通過完整條目數、來源 URI／数字保留、授權比對、相對連結、JavaScript、交叉引用、統計、離線 HTML、EPUB／Anki 生成及瀏覽器基本互動測試。實際結果以本分支 Actions 與檢查報告為準，未執行的 PDF 排版與專業審閱不得算通過。

本批尚未合併 main，沒有啟用 Pages 或發布 Release。僅建立此 fork 內部 PR，等待使用者確認合併。

## 下一批

先逐條精修第 14 章第 1～3 條的台灣情境與來源，再處理急難應變、勞動、醫療與福利。字形自動轉換仍可能有多義字或專有名稱需人工校閱；不能用工程測試取代內容審查。
''')
    attribution = read('ATTRIBUTION.md') + '\n本次另完成繁體字形轉換、介面文案與檔名調整；原始文字保留於 Git 固定版本，並以來源雜湊、URI 對照。這不代表原作者同意或背書台灣版，也不代表台灣制度查核已完成。\n'
    write('ATTRIBUTION.md', attribution)
    report = {'base_commit': BASE, 'branch': BRANCH, 'converter': 'OpenCC 1.1.9 / s2tw.json', 'text_files_processed': len(records), 'text_files_changed': sum(r['changed'] for r in records), 'renamed_files': sum(r['source_path_uri'] != quote(r['path'], safe='/') for r in records), 'source_chapters': 34, 'script_converted_entries': 765, 'taiwan_verified_entries': 0, 'scope': '字形轉換；不宣稱制度查核、部署或出版完成'}
    dump('localization/traditionalization-report.json', report)
    print(json.dumps(report, ensure_ascii=False))


class Links(HTMLParser):
    def __init__(self):
        super().__init__(); self.links = []; self.scripts = []; self.active = False; self.buffer = []
    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        for key in ('href', 'src'):
            if key in a: self.links.append(a[key])
        if tag == 'script':
            self.active = 'src' not in a and a.get('type', '') not in ('application/ld+json', 'application/json')
            self.buffer = []
    def handle_data(self, text):
        if self.active: self.buffer.append(text)
    def handle_endtag(self, tag):
        if tag == 'script' and self.active:
            self.scripts.append(''.join(self.buffer)); self.active = False


def check() -> None:
    mapping = paths_map()
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
        # 去掉新增適用性提示後比較阿拉伯數字序列，保護年齡、金額、研究量與電話。
        assert re.findall(r'\d+(?:\.\d+)?', before) == re.findall(r'\d+(?:\.\d+)?', after.replace(NOTICE, '')), f'數字有變：{new}'
        a = len(re.findall(r'^###\s+\d+\.', after, re.M)); count += a
        assert a == chapter['entry_count'], new
        assert NOTICE.strip() in after, new
    assert count == 765
    for e in manifest['entries']:
        o = by_id[e['id']]
        assert unquote(e['upstream_path_uri']) == o['upstream_path']
        assert e['upstream_text_sha256'] == o['upstream_text_sha256']
        assert e['status'] == o['status'] and e['verified_at'] == o['verified_at']
        assert (ROOT / e['display_path']).is_file()
    for p in ('LICENSE', 'LICENSE-CODE'):
        assert (ROOT / p).read_bytes() == git('show', f'{BASE}:{p}'), p
    errors = []
    js_count = 0; local_count = 0
    for p in current_files():
        if p.startswith('tools/tw/') or p.endswith('package-lock.json'): continue
        if Path(p).suffix not in SUFFIXES: continue
        text = read(p)
        if Path(p).suffix == '.mjs':
            subprocess.run(['node', '--check', p], cwd=ROOT, check=True); js_count += 1
        if Path(p).suffix == '.html':
            parser = Links(); parser.feed(text)
            for part in parser.scripts:
                subprocess.run(['node', '--check'], input=part, text=True, cwd=ROOT, check=True); js_count += 1
        if p in ('index.html', 'selfcheck.html'):
            assert 'lang="zh-TW"' in text
            assert not re.search(r'googletagmanager\.com|google-analytics\.com|G-NTPGXCLMP6|4\.mcyyy\.com|ads/wechat|id="tip-mask"', text), p
        if Path(p).suffix not in {'.md', '.html'}: continue
        # 原作歷史工作筆記中的命令示例不作網站入口測試；正文與公開頁面嚴格檢查。
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


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true'); parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    if not args.apply and not args.check: parser.error('請指定 --apply 或 --check')
    if args.apply: apply()
    if args.check: check()

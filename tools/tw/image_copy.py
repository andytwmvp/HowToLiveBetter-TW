#!/usr/bin/env python3
"""同步圖片臺灣用語、徽章、替代文字與統計格式；不變更正文制度。"""
from __future__ import annotations
import argparse
import hashlib
import html
import json
import re
import subprocess
from pathlib import Path
from urllib.parse import quote, unquote
from traditionalize import ROOT, REPO, read, write, dump, git

START = '510111a8bd1003fff5e9adef8b95f6ffc489afba'
BRANCH = 'tw/zh-hant-ui-and-assets'
SPEC = 'localization/image-copy.zh-TW.json'
REPORT = 'localization/image-copy-report.json'
EDIT_PATHS = ['tools/og.html', 'README.md', 'index.html', 'tools/sync-stats.mjs', 'PROJECT_STATE.md']


def load_spec():
    return json.loads(read(SPEC))


def statistics():
    chapters = sorted((ROOT / 'book').glob('*.md'))
    counts = {'entries': 0, 'A': 0, 'B': 0, 'C': 0, 'links': 0}
    for chapter in chapters:
        for line in chapter.read_text(encoding='utf-8').splitlines():
            if line.startswith('### '): counts['entries'] += 1
            match = re.match(r'^- 證據等級：([ABC])', line)
            if match: counts[match[1]] += 1
            if re.match(r'^- (來源|備註)：', line): counts['links'] += len(re.findall(r'https?://', line))
    if not chapters or counts['entries'] != sum(counts[g] for g in 'ABC'):
        raise RuntimeError('原作統計不一致，停止，不以猜測數字產圖')
    return counts


def badge_lines(spec, counts):
    result = []
    for badge in spec['badges']:
        message = badge['message'].format(**counts)
        label = badge['label']
        url = 'https://img.shields.io/badge/' + quote(label, safe='') + '-' + quote(message, safe='') + '-' + badge['color'] + '?style=flat-square'
        result.append(f"[![{label}：{message}]({url})]({badge['destination']})")
    return result


def cover(spec, counts):
    esc = html.escape
    row = lambda items: ' · '.join(esc(x) for x in items)
    return '''<!-- tw-cover-layout-v1 -->
<!-- 圖片文案依 localization/image-copy.zh-TW.json；原作統計由 data-stat 標記同步。 -->
<!doctype html>
<html lang="zh-TW">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=1200, initial-scale=1">
<title>''' + esc(spec['title']) + '''｜封面產圖模板</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{width:1200px;height:630px;font-family:"Noto Sans CJK TC","Microsoft JhengHei","PingFang TC",sans-serif;background:#fff;position:relative;overflow:hidden}
.bg{position:absolute;inset:0;background:radial-gradient(700px 420px at 88% 8%,rgba(100,108,255,.16),transparent 70%),radial-gradient(560px 380px at 4% 100%,rgba(16,185,129,.12),transparent 70%)}
.grid{position:absolute;inset:0;opacity:.5;background-image:linear-gradient(#eceded 1px,transparent 1px),linear-gradient(90deg,#eceded 1px,transparent 1px);background-size:48px 48px;mask-image:linear-gradient(180deg,rgba(0,0,0,.55),transparent 78%)}
.bar{position:absolute;left:0;top:0;width:100%;height:8px;background:linear-gradient(90deg,#3451b2,#5672cd 45%,#18794e)}
.in{position:relative;padding:48px 64px 82px;height:100%;display:flex;flex-direction:column}
.brand{display:flex;align-items:center;gap:14px;font-size:24px;color:#565a5f;font-weight:600}
.logo{width:44px;height:44px;border-radius:11px;background:#3451b2;color:#fff;display:flex;align-items:center;justify-content:center}
.logo svg{width:28px;height:28px}
h1{margin-top:32px;font-size:59px;line-height:1.3;letter-spacing:0;color:#1b1b1f;font-weight:700}
h1 em{font-style:normal;color:#3451b2}
p{margin-top:24px;font-size:23px;line-height:1.85;color:#565a5f;max-width:1072px}
.chips{margin-top:auto;display:flex;gap:10px;flex-wrap:wrap}
.c{font-size:18px;font-weight:600;padding:10px 16px;border-radius:999px;background:#f6f6f7;color:#565a5f;border:1px solid #e2e2e3}
.c b{color:#1b1b1f;font-variant-numeric:tabular-nums}
.c.a{background:rgba(16,185,129,.12);border-color:transparent;color:#18794e}
.c.u{background:rgba(100,108,255,.14);border-color:transparent;color:#3451b2}
.tw-note{position:absolute;bottom:24px;left:64px;right:64px;font-size:17px;line-height:1.6;color:#565a5f}
</style>
</head>
<body>
<div class="bg"></div><div class="grid"></div><div class="bar"></div>
<div class="in">
  <div class="brand"><span class="logo" aria-hidden="true"><svg viewBox="0 0 24 24"><path d="M6 12.5l4 4 8-9.5" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"/></svg></span>''' + esc(spec['title']) + '｜' + esc(spec['edition']) + '''</div>
  <h1>''' + esc(spec['headline'][0]) + '<br><em>' + esc(spec['headline'][1]) + '''</em></h1>
  <p>''' + row(spec['topics'][:4]) + '<br>' + row(spec['topics'][4:]) + '''</p>
  <div class="chips">
    <div class="c u">原作整理 <b data-stat="entries">''' + str(counts['entries']) + '''</b> 則建議</div>
    <div class="c a">原作 A 級標記 <b data-stat="grade-a">''' + str(counts['A']) + '''</b> 則</div>
    <div class="c">原作來源 <b data-stat="links">''' + str(counts['links']) + '''</b> 筆連結</div>
    <div class="c">''' + esc(spec['filter_label']) + '''</div>
  </div>
</div>
<div class="tw-note">''' + esc(spec['notice']) + '''</div>
</body>
</html>
'''


def replace_line(text, prefix, replacement):
    lines = text.splitlines()
    hits = [i for i, line in enumerate(lines) if line.startswith(prefix)]
    if len(hits) != 1: raise RuntimeError(f'統計規則應有一處：{prefix}，實際 {len(hits)}')
    lines[hits[0]] = replacement
    return '\n'.join(lines) + '\n'


def apply():
    if git('branch', '--show-current').decode().strip() != BRANCH:
        raise RuntimeError('僅允許指定工作分支，拒絕直接寫 main')
    if git('remote', 'get-url', 'origin').decode().strip().removesuffix('.git') != 'https://github.com/' + REPO:
        raise RuntimeError('寫入目標不是授權 fork')
    if (ROOT / REPORT).exists():
        raise RuntimeError('本批圖片已處理；不可重跑覆寫後續修改')
    for path in EDIT_PATHS:
        if (ROOT / path).read_bytes() != git('show', f'{START}:{path}'):
            raise RuntimeError(f'{path} 已有其他修改，請重新比對，不強行覆寫')
    spec = load_spec(); counts = statistics(); updates = {}
    updates['tools/og.html'] = cover(spec, counts)
    md = read('README.md')
    md, n = re.subn(r'<img src="og\.png" alt="[^"]*"', lambda _: '<img src="og.png" alt="' + html.escape(spec['alt'], quote=True) + '"', md)
    if n != 1: raise RuntimeError('README 封面圖片位置不符')
    badges = re.compile(r'^\[!\[[^\n]+\n?', re.M)
    old_badges = list(badges.finditer(md))
    if len(old_badges) != 6: raise RuntimeError('README 徽章不是六個，停止檢查差異')
    md = md[:old_badges[0].start()] + '\n'.join(badge_lines(spec, counts)) + '\n' + md[old_badges[-1].end():]
    md = md.replace('# 高性價比人生指南\n', '# ' + spec['title'] + '｜' + spec['edition'] + '\n', 1)
    updates['README.md'] = md

    page = read('index.html')
    title = spec['title'] + '｜' + spec['edition'] + '編修中'
    description = f"原作收錄 {counts['entries']} 條建議，主題涵蓋健康保健、急救防災、省錢理財、法律權益、失業協助、感情與育兒、海外生活與職涯學習。圖片用語已依臺灣習慣編修；正文制度仍待逐條查核。"
    page = re.sub(r'<title>.*?</title>', '<title>' + title + '</title>', page, count=1)
    for name, value in [('og:site_name', spec['title']), ('og:title', title), ('twitter:title', title), ('og:description', description), ('twitter:description', description), ('description', description)]:
        pattern = r'(<meta (?:property|name)="' + re.escape(name) + r'" content=")[^"]*(">)'
        page, n = re.subn(pattern, lambda m: m[1] + html.escape(value, quote=True) + m[2], page)
        if n != 1: raise RuntimeError('分享預覽欄位不符：' + name)
    for tag, attr in [('og:image:alt', 'property'), ('twitter:image:alt', 'name')]:
        markup = '<meta ' + attr + '="' + tag + '" content="' + html.escape(spec['alt'], quote=True) + '">'
        if tag not in page: page = page.replace('</head>', markup + '\n</head>', 1)
    updates['index.html'] = page

    stats = read('tools/sync-stats.mjs')
    prefix = quote('原作建議', safe=''); unit = quote('則', safe='')
    stats = replace_line(stats, "  ['README.md', '條目徽章',", "  ['README.md', '條目徽章', /" + prefix + r"-(\d+)%20" + unit + "/g, `" + prefix + "-${entries}%20" + unit + "`],")
    unit = quote('筆連結', safe='')
    stats = replace_line(stats, "  ['README.md', '文獻連結徽章',", "  ['README.md', '文獻連結徽章', /" + r"-(\d+)%20" + unit + "/g, `-${links}%20" + unit + "`],")
    for label, tag, variable in [('og 條目數', 'entries', 'entries'), ('og A 級數', 'grade-a', 'grade.A'), ('og 連結數', 'links', 'links')]:
        newline = "  ['tools/og.html', '" + label + "', /<b data-stat=\"" + tag + r'">(\d+)<\/b>/g, `<b data-stat="' + tag + '">${' + variable + '}</b>`],'
        stats = replace_line(stats, "  ['tools/og.html', '" + label + "',", newline)
    updates['tools/sync-stats.mjs'] = stats
    state = read('PROJECT_STATE.md')
    state += '\n## M1.1：圖片文案的臺灣用語編修\n\n本批封面改用「高效益人生指南」、「健康保健」、「法律權益」、「失業協助」、「感情・婚姻・育兒」與「依成本效益篩選」，不沿用僅換字形的用語。主標語改為「用更少的花費、時間與心力，把生活過得更好、更安心」，避免宣稱保證延壽或財務收益。\n\n原作建議數、A 級標記與來源數加註原作範圍，不當作臺灣已查核數。六個圖片徽章使用臺灣閱讀習慣，原作者工具宣傳徽章改為「編修進度／臺灣內容待查核」；原作署名與授權仍保留。同步更新封面替代文字與社群分享預覽。\n\n文案規格：localization/image-copy.zh-TW.json。實際封面與模板雜湊：localization/image-copy-report.json。圖片再產生、排版邊界與工程測試以本 PR Actions 為準。這是圖片文案在地化，不變更 765 條正文的臺灣查核狀態。PR #2 尚未合併，沒有部署或發行。\n'
    updates['PROJECT_STATE.md'] = state
    for path, text in updates.items(): write(path, text)
    print('已同步臺灣圖片文案、六個徽章、替代文字及統計標記；下一步實際重新產生 og.png。')


def check():
    spec = load_spec(); counts = statistics()
    template = read('tools/og.html')
    # 逐項檢查實際模板，而非只檢查規格檔或 alt。
    for value in [spec['title'], spec['edition'], *spec['headline'], *spec['topics'], spec['filter_label'], spec['notice']]:
        if html.escape(value) not in template: raise RuntimeError('模板文案未同步：' + value)
    for token in ('性價比', '長壽防病', '法律紅線', '失業兜底', '戀愛婚育', '換回壽命'):
        if token in template: raise RuntimeError('舊圖片用語殘留：' + token)
    expected = {'entries': counts['entries'], 'grade-a': counts['A'], 'links': counts['links']}
    for key, value in expected.items():
        if f'<b data-stat="{key}">{value}</b>' not in template: raise RuntimeError('封面統計過時：' + key)
    md = read('README.md')
    for line in badge_lines(spec, counts):
        if line not in md: raise RuntimeError('徽章文案或來源範圍不同步')
    if html.escape(spec['alt'], quote=True) not in md: raise RuntimeError('README alt 未同步')
    page = read('index.html')
    if 'og:image:alt' not in page or 'twitter:image:alt' not in page: raise RuntimeError('分享圖片缺替代文字')
    for key in ('og:title', 'og:description', 'twitter:title', 'twitter:description'):
        value = re.search(r'<meta (?:property|name)="' + key + r'" content="([^"]+)"', page)[1]
        for token in ('性價比', '失業兜底', '戀愛婚育', '法律紅線'):
            if token in value: raise RuntimeError('分享圖片文案殘留：' + key)
    changed = git('diff', '--name-only', START, '--', 'book', 'docs', 'LICENSE', 'LICENSE-CODE', 'localization/manifest.json').decode().strip()
    if changed: raise RuntimeError('圖片工作不應改動正文、授權或查核狀態：' + changed)
    raw = (ROOT / 'og.png').read_bytes()
    if raw == git('show', f'{START}:og.png'): raise RuntimeError('僅修改文字模板，實際圖片尚未重新產生')
    report = json.loads(read(REPORT))
    digest = lambda data: hashlib.sha256(data).hexdigest()
    if report['image_sha256'] != digest(raw) or report['template_sha256'] != digest(template.encode()): raise RuntimeError('模板與實際圖片版本對不上')
    if report['spec_sha256'] != digest((ROOT / SPEC).read_bytes()): raise RuntimeError('圖片文案規格已更新但未重新產圖')
    subprocess.run(['node', 'tools/sync-stats.mjs', '--check'], cwd=ROOT, check=True, stdout=subprocess.DEVNULL)
    print('PASS：臺灣圖片文案、六個徽章、替代文字、原作統計與實際 PNG 一致；正文、授權及查核狀態未變更。')


def record():
    # 必須在 assets_and_browser.py --render 成功後呼叫；檢查本次渲染實際報告。
    import os
    review = Path(os.environ['TW_REVIEW_DIR'])
    evidence = json.loads((review / 'browser-results.json').read_text(encoding='utf-8'))
    if evidence['errors'] or not any('1200×630' in line for line in evidence['checks']):
        raise RuntimeError('缺少本次成功產圖與排版檢查證據')
    digest = lambda path: hashlib.sha256((ROOT / path).read_bytes()).hexdigest()
    dump(REPORT, {'base_commit': START, 'scope': '圖片文案臺灣在地化；非正文制度查核', 'image': 'og.png', 'image_sha256': digest('og.png'), 'template': 'tools/og.html', 'template_sha256': digest('tools/og.html'), 'spec_sha256': digest(SPEC), 'dimensions': [1200, 630], 'dynamic_badges': 6, 'source_statistics': statistics(), 'taiwan_verified_entries_changed': False, 'render_checks': evidence['checks']})


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true'); parser.add_argument('--record', action='store_true'); parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    if not any(vars(args).values()): parser.error('請指定 --apply、--record 或 --check')
    if args.apply: apply()
    if args.record: record()
    if args.check: check()

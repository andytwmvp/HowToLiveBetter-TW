#!/usr/bin/env python3
"""臺灣字形驗證政策與一次性修復。不得以字形轉換冒充內容查核。"""
from __future__ import annotations
import argparse
import json
import re
import subprocess
from collections import Counter
from pathlib import Path
import traditionalize as base
import text_integrity as text

# 臺灣常見寫法及法規用字；接受異體，不把所有 OpenCC 差異當成簡體字。
EQUIVALENTS = [('臺','台'),('僱','雇'),('佔','占'),('裡','裏'),('公佈','公布'),('宣佈','宣布'),('發佈','發布'),('獲準','獲准'),('核準','核准'),('隻','只'),('衹','只')]


def canonical(value):
    for old, new in EQUIVALENTS:
        value = value.replace(old, new)
    return value


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('JSON 重複鍵：' + key)
        result[key] = value
    return result


def load_json(path):
    try:
        return json.loads(base.read(path), object_pairs_hook=unique_object)
    except ValueError as exc:
        raise ValueError(f'{path}: {exc}') from exc


def audit_drafts():
    files = base.current_files()
    json_files = [p for p in files if p.endswith('.json')]
    for path in json_files:
        load_json(path)
    manifest = load_json('localization/manifest.json')
    expected = Counter(e['upstream_chapter'] for e in manifest['entries'])
    registry = {}
    for path in sorted(p for p in files if p.startswith('localization/tw-edition/sources/') and p.endswith('.json')):
        for row in load_json(path)['sources']:
            if len(row) != 4 or not all(isinstance(v, str) and v.strip() for v in row):
                raise ValueError(f'{path}: 來源必須有四個非空文字欄位')
            key, title, url, scope = row
            if not re.fullmatch('[a-z][a-z0-9_]*', key) or not url.startswith('https://'):
                raise ValueError(f'{path}: 來源 ID 或網址格式錯誤')
            if key in registry and registry[key] != row:
                raise ValueError(f'{path}: 來源 ID 衝突：{key}')
            registry[key] = row
    chapters = []
    covered = set()
    unresolved = Counter()
    for path in sorted(p for p in files if p.startswith('localization/tw-edition/chapters/') and p.endswith('.json')):
        data = load_json(path)
        n = data['chapter']
        if type(n) is not int or n not in expected or Path(path).stem != f'{n:02}':
            raise ValueError(f'{path}: 章號不合法')
        if not all(isinstance(data.get(k), str) and data[k].strip() for k in ('title','intro')):
            raise ValueError(f'{path}: 缺少章名或導言')
        ids = []
        for row in data['entries']:
            if not isinstance(row, list) or len(row) != 8 or type(row[0]) is not int or not all(isinstance(v,str) and v.strip() for v in row[1:]):
                raise ValueError(f'{path}: 條目格式錯誤')
            item = f'TW-{n:02}-{row[0]:03}'
            if item in covered:
                raise ValueError(f'{path}: 重複條目 {item}')
            covered.add(item)
            ids.append(row[0])
            for key in row[5].split():
                if not re.fullmatch('[a-z][a-z0-9_]*', key):
                    raise ValueError(f'{path}: 不合法來源 ID {key}')
                if key not in registry:
                    unresolved[key] += 1
        if sorted(ids) != list(range(1,expected[n]+1)):
            raise ValueError(f'{path}: 條目遺漏或超出原作數量')
        chapters.append({'chapter':n,'path':path,'title':data['title'],'entries':len(ids),'state':'draft'})
    legacy = set()
    for path in files:
        if path.startswith('locales/zh-TW/book/') and path.endswith('.md'):
            legacy.update(re.findall(r'<!--\s*TW-ID:\s*(TW-\d{2}-\d{3})\s*-->',base.read(path)))
    all_ids = {e['id'] for e in manifest['entries']}
    if not (covered | legacy).issubset(all_ids):
        raise ValueError('草稿含不存在的原作 ID')
    # 工程盤點只揭露缺漏。完整實質審閱與正式閱讀整合仍需另行驗收。
    report = {'schema_version':1,'scope':'草稿結構盤點，不是台灣制度或來源正確性驗收','json_files_checked':len(json_files),'original_entries':len(all_ids),'structured_draft_chapters':len(chapters),'structured_draft_entries':len(covered),'legacy_markdown_draft_entries':len(legacy),'unique_draft_entries':len(covered|legacy),'entries_without_any_draft':len(all_ids-covered-legacy),'registry_sources':len(registry),'unresolved_source_ids':dict(sorted(unresolved.items())),'unresolved_reference_occurrences':sum(unresolved.values()),'chapters':chapters,'publication_ready':False,'publication_blockers':['尚有原作主題未完成台灣實質改寫','部分草稿來源 ID 尚未登錄完整來源','尚未完成逐條來源審閱及正式閱讀整合']}
    print(f"PASS：{len(json_files)} 份 JSON；{len(chapters)} 章／{len(covered)} 條結構化草稿。")
    print(f"未完成：{len(unresolved)} 個來源 ID、{sum(unresolved.values())} 處引用；{report['entries_without_any_draft']} 個主題尚無草稿。工程通過不代表出版就緒。")
    return report


def check():
    paths = text.protected_paths()
    problems = []
    for path in text.targets():
        before = base.read(path)
        after = text.normalized(before, paths)
        if canonical(before) != canonical(after):
            for number,(a,b) in enumerate(zip(before.splitlines(),after.splitlines()),1):
                if canonical(a) != canonical(b):
                    problems.append(f'{path}:{number}')
                    break
    if problems:
        raise RuntimeError('仍有簡體字或待校閱用字：\n'+'\n'.join(problems))
    # 沿用既有徽章、網址及 DOI 驗證，但不重複執行錯誤的全檔轉換比較。
    md = base.read('README.md')
    badges = text.BADGE.findall(md)
    if len(badges) != 6 or '%29%5D%28' in md:
        raise ValueError('Markdown 徽章數量或語法錯誤')
    for label,url,dest in badges:
        from urllib.parse import unquote
        if re.search(r'[\[\]()]',unquote(url)):
            raise ValueError('徽章網址混入 Markdown 語法')
        if canonical(base.cc().convert(label)) != canonical(label):
            raise ValueError('徽章仍含待轉換文字')
        if not dest.startswith(('https:','http:','#')) and not (base.ROOT/unquote(dest)).exists():
            raise ValueError('徽章目標不存在：'+dest)
    print(f'PASS：{len(text.targets())} 份文案與 6 個圖片徽章；有效台灣用字保留。')


def repair():
    branch = base.git('branch','--show-current').decode().strip()
    origin = base.git('remote','get-url','origin').decode().strip().removesuffix('.git')
    if branch != 'fix/ci-localization-recovery' or origin != 'https://github.com/'+base.REPO:
        raise RuntimeError('修復僅限授權 fork 的隔離工作分支')
    p = base.ROOT/'localization/tw-edition/chapters/11.json'
    original = p.read_text(encoding='utf-8')
    bad = '罪名與刑期。\n"'
    if bad in original:
        if original.count(bad) != 1:
            raise RuntimeError('JSON 缺陷與已檢查的基線不符')
        corrected = original.replace(bad,'罪名與刑期。"')
        json.loads(corrected)
        p.write_text(corrected,encoding='utf-8')
    paths = text.protected_paths()
    changed = []
    for path in text.targets():
        before = base.read(path)
        after = text.normalized(before,paths)
        if canonical(before) == canonical(after):
            continue
        for original,preferred in [('雇','僱'),('占','佔'),('公布','公佈'),('宣布','宣佈'),('發布','發佈'),('核准','核準'),('獲准','獲準')]:
            if original in before and preferred not in before:
                after = after.replace(preferred,original)
        if '台' in before and '臺' not in before:
            after = after.replace('臺','台')
        if Counter(text.URL.findall(before)) != Counter(text.URL.findall(after)) or re.findall(r'\d+',before) != re.findall(r'\d+',after):
            raise RuntimeError('來源網址或數字不得變動：'+path)
        base.write(path,after)
        changed.append(path)
    print(f'已修正 {len(changed)} 份文案，來源網址、數字及查核狀態不變。')
    # 舊圖片稽核會覆寫預期值，日常驗證改為比較而非重建。
    p = base.ROOT/'tools/tw/assets_and_browser.py'
    code = p.read_text(encoding='utf-8')
    needle = "    dump('localization/assets-inventory.json',"
    if 'CI_READONLY_INVENTORY' not in code:
        line = next(line for line in code.splitlines() if line.startswith(needle))
        replacement = '''    # CI_READONLY_INVENTORY：保留審閱狀態，不以實際檔案反向覆寫預期值。
    if not rendered:
        saved = json.loads(read('localization/assets-inventory.json'))
        old = {p['path']:p for p in saved['raster_and_vector_files']}
        if len(old) != len(pictures): raise RuntimeError('圖片數量與盤點不同')
        for item in pictures:
            prior = old.get(item['path'])
            if prior is None or any(prior.get(k)!=item.get(k) for k in ('sha256','width','height','contains_text')):
                raise RuntimeError('圖片已變更但盤點未更新：'+item['path'])
        if [(b['path'],b['url']) for b in saved['dynamic_badges']] != [(b['path'],b['url']) for b in badges]:
            raise RuntimeError('徽章與盤點不同步')
        if [(v['path'],v['contains_text']) for v in saved['inline_svg']] != [(v['path'],v['contains_text']) for v in inline]:
            raise RuntimeError('SVG 與盤點不同步')
        print('PASS：圖片稽核一致，沒有覆寫盤點清單。')
        return
'''+line
        code = code.replace(line,replacement)
        p.write_text(code,encoding='utf-8')
    report = audit_drafts()
    base.dump('localization/tw-edition/coverage.json',report)
    base.dump('localization/tw-edition/coverage.json',audit_drafts())
    check()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repair',action='store_true')
    parser.add_argument('--check',action='store_true')
    parser.add_argument('--audit',action='store_true')
    parser.add_argument('--report')
    args = parser.parse_args()
    if args.repair: repair()
    if args.check: check()
    if args.audit:
        report = audit_drafts()
        if args.report:
            dest=Path(args.report);dest.parent.mkdir(parents=True,exist_ok=True)
            dest.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    if not (args.repair or args.check or args.audit): parser.error('請指定操作')

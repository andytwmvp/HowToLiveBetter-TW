#!/usr/bin/env python3
"""臺灣字形與草稿結構檢查；全書完成門檻由 review_contract 計算。"""
from __future__ import annotations
import argparse
import json
import re
from collections import Counter
from pathlib import Path
from urllib.parse import unquote
import traditionalize as base
import text_integrity as text
from review_contract import publication_report, validate_runtime
# OpenCC可能把金融用語「扣款」轉為「釦款」；只校正這個詞，不豁免整份正文或其他簡體字。
EQUIVALENTS = [('臺','台'),('僱','雇'),('佔','占'),('裡','裏'),('公佈','公布'),('宣佈','宣布'),('發佈','發布'),('獲準','獲准'),('核準','核准'),('隻','只'),('衹','只'),('釦款','扣款')]
# OpenCC 的通用 s2tw 字典會將臺灣法定服務名稱「托嬰中心／托嬰人員」
# 誤轉成「託嬰」，也會將語意為不介入的「干預」誤轉成「幹預」。
# 「局限空間」為職安法規及職安署正式用語；只對完整詞組校正。
# 引用對照表會將原句裁成「…干的人下手」；截斷「不相干」後，OpenCC 將「干」誤判為「乾」。
# 僅校正這個有明確語意的引用片段，不豁免單獨的「托」、「干」、「局」或其餘簡體字。
OFFICIAL_TAIWAN_CONTEXT_TERMS = [
    ('託嬰', '托嬰'), ('幹預', '干預'), ('侷限空間', '局限空間'), ('乾的人下手', '干的人下手'),
    # OpenCC把臺灣政府資料頁正式使用的「儀表板」誤轉為「儀錶板」。
    ('儀錶板', '儀表板'),
    # OpenCC把臺灣慣用地名譯寫「南佛羅里達」中的「里」誤轉成「裏」。
    ('南佛羅裏達', '南佛羅里達'),
    # OpenCC會把癌症分類片語中的解剖部位「下咽」誤轉成「下嚥」。
    # 僅校正癌登實際使用的完整分類詞，不將一般用語「難以下嚥」等同「難以下咽」。
    ('口腔、口咽及下嚥', '口腔、口咽及下咽'),
    ('口咽與下嚥', '口咽與下咽'), ('口咽及下嚥', '口咽及下咽'),
]
# 「叫、叫、伸、拋、划」是消防署及教育部正式救溺口訣。
# OpenCC s2tw 把獨立的「划」改為「劃」會破壞官方原文；僅對該口訣和語境做精確對等，
# 不把所有「划／劃」視為同字，也不放寬簡體或其他字形的全檔檢查。
OFFICIAL_WATER_RESCUE_TERMS = [
    ('叫叫伸拋劃', '叫叫伸拋划'),
    ('叫、叫、伸、拋、劃', '叫、叫、伸、拋、划'),
    ('『劃』', '『划』'),
    ('「劃」', '「划」'),
    ('，劃是', '，划是'),
]

def canonical(value):
    for old, new in EQUIVALENTS + OFFICIAL_WATER_RESCUE_TERMS + OFFICIAL_TAIWAN_CONTEXT_TERMS:
        value = value.replace(old, new)
    return value

def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result: raise ValueError('JSON 重複鍵：' + key)
        result[key] = value
    return result

def load_json(path):
    try: return json.loads(base.read(path), object_pairs_hook=unique_object)
    except ValueError as exc: raise ValueError(f'{path}: {exc}') from exc

def audit_drafts():
    files = base.current_files()
    json_files = [p for p in files if p.endswith('.json')]
    for path in json_files: load_json(path)
    manifest = load_json('localization/manifest.json')
    expected = Counter(e['upstream_chapter'] for e in manifest['entries'])
    registry = {}
    for path in sorted(p for p in files if p.startswith('localization/tw-edition/sources/') and p.endswith('.json')):
        for row in load_json(path)['sources']:
            if len(row) != 4 or not all(isinstance(v,str) and v.strip() for v in row): raise ValueError(f'{path}:來源欄位缺漏')
            key,title,url,scope = row
            if not re.fullmatch('[a-z][a-z0-9_]*',key) or not url.startswith('https://'): raise ValueError(f'{path}:來源ID或網址錯誤')
            if key in registry and registry[key] != row: raise ValueError(f'{path}:來源ID衝突')
            registry[key] = row
    chapters, covered, unresolved = [], set(), Counter()
    for path in sorted(p for p in files if p.startswith('localization/tw-edition/chapters/') and p.endswith('.json')):
        data = load_json(path); n = data['chapter']
        if type(n) is not int or n not in expected or Path(path).stem != f'{n:02}': raise ValueError(f'{path}:章號不合法')
        if not all(isinstance(data.get(k),str) and data[k].strip() for k in ('title','intro')): raise ValueError(f'{path}:章名或導言缺漏')
        ids = []
        for row in data['entries']:
            if not isinstance(row,list) or len(row)!=8 or type(row[0]) is not int or not all(isinstance(v,str) and v.strip() for v in row[1:]): raise ValueError(f'{path}:條目格式錯誤')
            key = f'TW-{n:02}-{row[0]:03}'
            if key in covered: raise ValueError(f'{path}:重複條目')
            covered.add(key); ids.append(row[0])
            for source in row[5].split():
                if not re.fullmatch('[a-z][a-z0-9_]*',source): raise ValueError(f'{path}:來源ID錯誤')
                if source not in registry: unresolved[source] += 1
        if sorted(ids)!=list(range(1,expected[n]+1)): raise ValueError(f'{path}:條目遺漏或超出數量')
        chapters.append({'chapter':n,'path':path,'title':data['title'],'entries':len(ids),'state':'draft'})
    legacy = set()
    for path in files:
        if path.startswith('locales/zh-TW/book/') and path.endswith('.md'):
            legacy.update(re.findall(r'<!--\s*TW-ID:\s*(TW-\d{2}-\d{3})\s*-->',base.read(path)))
    all_ids = {e['id'] for e in manifest['entries']}
    if not (covered|legacy).issubset(all_ids): raise ValueError('草稿含不存在的原作ID')
    report = {'schema_version':2,'scope':'草稿結構盤點，不代表內容查核完成','json_files_checked':len(json_files),'original_entries':len(all_ids),'structured_draft_chapters':len(chapters),'structured_draft_entries':len(covered),'legacy_markdown_draft_entries':len(legacy),'unique_draft_entries':len(covered|legacy),'entries_without_any_draft':len(all_ids-covered-legacy),'registry_sources':len(registry),'unresolved_source_ids':dict(sorted(unresolved.items())),'unresolved_reference_occurrences':sum(unresolved.values()),'chapters':chapters}
    report.update(publication_report(base.ROOT,manifest))
    # 已有內容與完成審閱的核心正文分開計數，不把導航或重複稿件充作新主題。
    reviewed={e['id'] for e in manifest['entries'] if e['status']=='verified'}
    report.update(topics_with_any_content=len(covered|legacy),
                  topics_with_unreviewed_content=len((covered|legacy)-reviewed),
                  topics_without_content=len(all_ids-covered-legacy),
                  core_reviewed_entries=report['publication_completed_entries'])
    print(f"PASS：{len(json_files)}份JSON；{len(chapters)}章／{len(covered)}條結構化草稿。未完成來源ID：{len(unresolved)}；全書驗收：{report['publication_ready']}。")
    return report

def check():
    paths = text.protected_paths(); problems = []; details = []
    for path in text.targets():
        before = base.read(path); after = text.normalized(before,paths)
        original, converted = canonical(before), canonical(after)
        if original != converted:
            problems.append(path)
            # 不降低驗證嚴格度；在日誌列出字形差異供逐條修訂，避免盲改或擴大白名單。
            if len(original) < 12000 and len(converted) < 12000:
                import difflib
                differences = [
                    (original[i:j], converted[k:l])
                    for kind,i,j,k,l in difflib.SequenceMatcher(
                        None, original, converted, autojunk=False).get_opcodes()
                    if kind != 'equal'
                ]
                details.append(path + ': ' + repr(differences[:12]))
            else:
                index = next((i for i,(a,b) in enumerate(zip(original,converted)) if a != b),
                             min(len(original), len(converted)))
                details.append(path + ': 位置' + str(index) + '：'
                               + repr(original[max(index-18, 0):index+30]) + ' → '
                               + repr(converted[max(index-18, 0):index+30]))
    if problems: raise RuntimeError('仍有簡體字或待校閱用字：'+', '.join(problems)
                                    + '；差異：' + '; '.join(details))
    md = base.read('README.md'); badges = text.BADGE.findall(md)
    if len(badges)!=3 or '%29%5D%28' in md: raise ValueError('Markdown徽章數量或語法錯誤')
    for label,url,dest in badges:
        if re.search(r'[\[\]()]',unquote(url)): raise ValueError('徽章網址混入Markdown語法')
        if canonical(base.cc().convert(label))!=canonical(label): raise ValueError('徽章含待轉文字')
        if not dest.startswith(('https:','http:','#')) and not (base.ROOT/unquote(dest)).exists(): raise ValueError('徽章目標不存在')
    validate_runtime(base.ROOT)
    from link_policy import audit as check_repo_links
    check_repo_links(base.ROOT)
    print(f'PASS：{len(text.targets())}份文案、3個圖片徽章及臺灣導航資料。')

if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check',action='store_true'); parser.add_argument('--audit',action='store_true'); parser.add_argument('--report')
    args=parser.parse_args()
    if args.check: check()
    if args.audit:
        report=audit_drafts()
        if args.report:
            dest=Path(args.report);dest.parent.mkdir(parents=True,exist_ok=True)
            dest.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    if not (args.check or args.audit): parser.error('請指定--check或--audit；一次性修復入口已退休')

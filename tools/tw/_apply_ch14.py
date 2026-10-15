#!/usr/bin/env python3
"""本次已核對的12條正文有限套用；承接PR #6，保留並行來源與草稿成果。"""
from pathlib import Path
import hashlib
import json
import subprocess

ROOT=Path(__file__).resolve().parents[2]
BASE='9331d56201d30e4d19dce97f8e5d19fdc3b95286'
REPO='andytwmvp/HowToLiveBetter-TW'
BRANCH='tw/ch14-reviewed-runtime-20261016'
SKIP={'PROJECT_STATE.md','locales/zh-TW/README.md','locales/zh-TW/book/14-帳號與資訊安全.md','tools/tw/ci_language_policy.py'}

def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT)
def digest(raw):return hashlib.sha256(raw).hexdigest()
def encoded(obj):return (json.dumps(obj,ensure_ascii=False,indent=2)+'\n').encode()

def main():
    if git('branch','--show-current').decode().strip()!=BRANCH or git('remote','get-url','origin').decode().strip().removesuffix('.git')!='https://github.com/'+REPO:
        raise RuntimeError('非授權fork與分支，停止')
    subprocess.run(['git','merge-base','--is-ancestor',BASE,'HEAD'],cwd=ROOT,check=True)
    seed_path='localization/tw-edition/ch14-reviewed.json'
    batch=json.loads((ROOT/seed_path).read_text())
    if digest(encoded(batch))!='805a21ab7e68d33e8e31a47fb9726e66b0967b85b6ddfe7ae30a7781e7649c69':raise RuntimeError('來源編修稿與已核對版本不同')
    plans=[]
    for n in range(4):plans+=json.loads((ROOT/f'tools/tw/_ch14_changes{n}.json').read_text())
    if len(plans)!=16 or len({p['path'] for p in plans})!=16:raise RuntimeError('修改清單數量不符')
    updates={seed_path:encoded(batch)}
    for plan in plans:
        name=plan['path']
        if name in SKIP:continue
        path=(ROOT/name).resolve()
        if not path.is_relative_to(ROOT) or name.startswith(('.git/','.github/','book/','docs/')):raise RuntimeError('越過本次允許目標')
        before=path.read_bytes() if path.is_file() else None
        if (digest(before) if before is not None else None)!=plan['before']:raise RuntimeError('來源已有修改：'+name)
        lines=(before.decode() if before else '').splitlines(keepends=True)
        for start,end,replacement in reversed(plan['edits']):lines[start:end]=replacement.splitlines(keepends=True)
        after=''.join(lines).encode()
        if digest(after)!=plan['after']:raise RuntimeError('修改內容與本地測試雜湊不同：'+name)
        updates[name]=after
    # 舊版完整章節與PR #6來源測試保留，只新增清楚的閱讀入口說明。
    legacy='locales/zh-TW/book/14-帳號與資訊安全.md'
    old=git('show',BASE+':'+legacy)
    if (ROOT/legacy).read_bytes()!=old:raise RuntimeError('最新整章稿已有其他修改')
    banner='> **逐條閱讀版已另行整合：** 請使用[第14章12份臺灣正文](ch14/README.md)。本頁保留PR #6整章編修稿與來源稽核對照，不作第二套自動取材來源；本批仍沿用同一組主題ID，不重複計數。\n\n'
    updates[legacy]=banner.encode()+old
    policy='tools/tw/ci_language_policy.py'
    original=git('show',BASE+':'+policy)
    if (ROOT/policy).read_bytes()!=original:raise RuntimeError('最新字形政策已有其他修改')
    marker='    report.update(publication_report(base.ROOT,manifest))\n'
    if original.decode().count(marker)!=1:raise RuntimeError('草稿盤點結構不符')
    addition=marker+'''    # 已有內容與完成審閱的核心正文分開計數，不把導航或重複稿件充作新主題。
    reviewed={e['id'] for e in manifest['entries'] if e['status']=='verified'}
    report.update(topics_with_any_content=len(covered|legacy),
                  topics_with_unreviewed_content=len((covered|legacy)-reviewed),
                  topics_without_content=len(all_ids-covered-legacy),
                  core_reviewed_entries=report['publication_completed_entries'])
'''
    updates[policy]=original.decode().replace(marker,addition).encode()
    for name in ('localization/manifest.json','localization/tw-edition/runtime.json'):
        if (ROOT/name).read_bytes()!=git('show',BASE+':'+name):raise RuntimeError('來源資料已有並行修改：'+name)
    manifest=json.loads((ROOT/'localization/manifest.json').read_text())
    runtime=json.loads((ROOT/'localization/tw-edition/runtime.json').read_text())
    sources={s['id']:s for s in batch['sources']};date=batch['reviewed_at'];due=batch['review_due_at']
    if len(sources)!=14 or {e['id'] for e in batch['entries']}!={f'TW-14-{n:03}' for n in range(1,13)}:raise RuntimeError('章節或來源數量不符')
    for entry in batch['entries']:
        key=entry['id'];target=f'locales/zh-TW/book/ch14/{key}.md'
        body=f'# {entry["title"]}\n\n<!-- TW-ID: {key} -->\n\n'
        body+='\n\n'.join(f'## {heading}\n\n{text}' for heading,text in entry['paragraphs'])
        body+='\n\n## 已核對來源\n\n'+'\n\n'.join(f'[{sources[s]["title"]}]({sources[s]["url"]})' for s in entry['source_ids'])+'\n'
        checks=[dict(url=sources[s]['url'],claim=entry['title']+'：'+sources[s]['supports'],supporting_passage='編者摘要（非逐字引文）：'+sources[s]['supports'],accessed_at=date) for s in entry['source_ids']]
        review=dict(id=key,reviewer=batch['reviewer'],jurisdiction='TW',reviewed_at=date,review_due_at=due,target_path=target,target_sha256=digest(body.encode()),source_checks=checks,localization_changes=entry['localization_changes'],legal_scope=entry['legal_scope'],review_method='逐一開啟第一手來源核對；先分清制度、標準、廠商操作與編者建議，再作台灣改寫。不是自動爬到網址即升級狀態。')
        review_path=f'localization/reviews/{key}.json'
        if (ROOT/target).exists() or (ROOT/review_path).exists():raise RuntimeError('不得覆寫既有正文或審閱：'+key)
        updates[target]=body.encode();updates[review_path]=encoded(review)
        item=next(e for e in manifest['entries'] if e['id']==key)
        item.update(treatment='taiwan_rewrite',status='verified',target_path=target,sources=[sources[s]['url'] for s in entry['source_ids']],verified_at=date)
        runtime['items'].append(dict(id=key,title=entry['title'],body=body,limits=entry['limits'],source_ids=entry['source_ids'],review_status='source_checked',reviewed_at=date,review_due_at=due,eligibility={},target_path=target,chapter=14,evidence_type='第一手來源核對與台灣適用性改寫；非獨立專業簽證',question=f'我已瞭解「{entry["title"]}」的做法、來源與適用限制。'))
    runtime['sources']+=batch['sources'];runtime['updated_at']=date
    runtime['scope']='本版收錄第14章帳號與資訊安全12條台灣實質改寫，以及9則急救／篩檢補充導航，共21項。全書765條僅12條完成本批AI輔助來源核對與閱讀整合，其餘尚未定稿；不等於獨立專業審閱或法律個案意見。'
    updates['localization/manifest.json']=encoded(manifest);updates['localization/tw-edition/runtime.json']=encoded(runtime)
    updates['localization/tw-edition/sources/ch14.json']=encoded({'sources':[[s['id'],s['title'],s['url'],s['supports']] for s in sources.values()]})
    index='# 第14章：帳號與資訊安全（台灣改寫）\n\n本章逐條對應原作12個主題，並已整合進預設閱讀及匯出。來源核對是AI輔助編修，不代表獨立法律或資安專業簽證。\n\n'
    index+='\n'.join(f'- [{e["id"]} {e["title"]}]({e["id"]}.md)' for e in batch['entries'])+'\n\n[台灣版閱讀說明](../../README.md)\n'
    updates['locales/zh-TW/book/ch14/README.md']=index.encode()
    for name,expected in [('localization/manifest.json','55de8f3802a933324ba203758f2bff2e314565aa7a739a6769cbb1beeb58d77d'),('localization/tw-edition/runtime.json','2b3a8a9437aea5eae5e7eb30f3f345354019046940448f05b16f41bec5e789cd')]:
        if digest(updates[name])!=expected:raise RuntimeError('整合資料與已測試版本不同：'+name)
    # 只校正本輪新寫的進度文案字形；不改動PR #6內容或已核對的實質正文。
    import text_integrity
    paths=text_integrity.protected_paths()
    for name in ('PROJECT_STATE.md','locales/zh-TW/README.md','localization/ch14-localization.md'):
        updates[name]=text_integrity.normalized((ROOT/name).read_text(),paths).encode()
    for name,raw in updates.items():
        path=ROOT/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
    for n in range(4):(ROOT/f'tools/tw/_ch14_changes{n}.json').unlink()
    from ci_language_policy import audit_drafts
    report=audit_drafts()
    expected_counts={'topics_with_any_content':388,'topics_without_content':377,'topics_with_unreviewed_content':376,'core_reviewed_entries':12,'registry_sources':118,'unresolved_reference_occurrences':583}
    if any(report.get(k)!=v for k,v in expected_counts.items()) or len(report['unresolved_source_ids'])!=163:raise RuntimeError('與最新main整合後的實際盤點不符')
    (ROOT/'localization/tw-edition/coverage.json').write_bytes(encoded(report))
    for name in ('locales/zh-TW/book/23-學習技能與職涯發展.md','localization/source-audits/20261015-account-skills.json','localization/tw-edition/sources/12-account-skills.json','tools/tw/tests/test_account_skills_content.py','tools/tw/tests/test_ci_policy.py'):
        if (ROOT/name).read_bytes()!=git('show',BASE+':'+name):raise RuntimeError('並行已合併成果不可覆寫：'+name)
    print('12條核心正文、14份來源及21項閱讀內容已整合；PR #6新增稿件、來源與測試保留。尚須完整驗證才提交。')

if __name__=='__main__':main()

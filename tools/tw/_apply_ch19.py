#!/usr/bin/env python3
"""本次第19章已編寫之核對資料整合；只在指定fork與基線執行，不自行查核或部署。"""
from __future__ import annotations
import copy
import hashlib
import json
from pathlib import Path
import subprocess
from traditionalize import ROOT, read, dump, write
from content_validation import load_json

BASE='23c6f7b506fa22b98cf0232c1f78c515308f6d6b'
BRANCH='tw/ch19-labor-reviewed-20261016'
NUMBERS=(1,2,3,4,5,6,7,8,17,20,22,23,24)
IDS={f'TW-19-{n:03}' for n in NUMBERS}

def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT,text=True)
def replace(path,old,new):
    content=read(path)
    if old not in content:raise RuntimeError('基線文字不符，停止：'+path+' '+old[:80])
    write(path,content.replace(old,new))

def apply():
    if git('branch','--show-current').strip()!=BRANCH or git('remote','get-url','origin').strip().removesuffix('.git')!='https://github.com/andytwmvp/HowToLiveBetter-TW':
        raise RuntimeError('只允許本次授權fork工作分支')
    subprocess.run(['git','merge-base','--is-ancestor',BASE,'HEAD'],cwd=ROOT,check=True)
    batch=load_json(ROOT/'localization/tw-edition/ch19-reviewed.json')
    if {e['id'] for e in batch['entries']}!=IDS or len(batch['sources'])!=14:raise RuntimeError('章節範圍不符')
    manifest=load_json(ROOT/'localization/manifest.json');runtime=load_json(ROOT/'localization/tw-edition/runtime.json')
    # 大型共用檔必須仍等於已檢視的main，避免覆蓋其他人的並行修改。
    for path in ('localization/manifest.json','localization/tw-edition/runtime.json'):
        if read(path)!=git('show',BASE+':'+path):raise RuntimeError('共用檔案已有其他更新：'+path)
    old_items=copy.deepcopy(runtime['items']);old_sources=copy.deepcopy(runtime['sources'])
    old_core={e['id']:copy.deepcopy(e) for e in manifest['entries']}
    sources={s['id']:s for s in batch['sources']}
    registry={row[0] for p in (ROOT/'localization/tw-edition/sources').glob('*.json') for row in load_json(p)['sources']}
    if set(sources)&registry or set(sources)&{s['id'] for s in old_sources}:raise RuntimeError('來源ID衝突')
    headings=('適用與目標','實際做法','臺灣入口與效益','成本與風險')
    index=['# 第19章：勞動契約與離職權益（台灣改寫）','',
      '本章24個原作主題中，本批完成下列13條的AI輔助來源核對與閱讀整合；另11條職災、保險、稅務及霸凌等主題仍待處理。不是獨立律師審閱，也不是個案法律意見。','']
    for entry in batch['entries']:
        key=entry['id'];target=f'locales/zh-TW/book/ch19/{key}.md'
        if (ROOT/target).exists() or (ROOT/f'localization/reviews/{key}.json').exists():raise RuntimeError('目標已存在，停止：'+key)
        if len(entry['sections'])!=4 or set(entry['source_ids'])!=set(entry['source_claims']):raise RuntimeError('正文／來源核對缺漏')
        body=f"# {entry['title']}\n\n<!-- TW-ID: {key} -->\n\n"
        body+='\n\n'.join(f'## {heading}\n\n{paragraph}' for heading,paragraph in zip(headings,entry['sections'],strict=True))
        body+='\n\n## 已核對來源\n\n'+'\n\n'.join(f"[{sources[s]['title']}]({sources[s]['url']})" for s in entry['source_ids'])+'\n'
        write(target,body)
        review={'id':key,'reviewer':batch['reviewer'],'jurisdiction':'TW','reviewed_at':batch['reviewed_at'],'review_due_at':batch['review_due_at'],'target_path':target,'target_sha256':hashlib.sha256(body.encode()).hexdigest(),
          'source_checks':[{'url':sources[s]['url'],'claim':entry['title']+'：'+entry['source_claims'][s],
            'supporting_passage':'編者摘要（非逐字引文）：'+entry['source_claims'][s], 'accessed_at':sources[s]['accessed_at']} for s in entry['source_ids']],
          'localization_changes':entry['localization_changes'],
          'legal_scope':'以2026-10-16可讀的現行法規及官方說明核對本條主張；受僱身分、工時制度與個案終止事由另判斷。2026最低工資不預先套用後續年度。',
          'review_method':'逐一開啟第一手法規及主管機關說明，核對各款條件；支持段落是AI輔助編者摘要，不是逐字引文或獨立法律專業簽證。'}
        dump(f'localization/reviews/{key}.json',review)
        current=next(e for e in manifest['entries'] if e['id']==key)
        current.update(treatment='taiwan_rewrite',status='verified',target_path=target,sources=[sources[s]['url'] for s in entry['source_ids']],verified_at=batch['reviewed_at'])
        runtime['items'].append({'id':key,'title':entry['title'],'body':body,'limits':entry['limits'],'source_ids':entry['source_ids'],
            'review_status':'source_checked','reviewed_at':batch['reviewed_at'],'review_due_at':batch['review_due_at'],
            'eligibility':{},'target_path':target,'chapter':19,'evidence_type':'臺灣法規與主管機關第一手說明；編者實務建議另列，非獨立法律簽證',
            'question':f"我已瞭解「{entry['title']}」的適用條件、做法、來源與限制。"})
        index.append(f"- [{key} {entry['title']}]({key}.md)")
    index+=['','[台灣版閱讀說明](../../README.md) · [本批來源與限制](../../../../localization/ch19-localization.md)','']
    write('locales/zh-TW/book/ch19/README.md','\n'.join(index))
    runtime['sources']+=batch['sources'];runtime['updated_at']=batch['reviewed_at'];runtime['review_due_at']=batch['review_due_at']
    runtime['scope']='目前提供第14章12條帳號安全正文、第19章13條勞動契約與離職權益正文，加9則急救／篩檢補充導航，共34項。核心進度25／765；AI輔助來源核對不是獨立专业簽證，未審閱草稿不作正式建議。'.replace('专业','專業')
    assert runtime['items'][:len(old_items)]==old_items and runtime['sources'][:len(old_sources)]==old_sources
    assert all(e==old_core[e['id']] for e in manifest['entries'] if e['id'] not in IDS)
    dump('localization/manifest.json',manifest);dump('localization/tw-edition/runtime.json',runtime)
    dump('localization/tw-edition/sources/ch19.json',{'sources':[[s['id'],s['title'],s['url'],s['supports']] for s in batch['sources']]})
    # 上一輪章節測試只保護自身已完成內容及全部原作識別，不凍結其他章節的合法進度。
    p='tools/tw/tests/test_ch14_content.py'
    replace(p,"self.assertEqual(report['publication_completed_entries'],12)","self.assertGreaterEqual(report['publication_completed_entries'],len(IDS))")
    replace(p,"[s for s in new['sources'] if not s['id'].startswith('ch14_')]","[s for s in new['sources'] if s['id'] in {source['id'] for source in old['sources']}]")
    replace(p,"            if before['id'] in IDS:\n                for key in ('upstream_text_sha256','upstream_commit','upstream_path_uri','id'):self.assertEqual(before[key],after[key])\n            else:self.assertEqual(before,after)","            for key in ('upstream_text_sha256','upstream_commit','upstream_path_uri','id','upstream_chapter','upstream_item','display_path','source_title_zh_tw'):\n                self.assertEqual(before[key],after[key])")
    replace('tools/tw/tests/test_audit_fixes.py',"self.assertEqual(len(data['items']),21)","self.assertGreaterEqual(len(data['items']),21)")
    replace('tools/tw/tests/test_audit_fixes.py',"self.assertEqual({e['id'] for e in data['items']},{f'TW-NAV-{n:03}' for n in range(1,10)}|{f'TW-14-{n:03}' for n in range(1,13)})","self.assertTrue(({f'TW-NAV-{n:03}' for n in range(1,10)}|{f'TW-14-{n:03}' for n in range(1,13)}).issubset({e['id'] for e in data['items']}))")
    replace('tools/tw/check_navigation.py',"    chapter=page.locator('#TW-14-003')",'''    assert page.locator('[data-id^="TW-19-"]').count()==13
    labor=page.locator('#TW-19-004')
    assert labor.locator('h3').count()==5 and '50,000' in labor.inner_text()
    assert labor.locator('a[href="https://law.moj.gov.tw/LawClass/LawAll.aspx?pcode=N0030020"]').count()>=1
    page.locator('#q').fill('最低服務年限')
    assert page.locator('#TW-19-022').count()==1
    page.locator('#reset').click()
    chapter=page.locator('#TW-14-003')''')
    replace('tools/tw/check_navigation.py',"    # 損壞百分比編碼只忽略錨點，不清空可用的安全導航。",'''    page.goto(url+'index.html#TW-19-022',wait_until='domcontentloaded')
    page.wait_for_function('window.TWRuntime && window.TWRuntime.ready')
    page.locator('#TW-19-022').scroll_into_view_if_needed()
    page.screenshot(path=str(review/'chapter19-employment-terms.png'),animations='disabled')
    # 損壞百分比編碼只忽略錨點，不清空可用的安全導航。''')
    replace('tools/tw/check_navigation.py',"'臺灣預設閱讀與自查共用12條核心正文及9則補充導航；未讀取原作或草稿'","f'臺灣預設閱讀與自查共用{len(expected)}項；含第14章及第19章正文，未讀取原作或草稿'")
    description='第14章12條帳號安全、第19章13條勞動契約與離職權益臺灣改寫，加9則急救／篩檢導航；其餘內容仍在編修，未審閱草稿不作正式建議。'
    for p in ('index.html','selfcheck.html'):
        replace(p,'第14章帳號與資訊安全12條臺灣改寫，加9則急救與篩檢導航；全書其餘內容仍在編修，未審閱草稿不作正式建議。',description)
        replace(p,'展示已核對來源的帳號安全正文與補充導航。','展示已核對來源的帳號安全、勞動契約與離職權益正文及補充導航。')
    replace('README.md','[第14章：帳號與資訊安全（12條台灣改寫）](locales/zh-TW/book/ch14/README.md)','[第14章：帳號與資訊安全（12條台灣改寫）](locales/zh-TW/book/ch14/README.md) · [第19章：勞動契約與離職權益（13條）](locales/zh-TW/book/ch19/README.md)')
    replace('README.md','目前的臺灣預設閱讀包含第14章12條實質改寫，以及9則已核對來源的補充導航；','目前的臺灣預設閱讀包含第14章12條與第19章13條實質改寫，加9則已核對來源的補充導航，共34項；')
    replace('REPOSITORY_GUIDE.md','包含第14章帳號與資訊安全12條臺灣改寫，以及9則急救／篩檢補充導航；核心進度為12／765，','包含第14章12條與第19章13條臺灣改寫，以及9則急救／篩檢補充導航；核心進度為25／765，')
    replace('REPOSITORY_GUIDE.md','[直接閱讀第14章的12條正文](locales/zh-TW/book/ch14/README.md)。','[第14章12條正文](locales/zh-TW/book/ch14/README.md) · [第19章13條正文](locales/zh-TW/book/ch19/README.md)。')
    replace('skills/life-decision-guide/README.md','目前有第14章帳號與資訊安全12條正文，加9則急救與篩檢補充導航，共21項，','目前有第14章12條與第19章13條正文，加9則急救與篩檢補充導航，共34項，')
    replace('skills/life-decision-guide/SKILL.md','第14章12條已按固定核心ID完成','第14章12條與第19章13條已按固定核心ID完成')
    from ci_language_policy import audit_drafts
    dump('localization/tw-edition/coverage.json',audit_drafts())
    print('PASS：本批13條正文、審閱、來源與閱讀資料已同步；舊21項內容未改寫。')

if __name__=='__main__':apply()

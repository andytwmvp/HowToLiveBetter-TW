#!/usr/bin/env python3
"""一次性整合已逐項核對的第19章內容；核對本fork、基線及資料雜湊，不在執行時假造查核。"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[2]
BASE='c2472e69a50b9585b1a9e58576b0654fa238e3e2'
BRANCH='tw/ch19-completion-20261016'
REPO='andytwmvp/HowToLiveBetter-TW'
DATA='localization/tw-edition/ch19-completion-reviewed.json'
DATA_SHA='da381ddb7d6a36f4d3e3637d6f6cc11b73a6bf341242196c2af57354b9a509a6'
IDS={f'TW-19-{n:03}' for n in (9,10,11,12,13,14,15,16,18,19,21)}

def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT)
def load(path):return json.loads((ROOT/path).read_text(encoding='utf-8'))
def output(path,value):
    p=ROOT/path;p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(value.rstrip()+'\n',encoding='utf-8')
def dump(path,value):output(path,json.dumps(value,ensure_ascii=False,indent=2))
def replace_once(text,old,new):
    if text.count(old)!=1:raise RuntimeError('基線標記數不符：'+old)
    return text.replace(old,new,1)

def main():
    if git('branch','--show-current').decode().strip()!=BRANCH or git('remote','get-url','origin').decode().strip().removesuffix('.git')!='https://github.com/'+REPO:
        raise RuntimeError('只允許指定fork與隔離分支')
    git('merge-base','--is-ancestor',BASE,'HEAD')
    if hashlib.sha256(json.dumps(load(DATA),ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()!=DATA_SHA:raise RuntimeError('內容與已核對版本不符')
    data=load(DATA)
    if {e['id'] for e in data['entries']}!=IDS or len(data['entries'])!=11 or len(data['sources'])!=20:raise RuntimeError('本批範圍不符')
    changed_existing=['localization/manifest.json','localization/tw-edition/runtime.json','localization/tw-edition/coverage.json','locales/zh-TW/book/ch19/README.md','PROJECT_STATE.md','README.md','REPOSITORY_GUIDE.md','index.html','selfcheck.html','locales/zh-TW/README.md','skills/life-decision-guide/README.md','skills/life-decision-guide/SKILL.md','tools/tw/check_navigation.py']
    for name in changed_existing:
        if (ROOT/name).read_bytes()!=git('show',BASE+':'+name):raise RuntimeError('基線已有其他修改，停止：'+name)
    manifest=load('localization/manifest.json');runtime=load('localization/tw-edition/runtime.json')
    old_runtime=json.loads(json.dumps(runtime))
    sources={s['id']:s for s in runtime['sources']}
    registry={r[0] for p in (ROOT/'localization/tw-edition/sources').glob('*.json') for r in json.loads(p.read_text())['sources']}
    for source in data['sources']:
        if source['id'] in sources or source['id'] in registry:raise RuntimeError('來源ID碰撞：'+source['id'])
        sources[source['id']]=source
    generated={}
    for item in data['entries']:
        if len(item['sections'])!=4 or set(item['source_claims'])!=set(item['source_ids']):raise RuntimeError('正文或逐項來源主張缺漏')
        body='# '+item['title']+'\n\n<!-- TW-ID: '+item['id']+' -->\n'
        for label,section in zip(('適用與目標','實際做法','臺灣入口與效益','成本與風險'),item['sections'],strict=True):body+='\n## '+label+'\n\n'+section+'\n'
        body+='\n## 已核對來源\n\n'+'\n\n'.join('['+sources[s]['title']+']('+sources[s]['url']+')' for s in item['source_ids'])+'\n'
        target='locales/zh-TW/book/ch19/'+item['id']+'.md'
        generated[target]=body
        review={'id':item['id'],'reviewer':data['reviewer'],'jurisdiction':'TW','reviewed_at':data['reviewed_at'],'review_due_at':data['review_due_at'],'target_path':target,'target_sha256':hashlib.sha256(body.encode()).hexdigest(),'source_checks':[{'url':sources[s]['url'],'claim':item['title']+'：'+item['source_claims'][s],'supporting_passage':'編者摘要（非逐字引文）：'+item['source_claims'][s],'accessed_at':data['reviewed_at']} for s in item['source_ids']],'localization_changes':item['localization_changes'],'legal_scope':'逐項核對2026-10-16可讀的法規及官方說明。健檢須分期施行、退職所得按115年度；職災與身分依個案認定，不代替醫師、律師或國稅局。','review_method':'開啟第一手全文及歷史生效條文交叉核對；支持段落為AI輔助編者摘要，未假稱獨立專業簽證。'}
        generated['localization/reviews/'+item['id']+'.json']=json.dumps(review,ensure_ascii=False,indent=2)+'\n'
        found=[e for e in manifest['entries'] if e['id']==item['id']]
        if len(found)!=1 or found[0]['status']=='verified':raise RuntimeError('原作條目不存在或已被其他人審閱')
        found[0].update(treatment='taiwan_rewrite',status='verified',target_path=target,sources=[sources[s]['url'] for s in item['source_ids']],verified_at=data['reviewed_at'])
        runtime['items'].append({'id':item['id'],'title':item['title'],'body':body,'limits':item['limits'],'source_ids':item['source_ids'],'review_status':'source_checked','reviewed_at':data['reviewed_at'],'review_due_at':data['review_due_at'],'eligibility':{},'question':'我已瞭解「'+item['title']+'」的做法與適用限制。','target_path':target})
    for name in generated:
        if (ROOT/name).exists():raise RuntimeError('不能覆寫既有正文或審閱：'+name)
    runtime['sources'].extend(data['sources'])
    runtime.update(updated_at=data['reviewed_at'],review_due_at=data['review_due_at'],scope='目前提供第14章12條及第19章24條臺灣正文，加9則急救／篩檢補充導航，共45項。核心進度36／765；AI輔助來源核對不是獨立專業簽證，其餘草稿仍待審閱。')
    if old_runtime['items']!=runtime['items'][:len(old_runtime['items'])] or old_runtime['sources']!=runtime['sources'][:len(old_runtime['sources'])]:raise RuntimeError('先前正文或來源被改寫')
    for name,value in generated.items():output(name,value)
    dump('localization/manifest.json',manifest);dump('localization/tw-edition/runtime.json',runtime)
    dump('localization/tw-edition/sources/ch19-completion.json',{'sources':[[s['id'],s['title'],s['url'],s['supports']] for s in data['sources']]})
    rows=sorted([e for e in runtime['items'] if e['id'].startswith('TW-19-')],key=lambda e:e['id'])
    if len(rows)!=24:raise RuntimeError('第19章並非24條完整ID')
    output('locales/zh-TW/book/ch19/README.md','# 第19章：勞動、職災與離職權益（台灣改寫）\n\n本章24個原作主題已完成AI輔助逐項來源核對、獨立正文與閱讀整合。前批13條保留，本批補齊11條；不是獨立律師、醫師或稅務專業簽證，亦不是全書765條全部完成。\n\n'+'\n'.join('- ['+e['id']+' '+e['title']+']('+e['id']+'.md)' for e in rows)+'\n\n[台灣版閱讀說明](../../README.md) · [前批13條來源](../../../../localization/ch19-localization.md) · [本批11條來源與時效](../../../../localization/ch19-completion.md)')
    for name in ['README.md','REPOSITORY_GUIDE.md','index.html','selfcheck.html','skills/life-decision-guide/README.md','skills/life-decision-guide/SKILL.md']:
        content=(ROOT/name).read_text(encoding='utf-8')
        # 只修改編修統計與章節入口，不改原作統計、圖片文案或法律正文數字。
        content=content.replace('第19章13條','第19章24條').replace('共34項','共45項').replace('核心進度為25／765','核心進度為36／765').replace('勞動契約與離職權益（13條）','勞動、職災與離職權益（24條）').replace('第19章24條勞動契約與離職權益','第19章24條勞動、職災與離職權益')
        output(name,content)
    nav=(ROOT/'tools/tw/check_navigation.py').read_text(encoding='utf-8')
    needle="    page.screenshot(path=str(review/'chapter19-employment-terms.png'),animations='disabled')"
    addition='''
    page.goto(url+'index.html#TW-19-009',wait_until='domcontentloaded')
    page.wait_for_function('window.TWRuntime && window.TWRuntime.ready')
    health=page.locator('#TW-19-009')
    assert health.locator('h3').count()==5 and '2028-01-01' in health.inner_text()
    assert health.locator('a[href*="LawOldVer.aspx"]').count()>=1
    page.locator('#q').fill('191,000')
    assert page.locator('#TW-19-018').count()==1
    assert '不是稅額' in page.locator('#TW-19-018').inner_text()
    page.locator('#reset').click()
    page.set_viewport_size({'width':390,'height':844})
    page.goto(url+'index.html#TW-19-016',wait_until='domcontentloaded')
    page.wait_for_function('window.TWRuntime && window.TWRuntime.ready')
    bullying=page.locator('#TW-19-016')
    assert '最高負責人' in bullying.inner_text() and '2026-07-01' in bullying.inner_text()
    bullying.scroll_into_view_if_needed()
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1')
    page.screenshot(path=str(review/'chapter19-occupational-rights.png'),animations='disabled')
    page.set_viewport_size({'width':1440,'height':1000})
'''
    output('tools/tw/check_navigation.py',replace_once(nav,needle,needle+addition))
    output('localization/ch19-completion.md',DOC)
    # 所有新JSON已就位後再盤點；清單本身不被當成新條目。
    from ci_language_policy import audit_drafts
    report=audit_drafts()
    dump('localization/tw-edition/coverage.json',report)
    report=audit_drafts();dump('localization/tw-edition/coverage.json',report)
    if report['publication_completed_entries']!=36 or report['unique_draft_entries']!=388:raise RuntimeError('核心／去重進度與預期不符')
    missing=len(report['unresolved_source_ids']);refs=report['unresolved_reference_occurrences'];registry_count=report['registry_sources']
    output('locales/zh-TW/README.md',f'''# 臺灣版正文、來源與閱讀入口

[第14章帳號安全](book/ch14/README.md) · [第19章勞動、職災與離職權益](book/ch19/README.md) · [本地閱讀與匯出](../../REPOSITORY_GUIDE.md)

目前第14章12條與第19章24條核心正文具AI輔助来源核對、逐條審閱紀錄與閱讀整合，加原有9則補充導航，共45項。核心完成36／765，不把補充導航算成核心正文，也不把其他未審閱草稿列為完成。

網站、自查、Skill及HTML／EPUB／Anki使用同一份[runtime.json](../../localization/tw-edition/runtime.json)。第19章新內容已區分健檢現行頻率與2028年新規、職災保險與僱主補償、2026年已施行的霸凌規定，以及115年度退職所得額度。這些是AI輔助編修，不是獨立法律、醫療或稅務專業簽證。[來源與時效記錄](../../localization/ch19-completion.md)逐項說明限制。

## 稿件與全書進度

結構化草稿14章373條不變；去重仍涵蓋388個主題，377個尚無稿件，已有稿件但未完成審閱整合者352個。來源登錄{registry_count}個ID，尚有{missing}個來源ID、{refs}處引用未完成登錄；同一ID可能被多處引用，登錄也不等於相關章節的主張均已查核。

[原作繁體來源稿](../../source.html)保留34章765條與搜尋、分級及長文功能。原作與未審閱草稿不能當成臺灣現行制度，來源載入失敗不回退使用它們。完整出版驗收仍應拒絕通過。

## 本地操作

```sh
node tools/offline/build.mjs
node tools/epub/build.mjs
node tools/anki/build.mjs
```

三種產物含相同36條核心正文與9則補充導航。原作預覽必須依[來源建置說明](../../REPOSITORY_GUIDE.md#source-preview)明確指定`--source-preview`。不把結構測試當成所有閱讀器或Anki用戶端匯入驗收；不發布全書定稿。

[工作進度](../../PROJECT_STATE.md) · [原作與授權](../../ATTRIBUTION.md)
'''.replace('来源','來源'))
    output('PROJECT_STATE.md',f'''# HowToLiveBetter-TW 工作狀態

唯一寫入目標：`{REPO}`。不向上游PR、issue、留言或推送；保留署名、授權、分支與歷史，不部署Pages、發布Release或更改通知。

## 已整合基線與本批

PR #8已將第19章13條及先前第14章12條整合至main，基線`{BASE}`。本批工作分支`{BRANCH}`補完第19章其餘009至016、018、019及021，共11個原作主題。原有34項閱讀資料及來源逐項保留；舊草稿與原作正文不覆蓋。

本章24條現在都有獨立臺灣正文、AI輔助來源核對與審閱紀錄；不是獨立律師、醫師或稅務專業簽證。每條均附适用、做法、效益、成本、風險及改寫說明，來源支持段落為編者摘要而非逐字引文。核對日期2026-10-16，複查期限2026-12-31。

[完整第19章](locales/zh-TW/book/ch19/README.md) · [本批來源與生效規則](localization/ch19-completion.md) · [第14章](locales/zh-TW/book/ch14/README.md)

## 實質修正

一般健檢依條文生效時間處理，不把2028-01-01才適用的新頻率提前套到2026年。職安法2026-07-01已施行的霸凌規定、最高負責人申訴與其他程序期限分開，不以法規公佈日當成所有條文同日生效。

職災先救治、合法留存工作關聯；通勤排除事由不泛化，傷病、失能、死亡各按資格。災保一般5年請求權與勞基法補償2年分開，醫療核退另有期限；保險與僱主責任不可一律相加。漏報災保的法定效力與其他未加保補助分開，不套普通勞保5人門檻。

退職所得採115年度206,000／414,000及分期894,000額度，數值範例結果191,000是所得額而非稅額。保險銜接、低報、勞退、健保与就保各自核對，不保證更正後全部損失自動追回，也不提供保證免稅方案。

## 精確進度

核心完成36／765，729條仍未完成来源核對紀錄與閱讀整合。網站、自查、Skill及三類匯出共45項：36條核心加9則補充導航。原有醫療導航與第14章內容未改，本批11題原先均有草稿，不重複算新主題。

去重仍涵蓋388個主題；377個尚無稿件，352個已有稿件但未完成審閱整合。結構化草稿14章373條不變。登錄來源{registry_count}個ID；尚未登錄{missing}個ID、涉及{refs}處引用。新增20筆來源中補齊的既有ID，不代表所有其他章節使用這些來源的主張也已查核。

## 驗證與合併邊界

正文、manifest、runtime及逐條review的ID、路徑、來源、日期與SHA-256須一致。新增第19章全章覆蓋、時效界線、給付區別、年度稅額範例及保留舊內容的回歸；瀏覽器新增健檢歷史法規連結、退職所得搜尋與霸凌手機正文，日常來源／JSON／字形／圖片／匯出／內部連結與既有瀏覽器測試不省略。

本檔於提交前更新；最新PR、main的測試與合併SHA以GitHub實際結果為準，不预填成功。一次性套用腳本與快照工作流程在交付PR前移除。全書完整出版門檻仍未通過，沒有將工程綠燈當成全書或專業驗收。

原作、舊草稿、圖片像素與兩份授權保留，不恢復廣告。About首頁設定仍待處理。不假稱Anki桌面匯入、全部閱讀器或EPUBCheck正式驗收完成。

本次/mnt/data、/tmp及dist專用暫存不再需要時清除，保留原始附件，不交付字型、依賴或私人資料。
'''.replace('适用','適用').replace('与就保','與就保').replace('来源','來源').replace('预填','預填'))
    print('PASS：第19章24條與45項閱讀整合；核心36／765；來源登錄',registry_count,'，未登錄',missing,'／',refs)

DOC='''# 第19章補完：職災、保險、霸凌與退職所得

本批以PR #8已合併的c2472e69為基線，補完11條：009至016、018、019及021，完整第19章共24條。原有13條及第14章12條、9則補充導航原样保留，不能將本批已具草稿的主題重算為新主題。

## 查核與施行版本

核對日期2026-10-16；第19章本批複查期限2026-12-31。資料集[ch19-completion-reviewed.json](tw-edition/ch19-completion-reviewed.json)收錄20個具名來源及各條主張對應。另重用已登錄的勞基法、國健署急救與1925資料，但沒有改寫原來源物件。逐條審閱紀錄在reviews/，明示AI輔助摘要，不是獨立專業簽證。

健檢必須交叉讀2026-06-26修正的健康保護規則第29條與原2021版本第17條。新第17條60歲及2／3年頻率要到2028-01-01才施行；2026年仍用既有65歲及1／3／5年。其他已生效條文不因採用原第17條就全部退回歷史版本。

職安法與霸凌核心規則自2026-07-01施行，嚴重個案不以持續發生為要件；最高負責人外部申訴有特定期限，不拿來替代所有內部、性騷擾、民事或刑事期限。已公佈、分階段施行與實際適用對象分開記錄。

職災認定、健檢與職業醫學服務、保險傷病／失能／死亡給付、僱主補償及其他未保補助分開，不能一筆全包或保證必賠。保險一般5年與僱主補償2年不是醫療核退一律期限；舊事故亦有過渡規定。健康危急先119，不以打卡或48小時外國規則延誤治療。

退職所得以實際領取年度查官方表；115年度206,000／414,000及894,000額度不能沿用114年度或法條原始物價基數。例子191,000是應計所得額，不是應繳稅額；具體身分與特殊給付仍須核對。

## 閱讀與驗證

正文、runtime、manifest及review按同一原作ID與SHA-256對照；網站、自查、Skill及HTML／EPUB／Anki共用45項。來源ID登錄減少草稿索引缺口，但不代表相關舊草稿每個主張已一併查核。本輪未修改那些草稿，舊稿與正式閱讀資料分開。

回歸驗證完整章節ID、舊34項資料不被重寫、來源對照、施行時間區別、保險與僱主責任、所得額範例及閱讀／匯出一致性。瀏覽器查看新正文、歷史條文連結、搜尋、手機及離線。每一次最終PR和main仍需完整通過，不以隔離測試代替；沒有關閉通知或略過測試。

完整全書仍有729條未完成核對整合，不發布全書定稿；不宣稱法律、醫療、稅務專業意見或所有用戶端驗收。原作署名、授權與圖片保留，不上游寫入、不部署、不發行。一次性工具與不再需要的測試中間檔須清除。
'''.replace('原样','原樣')

if __name__=='__main__':main()

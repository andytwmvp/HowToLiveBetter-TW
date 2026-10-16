#!/usr/bin/env python3
"""一次性第23章整合；固定基線、限定路徑、保留既有正文。"""
from pathlib import Path
import copy
import hashlib
import json
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools/tw'))
from content_validation import load_json,source_url
from text_integrity import normalized
from review_contract import validate_runtime,publication_report
BASE='0c76f150b5979378e04c0fe79bf828f8de460236'
DATE='2026-10-16';DUE='2026-12-31'
STAGES=[f'tools/tw/ch23-input-{n}.json' for n in range(4)]
EPHEMERAL=STAGES+['tools/tw/apply_ch23.py','.github/workflows/ch23-integrate.yml']
ALLOWED=set(EPHEMERAL+['tools/tw/tests/test_ch23_content.py','tools/tw/check_ch23_browser.py'])
def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT,text=True).strip()
def write(path,text):
 dest=ROOT/path;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_text(text,encoding='utf-8')
def dump(path,value):write(path,json.dumps(value,ensure_ascii=False,indent=2)+'\n')
def clean(value):
 if isinstance(value,str):return value if value.startswith('https://') else normalized(value,[])
 if isinstance(value,list):return [clean(v) for v in value]
 if isinstance(value,dict):return {k:clean(v) for k,v in value.items()}
 return value
def replace_once(path,old,new):
 value=(ROOT/path).read_text(encoding='utf-8')
 if value.count(old)!=1:raise RuntimeError('基線文字不同：'+path)
 write(path,value.replace(old,new,1))
assert git('rev-parse','HEAD^')==BASE,'基線不是指定main；須重新讀取並調和'
assert not git('status','--porcelain'),'工作區不乾淨'
assert set(git('diff','--name-only',BASE+'..HEAD').splitlines()).issubset(ALLOWED)
parts=[load_json(ROOT/path) for path in STAGES]
sources=clean(parts[0]['sources']);entries=clean(sum([p['entries'] for p in parts[1:]],[]))
ids={f'TW-23-{n:03}' for n in range(1,26)}
assert len(entries)==25 and {e['id'] for e in entries}==ids
assert len(sources)==22 and len({s['id'] for s in sources})==22
for s in sources:
 s['accessed_at']=DATE
 s['scope_note']='僅支持所列主張；取材方法逐筆揭露，研究與制度不作個人結果保證。'
for e in entries:e['source_ids']=list(e['source_claims'])
entries.sort(key=lambda e:e['id'])
by_source={s['id']:s for s in sources}
for s in sources:
 source_url(s['url']);assert s['id'].startswith('ch23_')
manifest=load_json(ROOT/'localization/manifest.json');runtime=validate_runtime(ROOT)
old_manifest=copy.deepcopy(manifest);old_runtime=copy.deepcopy(runtime)
assert len(runtime['items'])==45
assert not ids & {i['id'] for i in runtime['items']}
assert not set(by_source) & {s['id'] for s in runtime['sources']}
lookup={e['id']:e for e in manifest['entries']}
for e in entries:
 key=e['id'];assert lookup[key]['status']=='pending' and lookup[key]['target_path'] is None
 assert len(e['sections'])==4 and all(len(s)>90 for s in e['sections'])
 assert set(e['source_ids'])==set(e['source_claims']) and set(e['source_ids']).issubset(by_source)
 path=f'locales/zh-TW/book/ch23/{key}.md'
 chunks=['# '+e['title'],f'<!-- TW-ID: {key} -->']
 for heading,body in zip(['適用與目標','實際做法','臺灣入口與效益','成本與風險'],e['sections'],strict=True):chunks += ['## '+heading,body]
 chunks += ['## 已核對來源']
 for sid in e['source_ids']:
  s=by_source[sid];chunks += [f"[{s['title']}]({s['url']})"]
 chunks += ['查閱與AI輔助核對：2026-10-16；複查期限：2026-12-31。取材方法及支持摘要見本條審閱紀錄；不是獨立專業簽證或個案核准。']
 body='\n\n'.join(chunks)+'\n';write(path,body)
 checks=[dict(url=by_source[sid]['url'],claim=e['source_claims'][sid],supporting_passage='編者摘要（非逐字引文）：'+e['source_claims'][sid],accessed_at=DATE,retrieval_method=by_source[sid]['retrieval_method']) for sid in e['source_ids']]
 review=dict(id=key,reviewer='ChatGPT（AI輔助逐項來源核對；非獨立人工、法律、醫療或教育專業簽證）',jurisdiction='TW',reviewed_at=DATE,review_due_at=DUE,target_path=path,target_sha256=hashlib.sha256(body.encode()).hexdigest(),source_checks=checks,localization_changes=e['localization_changes'],legal_scope='依各來源指定段落與取材範圍核對；法規最後修正日不等於所有條文施行日。學位授予法本批不採待施行的第4條及第5條第1項；招生及補助以當期資格另核對。研究只支持已列出的群體結論，不是個人因果或結果保證。',review_method='各來源method個別記錄HTML、機構典藏摘要、出版社摘要或官方搜尋索引摘要。未取得全文者不宣稱全文審閱；不把索引摘要用來新增未見的效應、細目或個案資格。')
 review=clean(review);dump(f'localization/reviews/{key}.json',review)
 lookup[key].update(treatment='taiwan_rewrite',status='verified',target_path=path,sources=[by_source[s]['url'] for s in e['source_ids']],verified_at=DATE)
 runtime['items'].append(dict(id=key,title=e['title'],body=body,limits='AI輔助核對而非獨立專業簽證；個別資格與方案須再確認。取材限制按本條正文及來源紀錄，不把研究平均值當結果保證。',question='我已瞭解「'+e['title']+'」的適用條件、做法及限制',source_ids=e['source_ids'],review_status='source_checked',reviewed_at=DATE,review_due_at=DUE,eligibility={},target_path=path,chapter=23,evidence_type='法規、官方方案或研究依各來源區分；實作框架為編者建議'))
# 不重寫原有45條或來源物件。
for i in runtime['items']:
 if i['id'] in ids:i['limits']=clean(i['limits'])
runtime['sources'].extend(sources);runtime.update(scope='61條核心臺灣正文加9則補充導航，共70項；其餘主題尚在編修。AI輔助來源核對不是獨立專業簽證。',updated_at=DATE,review_due_at=DUE)
assert runtime['items'][:45]==old_runtime['items'] and runtime['sources'][:len(old_runtime['sources'])]==old_runtime['sources']
assert [e for e in manifest['entries'] if e['id'] not in ids]==[e for e in old_manifest['entries'] if e['id'] not in ids]
dump('localization/manifest.json',manifest);dump('localization/tw-edition/runtime.json',runtime)
batch=dict(schema_version=1,base_commit=BASE,reviewed_at=DATE,review_due_at=DUE,scope='第23章25條的來源與改寫摘要；不是逐字引文，按來源揭露取材方法。',sources=sources,entries=entries)
dump('localization/ch23-batch.json',batch)
dump('localization/tw-edition/sources/16-skills.json',{'sources':[[s['id'],s['title'],s['url'],s['supports']] for s in sources]})
write('locales/zh-TW/book/ch23/README.md','# 第23章：學習技能與職涯發展\n\n25個原作主題的臺灣改寫，均有來源支持摘要與AI輔助核對紀錄，不是獨立專業簽證。部分研究及官方資料採摘要或搜尋索引文字，詳見每條正文與審閱方法；未宣稱全文通讀或保證個人結果。\n\n'+'\n'.join(f"- [{e['id']} {e['title']}]({e['id']}.md)" for e in entries)+'\n\n[臺灣版閱讀說明](../../README.md) · [來源及取材紀錄](../../../../localization/ch23-batch.json)\n')
replace_once('README.md','[臺灣版閱讀說明](locales/zh-TW/README.md)','[第23章：學習技能與職涯發展（25條）](locales/zh-TW/book/ch23/README.md) · [臺灣版閱讀說明](locales/zh-TW/README.md)')
replace_once('README.md','第14章12條與第19章24條實質改寫，加9則已核對來源的補充導航，共45項','第14章12條、第19章24條與第23章25條實質改寫，加9則補充導航，共70項')
p='locales/zh-TW/README.md';value=(ROOT/p).read_text()
changes={'[本地閱讀與匯出](../../REPOSITORY_GUIDE.md)':'[第23章學習技能與職涯發展](book/ch23/README.md) · [本地閱讀與匯出](../../REPOSITORY_GUIDE.md)','第14章12條與第19章24條核心正文':'第14章12條、第19章24條與第23章25條核心正文','共45項':'共70項','核心完成36／765':'核心完成61／765','去重仍涵蓋388個主題，377個尚無稿件':'去重涵蓋410個主題，355個尚無稿件','整合者352個':'整合者349個','來源登錄152個ID':'來源登錄174個ID','相同36條核心正文':'相同61條核心正文'}
for a,b in changes.items():
 assert value.count(a)==1,(p,a);value=value.replace(a,b,1)
value += '\n第23章新增22個原先無稿的主題，另承接既有第1、8、9條。來源取材方法見[本批紀錄](../../localization/ch23-batch.json)，摘要核對不冒充全文通讀，研究平均值不作個人結果保證。\n';write(p,value)
p='locales/zh-TW/book/23-學習技能與職涯發展.md';s=(ROOT/p).read_text();write(p,'> 本頁是先前3條草稿，保留供編修對照；目前25條分條正文請見[第23章閱讀入口](ch23/README.md)。\n\n'+s)
p='skills/life-decision-guide/SKILL.md';s=(ROOT/p).read_text();assert '第19章24條' in s
s=s.replace('第14章12條與第19章24條','第14章12條、第19章24條與第23章25條',1)
s+='\n第23章研究與政策資料的取材方法逐來源揭露；只取得摘要或官方索引時，不宣稱全文審閱。研究平均效果不可改寫為保證加薪、錄取、延壽或免於失業；入學及補助資格須核對當期官方公告。\n';write(p,s)
for p in ['index.html','selfcheck.html']:
 s=(ROOT/p).read_text();old='第14章12條帳號安全、第19章24條勞動、職災與離職權益臺灣改寫，加9則急救／篩檢導航；其餘內容仍在編修，未審閱草稿不作正式建議。'
 assert s.count(old)==4,(p,'metadata不同')
 write(p,s.replace(old,'第14章12條帳號安全、第19章24條勞動與職災、第23章25條學習職涯臺灣改寫，加9則補充導航；來源取材限制逐條揭露，其他草稿不作正式建議。').replace('展示已核對來源的帳號安全、勞動契約與離職權益正文及補充導航。','展示具AI輔助來源核對紀錄的帳號安全、勞動與職災、學習職涯正文及補充導航。'))
replace_once('tools/tw/assets_and_browser.py',"result['checks'].extend(check_navigation(page,context,url,review))","result['checks'].extend(check_navigation(page,context,url,review))\n            from check_ch23_browser import check_ch23_browser\n            result['checks'].extend(check_ch23_browser(page,context,url,review))")
# 移除一次性輸入與可寫入流程；日常CI不修改。
for p in EPHEMERAL:(ROOT/p).unlink()
git('add','--all')
from ci_language_policy import audit_drafts
report=audit_drafts()
assert report['publication_completed_entries']==61 and not report['publication_ready']
assert (report['unique_draft_entries'],report['entries_without_any_draft'],report['registry_sources'])==(410,355,174)
assert (len(report['unresolved_source_ids']),report['unresolved_reference_occurrences'])==(140,492)
dump('localization/tw-edition/coverage.json',report)
write('PROJECT_STATE.md',f'''# HowToLiveBetter-TW 工作狀態

唯一寫入目標：`andytwmvp/HowToLiveBetter-TW`。不寫上游、不部署Pages、不發布Release、不強制推送、不刪除分支，不改通知。原作、署名、授權及圖片保留。

## 本批基線與正文

承接PR #9合併`{BASE}`，保留第14章12條、第19章24條與9則補充導航。第23章25條完成臺灣改寫、來源支持摘要、AI輔助審閱紀錄與閱讀整合；不是獨立人工、法律、醫療或教育專業簽證。

[第23章正文](locales/zh-TW/book/ch23/README.md) · [逐項來源與取材方法](localization/ch23-batch.json) · [第19章](locales/zh-TW/book/ch19/README.md) · [第14章](locales/zh-TW/book/ch14/README.md)

核對日期2026-10-16，複查期限2026-12-31。內容分開處理臺灣未成年工作、免學費、招生入口、技能與職訓、資格及加薪、碩博士條件；國際學習研究與教育報酬不變成個人結果保證。已讀HTML、出版社或典藏摘要、官方搜尋索引的取材方法逐筆列出，未取得全文者不冒稱通讀或查完附錄。

## 精確進度

核心61／765，704條仍待來源審閱及閱讀整合。網站、自查、Skill及HTML／EPUB／Anki共用70項，包含61條核心及9則補充導航。既有45項內容與來源物件逐項保留。

去重涵蓋410個主題，355個尚無稿，349個有稿但未完成審閱整合。結構化草稿仍14章373條。第23章既有1、8、9共3個主題不重複算新增，其餘22個新增覆蓋。來源登錄174個ID，140個未登錄ID及492處引用尚待補齊；登錄數不是唯一網址數或全文查核數。

## 驗證與邊界

每條正文、manifest、runtime與review的ID、來源、日期及SHA-256一致。新增第23章全章、資料保全、來源取材、成本情境及誤讀邊界的回歸；瀏覽器增加職訓搜尋、學歷資料、研究限制、手機、自查與離線一致性。保留全部既有96項單元測試及日常來源、字形、JSON、圖片、交叉引用、匯出與瀏覽器檢查。

本檔提交前撰寫，不預填遠端成功或合併；最新狀態以PR與main實際Actions為準。一次性整合腳本、輸入及可寫入流程已移除，日常CI不跳過、不忽略失敗。全書完整出版門檻仍未通過，不宣稱Anki桌面匯入、全部閱讀器、EPUBCheck或專業簽證完成。

About首頁設定仍待處理。所有本批不再需要的/mnt/data、/tmp及dist暫存完成後清除，保留原始附件，不提交字型、依賴或私人資料。
''')
# 只整理本批明確修改文案；原作、圖片及既有45條閱讀物件不變。
for p in ['PROJECT_STATE.md','locales/zh-TW/README.md','skills/life-decision-guide/SKILL.md','index.html','selfcheck.html']:
 write(p,normalized((ROOT/p).read_text(),[]))
git('add','--all')
assert {e['id'] for e in validate_runtime(ROOT)['items']}=={e['id'] for e in old_runtime['items']}|ids
assert publication_report(ROOT)['publication_completed_entries']==61
print('第23章已完成限定路徑整合；尚須完整工程與瀏覽器驗證。')

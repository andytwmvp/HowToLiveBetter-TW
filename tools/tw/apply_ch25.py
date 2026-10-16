"""第25章一次性整合；只處理固定基線及明列路徑，不會重跑全專案轉字。"""
import hashlib
import json
import subprocess
from pathlib import Path
from text_integrity import normalized
from content_validation import load_json, validate_runtime_data
from ci_language_policy import audit_drafts
ROOT=Path(__file__).resolve().parents[2]
BASE='3d010bccdb5f86304c34b454977d65ecb990443a'
EPHEMERAL=['tools/tw/ch25-input-sources.json','tools/tw/ch25-input-entries.json','tools/tw/apply_ch25.py','.github/workflows/ch25-integrate.yml']

def get(path):return load_json(ROOT/path)
def save(path,value):
    p=ROOT/path;p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(value if isinstance(value,str) else json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def old(path):return json.loads(subprocess.check_output(['git','show',BASE+':'+path],cwd=ROOT,text=True))
def replace_once(path,before,after):
    s=(ROOT/path).read_text(encoding='utf-8')
    if s.count(before)!=1:raise ValueError('基線文字不唯一：'+path+' / '+before)
    save(path,s.replace(before,after,1))
def normalize(value):
    if isinstance(value,str):return normalized(value,[])
    if isinstance(value,list):return [normalize(v) for v in value]
    if isinstance(value,dict):return {k:normalize(v) for k,v in value.items()}
    return value

if subprocess.check_output(['git','rev-parse','HEAD^'],cwd=ROOT,text=True).strip()!=BASE:
    raise ValueError('不是指定基線的直接子提交，停止以免覆蓋並行修改')
manifest=get('localization/manifest.json');runtime=get('localization/tw-edition/runtime.json')
if manifest!=old('localization/manifest.json') or runtime!=old('localization/tw-edition/runtime.json'):
    raise ValueError('基線內容已變，停止')
if len(runtime['items'])!=70:raise ValueError('舊閱讀數量不符')
sources=[dict(zip(('id','title','url','supports','evidence_type','published_at'),r,strict=True),accessed_at='2026-10-16',retrieval_method='已取得官方HTML並核對本筆指定條文或段落；查閱日不等於法規整編或發布日，不宣稱個案已獲准。') for r in get('tools/tw/ch25-input-sources.json')['sources']]
entries=[dict(id=f'TW-25-{r[0]:03}',title=r[1],action=r[2],procedure=r[3],cost=r[4],limits=r[5],changes=r[6],source_ids=list(r[7]),source_claims=r[7],question=r[8]) for r in get('tools/tw/ch25-input-entries.json')['entries']]
meta=get('tools/tw/ch25-input-entries.json')
batch=normalize(dict(schema_version=1,chapter=25,base_commit=BASE,reviewed_at='2026-10-16',review_due_at='2026-12-31',title='親友離世後：先安頓，再按期限辦理',reviewer='ChatGPT（AI輔助逐項來源核對；非獨立人工、法律、醫療、稅務或殯葬專業簽證）',sources=sources,entries=entries,limits=meta['limits']))
sources=batch['sources'];entries=batch['entries'];source_by={s['id']:s for s in sources}
ids={f'TW-25-{n:03}' for n in range(1,13)}
if {e['id'] for e in entries}!=ids or len(entries)!=12 or len(source_by)!=27:raise ValueError('第25章輸入數量不符')
registry={s[0] for path in (ROOT/'localization/tw-edition/sources').glob('*.json') for s in load_json(path)['sources']}
if registry & set(source_by):raise ValueError('新增來源ID與現有登錄衝突')
by_id={e['id']:e for e in manifest['entries']}
if ids & {e['id'] for e in runtime['items']}:raise ValueError('不得重複加入已存在正文')
links=[]
for e in entries:
    key=e['id'];path=f'locales/zh-TW/book/ch25/{key}.md'
    if by_id[key]['status']=='verified' or (ROOT/path).exists():raise ValueError('正文已存在，停止')
    if set(e['source_ids'])!=set(e['source_claims']) or len(e['source_ids'])!=len(set(e['source_ids'])):raise ValueError('來源主張不完整')
    body=f"<!-- TW-ID: {key} -->\n\n# {e['title']}\n\n## 適用情境與第一步\n\n{e['action']}\n\n## 實際辦理與判斷\n\n{e['procedure']}\n\n## 成本與預期效益\n\n{e['cost']}\n\n## 限制與容易誤讀的地方\n\n{e['limits']}\n\n## 來源與改寫說明\n\n{e['changes']}\n\n"
    checks=[]
    for sid in e['source_ids']:
        s=source_by[sid];claim=e['source_claims'][sid]
        body+=f"[{s['title']}]({s['url']})\n\n{claim}\n\n"
        checks.append(dict(url=s['url'],claim=claim,supporting_passage='編者摘要（非逐字引文）：'+s['supports'],accessed_at=s['accessed_at'],retrieval_method=s['retrieval_method']))
    body+='核對日期：2026-10-16。複查期限：2026-12-31。AI輔助來源核對，非獨立法律、醫療、稅務或殯葬專業簽證。部分法規頁整編截止早於查閱日；實際申辦仍核對主管機關更新、個案資格與期限。\n'
    if len(body)<850:raise ValueError('正文過短')
    save(path,body)
    save(f'localization/reviews/{key}.json',dict(id=key,reviewer=batch['reviewer'],jurisdiction='TW',reviewed_at=batch['reviewed_at'],review_due_at=batch['review_due_at'],target_path=path,target_sha256=hashlib.sha256(body.encode()).hexdigest(),source_checks=checks,localization_changes=e['changes'],review_method='已讀指定官方HTML或法規段落；支持段落是編者摘要。未讀附件不作細項依據。',limits=batch['limits']))
    by_id[key].update(status='verified',treatment='rewritten',target_path=path,sources=[source_by[s]['url'] for s in e['source_ids']],verified_at=batch['reviewed_at'])
    runtime['items'].append(dict(id=key,title=e['title'],body=body,limits=e['limits'],question=e['question'],review_status='source_checked',reviewed_at=batch['reviewed_at'],review_due_at=batch['review_due_at'],source_ids=e['source_ids'],eligibility={},target_path=path))
    links.append(f"- [{key} {e['title']}]({key}.md)")
runtime['sources'].extend(sources)
runtime.update(scope='73條核心臺灣正文加9則補充導航，共82項；其餘主題尚在編修。AI輔助來源核對不是獨立專業簽證。',updated_at=batch['reviewed_at'])
validate_runtime_data(runtime)
save('localization/ch25-batch.json',batch)
save('localization/tw-edition/sources/17-after-death.json',{'sources':[[s['id'],s['title'],s['url'],s['supports']] for s in sources]})
save('localization/manifest.json',manifest);save('localization/tw-edition/runtime.json',runtime)
save('locales/zh-TW/book/ch25/README.md','# 第25章：親友離世後，先安頓再按期限辦理\n\n12條對應原作固定ID，已完成AI輔助來源核對與閱讀整合，不是獨立專業簽證。死亡登記、知悉繼承、死亡年度所得稅、遺產稅及不動產登記分開追蹤；不以單一期限替代全部程序。\n\n'+'\n'.join(links)+'\n\n[逐項來源與取材限制](../../../../localization/ch25-batch.json) · [臺灣版閱讀說明](../../README.md)\n')
replace_once('README.md','[第23章：學習技能與職涯發展（25條）](locales/zh-TW/book/ch23/README.md)','[第23章：學習技能與職涯發展（25條）](locales/zh-TW/book/ch23/README.md) · [第25章：親友離世後的處理（12條）](locales/zh-TW/book/ch25/README.md)')
replace_once('README.md','第14章12條、第19章24條與第23章25條實質改寫，加9則補充導航，共70項','第14章12條、第19章24條、第23章25條與第25章12條實質改寫，加9則補充導航，共82項')
replace_once('REPOSITORY_GUIDE.md','包含第14章12條與第19章24條臺灣改寫，以及9則急救／篩檢補充導航；核心進度為36／765','包含第14章12條、第19章24條、第23章25條與第25章12條臺灣改寫，以及9則急救／篩檢補充導航；核心進度為73／765')
replace_once('REPOSITORY_GUIDE.md','[第19章24條正文](locales/zh-TW/book/ch19/README.md)。','[第19章24條正文](locales/zh-TW/book/ch19/README.md) · [第23章25條正文](locales/zh-TW/book/ch23/README.md) · [第25章12條正文](locales/zh-TW/book/ch25/README.md)。')
replace_once('locales/zh-TW/README.md','[第23章學習技能與職涯發展](book/ch23/README.md)','[第23章學習技能與職涯發展](book/ch23/README.md) · [第25章親友離世後的處理](book/ch25/README.md)')
replace_once('locales/zh-TW/README.md','第14章12條、第19章24條與第23章25條核心正文','第14章12條、第19章24條、第23章25條與第25章12條核心正文')
replace_once('locales/zh-TW/README.md','共70項。核心完成61／765','共82項。核心完成73／765')
replace_once('locales/zh-TW/README.md','審閱整合者349個。來源登錄174個ID，尚有140個來源ID、492處引用','審閱整合者337個。來源登錄201個ID，尚有137個來源ID、446處引用')
replace_once('locales/zh-TW/README.md','相同61條核心正文','相同73條核心正文')
save('locales/zh-TW/README.md',(ROOT/'locales/zh-TW/README.md').read_text()+'\n第25章補上2026年指定公立殯葬設施減免、書面費用、數位遺產、各類期限及公同共有程序。[本批來源與限制](../../localization/ch25-batch.json)不把政府導航或入口當作個案核准。\n')
replace_once('tools/tw/assets_and_browser.py',"            result['checks'].extend(check_ch23_browser(page,context,url,review))","            result['checks'].extend(check_ch23_browser(page,context,url,review))\n            from check_ch25_browser import check_ch25_browser\n            result['checks'].extend(check_ch25_browser(page,context,url,review))")
for path in EPHEMERAL:
    (ROOT/path).unlink()
report=audit_drafts()
expected={'publication_completed_entries':73,'unique_draft_entries':410,'entries_without_any_draft':355,'registry_sources':201,'unresolved_reference_occurrences':446}
if any(report[k]!=v for k,v in expected.items()) or len(report['unresolved_source_ids'])!=137:raise ValueError('新進度與實際盤點不符')
save('localization/tw-edition/coverage.json',report)
save('PROJECT_STATE.md','''# HowToLiveBetter-TW 工作狀態

唯一寫入目標：`andytwmvp/HowToLiveBetter-TW`。不寫上游、不部署Pages、不發布Release、不強制推送、不刪除分支、不改通知。原作、署名、授權與圖片保留。

## 本批基線與正文

承接PR #10合併`3d010bccdb5f86304c34b454977d65ecb990443a`，保留第14章12條、第19章24條、第23章25條及9則補充導航。新增第25章12條逐項臺灣正文、27筆來源登錄、12份審閱紀錄與閱讀整合。這12個主題原本已有結構化草稿，不重複算新增覆蓋。

[第25章正文](locales/zh-TW/book/ch25/README.md) · [來源與取材限制](localization/ch25-batch.json) · [第23章](locales/zh-TW/book/ch23/README.md) · [第19章](locales/zh-TW/book/ch19/README.md) · [第14章](locales/zh-TW/book/ch14/README.md)

核對2026-10-16，複查期限2026-12-31。內容區分救護與死亡證明、司法相驗、法定許可、指定公立設施減免、契約收費、各類給付、數位帳號、限定責任和拋棄繼承。死亡年度所得稅、遺產稅及不動產登記不是同一期限，公同共有不是單方分割。

2025年殯葬第21條之1修正自2026-01-01施行；中低收入戶指定公立設施減免不泛化成全部費用免費。15日消費申訴處理不是退款保證。法規整編截止、查閱日及施行日分開；金融查詢入口不假稱已讀附件全文或涵蓋全部資產。

## 精確進度

核心73／765，692條仍待來源審閱及閱讀整合。網站、自查、Skill及HTML／EPUB／Anki共用82項，包含73條核心及9則補充導航。基線70項閱讀內容與全部來源物件逐項保留。

去重涵蓋410個主題，355個尚無稿，337個有稿但未完成審閱整合。結構化草稿仍14章373條。來源登錄201個ID，137個未登錄ID及446處引用待補齊；新增consumer、civil1148與civil1174只解除3個ID、46處索引缺漏，不代表其他章節46項主張均已核對。

## 驗證與邊界

每條正文、manifest、runtime與review的ID、來源、日期及SHA-256一致。新增第25章全章、來源保全、期限差異、減免範圍、給付與數位資料界線的回歸。瀏覽器增加殯葬減免搜尋、繼承書籤、手機自查及離線一致性，保留既有全部105項單元及日常文字、JSON、來源、圖片、1,809處交叉引用、匯出與瀏覽器測試。

同步修正REPOSITORY_GUIDE仍停在36條的舊介紹。此檔提交前撰寫，不預填遠端成功；最新結果以PR及main實際Actions為準。一次性輸入、整合腳本與可寫入工作流程已移除；日常CI未關閉或忽略失敗。

AI輔助來源核對不是獨立人工、法律、醫療、稅務或殯葬專業簽證。全書正式出版門檻仍未通過；不宣稱Anki桌面匯入、全部閱讀器或EPUBCheck完成。About首頁設定仍待處理。完成後清除本批不再需要的/mnt/data、/tmp及dist暫存，保留原始附件，不提交字型、依賴或私人資料。
''')
print('第25章整合完成，等待最新全文、來源、匯出與瀏覽器驗證。')

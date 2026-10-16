"""第7章一次性整合：固定基線、明列檔案、保留前版全部閱讀內容。"""
import hashlib
import json
import subprocess
from pathlib import Path
from content_validation import load_json,validate_runtime_data
from ci_language_policy import audit_drafts
ROOT=Path(__file__).resolve().parents[2]
BASE='4dfb5f7b92c7e3c06863d52d1b5f77fb4eee2900'
BRANCH='tw/ch07-living-support-20261016'

def get(path):return load_json(ROOT/path)
def save(path,value):
 p=ROOT/path;p.parent.mkdir(parents=True,exist_ok=True)
 p.write_text(value if isinstance(value,str) else json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def old(path):return json.loads(subprocess.check_output(['git','show',BASE+':'+path],cwd=ROOT,text=True))
def replace(path,before,after):
 s=(ROOT/path).read_text(encoding='utf-8')
 if s.count(before)!=1:raise ValueError('預期基線文字不唯一：'+path+' '+before)
 save(path,s.replace(before,after,1))

branch=subprocess.check_output(['git','branch','--show-current'],cwd=ROOT,text=True).strip()
origin=subprocess.check_output(['git','remote','get-url','origin'],cwd=ROOT,text=True).strip().removesuffix('.git')
if branch!=BRANCH or origin!='https://github.com/andytwmvp/HowToLiveBetter-TW':raise ValueError('僅允許授權fork的指定分支')
subprocess.run(['git','merge-base','--is-ancestor',BASE,'HEAD'],cwd=ROOT,check=True)
# 明文輸入已逐檔比對Git blob；先重建並核對完整正文批次，沒有解碼任意程式。
meta=get('tools/tw/ch07-input-0.json')
limits=meta.pop('limits')
meta['entries']=[e for n in range(1,4) for e in get(f'tools/tw/ch07-input-{n}.json')['entries']]
meta['limits']=limits
raw=json.dumps(meta,ensure_ascii=False,indent=2)+'\n'
if hashlib.sha256(raw.encode()).hexdigest()!='8a387dac7174c037fa772c9d0cea9b664488398495ffa7baee6bea656c371ff6':raise ValueError('明文輸入與本地已測試批次不同')
# 六處已校閱的語境用字修正，僅處理本章新輸入，不動法規網址或舊章節。
raw=raw.replace('不是隻','不是只').replace('到賬','入帳').replace('身份證','身分證')
if hashlib.sha256(raw.encode()).hexdigest()!='b7f44c95262a62abd349e7579284f6397d23b5ea7cf6c3d92c5c2a9dc16e7771':raise ValueError('用字校正與已審查版本不同')
save('localization/ch07-batch.json',raw)
for n in range(4):(ROOT/f'tools/tw/ch07-input-{n}.json').unlink()
manifest=get('localization/manifest.json');runtime=get('localization/tw-edition/runtime.json');batch=get('localization/ch07-batch.json')
if manifest!=old('localization/manifest.json') or runtime!=old('localization/tw-edition/runtime.json'):raise ValueError('基線內容已變更，停止')
if len(runtime['items'])!=82 or len(batch['entries'])!=23 or batch['base_commit']!=BASE:raise ValueError('數量或基線不符')
sources=batch['sources'];entries=batch['entries'];source_by={s['id']:s for s in sources}
if len(source_by)!=len(sources):raise ValueError('來源ID重複')
ids={f'TW-07-{n:03}' for n in range(1,24)}
if {e['id'] for e in entries}!=ids:raise ValueError('章節條目缺漏')
registry={s[0] for path in (ROOT/'localization/tw-edition/sources').glob('*.json') for s in load_json(path)['sources']}
if registry & set(source_by):raise ValueError('來源ID已存在，不得覆寫')
by_id={e['id']:e for e in manifest['entries']};links=[]
if ids & {e['id'] for e in runtime['items']}:raise ValueError('正文重複')
for e in entries:
 key=e['id'];path=f'locales/zh-TW/book/ch07/{key}.md'
 if by_id[key]['status']=='verified' or (ROOT/path).exists():raise ValueError('正文已存在')
 if set(e['source_ids'])!=set(e['source_claims']):raise ValueError('缺少來源主張')
 body=f"<!-- TW-ID: {key} -->\n\n# {e['title']}\n\n## 適用情境與第一步\n\n{e['action']}\n\n## 實際辦理與判斷\n\n{e['procedure']}\n\n## 成本與預期效益\n\n{e['cost']}\n\n## 限制與容易誤讀的地方\n\n{e['limits']}\n\n## 來源與改寫說明\n\n{e['changes']}\n\n"
 checks=[]
 for sid in e['source_ids']:
  s=source_by[sid];claim=e['source_claims'][sid]
  body+=f"[{s['title']}]({s['url']})\n\n{claim}\n\n"
  checks.append(dict(url=s['url'],claim=claim,supporting_passage='編者摘要（非逐字引文）：'+s['supports'],accessed_at=s['accessed_at'],retrieval_method=s['retrieval_method']))
 body+='核對日期：2026-10-16。複查期限：2026-12-31。AI輔助來源核對，非獨立法律、醫療或社福專業簽證。各項救助、服務與給付須依年度、地域、實際資格及承辦核定；申請不等於獲准。取材限制詳見本章來源紀錄。\n'
 if len(body)<850:raise ValueError('正文不完整：'+key)
 save(path,body)
 save(f'localization/reviews/{key}.json',dict(id=key,reviewer=batch['reviewer'],jurisdiction='TW',reviewed_at=batch['reviewed_at'],review_due_at=batch['review_due_at'],target_path=path,target_sha256=hashlib.sha256(body.encode()).hexdigest(),source_checks=checks,localization_changes=e['changes'],review_method='AI輔助核對指定來源段落；各來源方法分別記載，不將摘要、PDF文字層或政府轉載冒充未取得的全文／影像。',limits=batch['limits']))
 by_id[key].update(status='verified',treatment='rewritten',target_path=path,sources=[source_by[s]['url'] for s in e['source_ids']],verified_at=batch['reviewed_at'])
 runtime['items'].append(dict(id=key,title=e['title'],body=body,limits=e['limits'],question=e['question'],review_status='source_checked',reviewed_at=batch['reviewed_at'],review_due_at=batch['review_due_at'],source_ids=e['source_ids'],eligibility={},target_path=path))
 links.append(f"- [{key} {e['title']}]({key}.md)")
runtime['sources'].extend(sources)
runtime.update(scope='96條核心臺灣正文加9則補充導航，共105項；其餘主題尚在編修。AI輔助來源核對不是獨立專業簽證。',updated_at=batch['reviewed_at'])
validate_runtime_data(runtime)
save('localization/tw-edition/sources/18-living-support.json',{'sources':[[s['id'],s['title'],s['url'],s['supports']] for s in sources]})
save('localization/manifest.json',manifest);save('localization/tw-edition/runtime.json',runtime)
save('locales/zh-TW/book/ch07/README.md','# 第7章：收入中斷時，先穩住基本生活\n\n23條對應原作固定ID，完成AI輔助來源核對與閱讀整合，不是個案核准或獨立專業簽證。失業認定、急難救助、急難紓困、家庭收入、健保、職訓、住宅與債務清理分開處理；不把任一窗口或補助當成全國通用保證。\n\n'+'\n'.join(links)+'\n\n[來源取材與限制](../../../../localization/ch07-batch.json) · [臺灣版閱讀說明](../../README.md)\n')
replace('README.md','[第14章：帳號與資訊安全（12條台灣改寫）]','[第7章：收入中斷與基本生活支持（23條）](locales/zh-TW/book/ch07/README.md) · [第14章：帳號與資訊安全（12條台灣改寫）]')
replace('README.md','第14章12條、第19章24條、第23章25條與第25章12條實質改寫，加9則補充導航，共82項','第7章23條、第14章12條、第19章24條、第23章25條與第25章12條實質改寫，加9則補充導航，共105項')
replace('REPOSITORY_GUIDE.md','包含第14章12條、第19章24條、第23章25條與第25章12條臺灣改寫，以及9則急救／篩檢補充導航；核心進度為73／765','包含第7章23條、第14章12條、第19章24條、第23章25條與第25章12條臺灣改寫，以及9則急救／篩檢補充導航；核心進度為96／765')
replace('REPOSITORY_GUIDE.md','[第25章12條正文](locales/zh-TW/book/ch25/README.md)。','[第25章12條正文](locales/zh-TW/book/ch25/README.md) · [第7章23條正文](locales/zh-TW/book/ch07/README.md)。')
replace('locales/zh-TW/README.md','[第14章帳號安全]','[第7章生活支持](book/ch07/README.md) · [第14章帳號安全]')
replace('locales/zh-TW/README.md','目前第14章12條、第19章24條、第23章25條與第25章12條核心正文','目前第7章23條、第14章12條、第19章24條、第23章25條與第25章12條核心正文')
replace('locales/zh-TW/README.md','共82項。核心完成73／765','共105項。核心完成96／765')
replace('locales/zh-TW/README.md','相同73條核心正文','相同96條核心正文')
replace('tools/tw/assets_and_browser.py',"            result['checks'].extend(check_ch25_browser(page,context,url,review))","            result['checks'].extend(check_ch25_browser(page,context,url,review))\n            from check_ch07_browser import check_ch07_browser\n            result['checks'].extend(check_ch07_browser(page,context,url,review))")
# 一次性輸入在執行後即移除，不讓可寫流程進入正式PR。
for name in ('tools/tw/apply_ch07.py','.github/workflows/ch07-integrate.yml','.github/workflows/ch07-source-snapshot.yml'):
 p=ROOT/name
 if p.exists():p.unlink()
report=audit_drafts()
assert report['publication_completed_entries']==96 and report['unique_draft_entries']==410 and report['entries_without_any_draft']==355
save('localization/tw-edition/coverage.json',report)
count=report['registry_sources'];missing=len(report['unresolved_source_ids']);refs=report['unresolved_reference_occurrences']
replace('locales/zh-TW/README.md','審閱整合者337個。來源登錄201個ID，尚有137個來源ID、446處引用',f'審閱整合者314個。來源登錄{count}個ID，尚有{missing}個來源ID、{refs}處引用')
save('locales/zh-TW/README.md',(ROOT/'locales/zh-TW/README.md').read_text()+'\n第7章完成失業、救助、食宿、健保、求職防詐與債務清理分流。[本批來源與限制](../../localization/ch07-batch.json)明列PDF文字層、政府轉載及官方索引文字的取材方式，不以申請入口或年度金額當作個案核定。\n')
save('PROJECT_STATE.md',f'''# HowToLiveBetter-TW 工作狀態

唯一寫入目標：`andytwmvp/HowToLiveBetter-TW`。不寫上游、不部署Pages、不發布Release、不強制推送、不刪除分支、不改通知。原作、署名、授權、圖片與廣告移除成果保留。

## 本批基線與正文

承接PR #11合併`{BASE}`。保留原先73條核心正文及9則補充導航共82項，新增第7章23條臺灣正文、23份逐條審閱紀錄及{len(sources)}筆來源登錄。這23個主題原本已有結構化草稿，不增加主題覆蓋數。

[第7章生活支持](locales/zh-TW/book/ch07/README.md) · [來源取材與限制](localization/ch07-batch.json) · [第25章](locales/zh-TW/book/ch25/README.md) · [第23章](locales/zh-TW/book/ch23/README.md) · [第19章](locales/zh-TW/book/ch19/README.md) · [第14章](locales/zh-TW/book/ch14/README.md)

本輪核對2026-10-16，複查期限2026-12-31。失業給付的資格、退保後二年申請、14日認定與實際入帳分開；戶籍地急難救助和居住地急難紓困分開。低收入認定包含家庭與推計收入，失業例外不等於所有給付均不列收入。1957為08:00至22:00，不是24小時床位服務。

健保銜接、欠費分期及紓困貸款分開；重大傷病不表示全部醫療免費。職訓生活津貼不得與失業給付同領，中央租補115年度的房屋要件與過渡例外不泛化。國保、勞退、刑事更生保護與消費者債務更生各依不同身分及程序，沒有補助核准、工作錄取、理賠或免債保證。

## 精確進度

核心96／765，669條仍待實質來源審閱及閱讀整合。網站、自查、Skill及HTML／EPUB／Anki共105項：96條核心加9則導航；基線82項與原有來源物件完整保留。

全部稿件去重涵蓋410個主題，355個尚無稿；314個已有稿但未完成審閱整合。結構化草稿仍14章373條。來源登錄{count}個ID，尚有{missing}個未登錄ID及{refs}處引用。新增{len(sources)}個來源中，解除{137-missing}個既有索引缺口、{446-refs}處引用；不代表其他章節這些主張全部通過查核。

## 驗證與限制

正文、manifest、runtime與review的固定ID、來源、日期與SHA-256一致。新增全章整合、基線保全、不同給付與申請程序、範圍限制的回歸；瀏覽器驗證1957及救助搜尋、低收推計收入書籤、手機自查及離線23條一致性。保留既有114項單元、來源保全、JSON、1,809處交叉引用、圖片及各類匯出測試，不關閉或省略失敗情境。

最新PR與main驗證以實際Actions為準，這份狀態不提前填成功SHA。一次性整合腳本與快照／可寫工作流程執行後移除。補助核定不是CI能判斷的事，全文出版門檻仍不通過。

急難紓困讀取2026修正PDF文字層本文，截圖工具失敗，未使用未核對影像的附表計分。中央租補申請站本次拒絕連線，以政府指南及國立大學轉知中央函文限定說明；更生保護僅使用官方索引可取得的對象與意願段落，不引用未讀流程圖及金額。部分法規整編早於取材日，查閱日與公布／施行日分開，方法逐筆記錄。

AI輔助來源核對不是獨立法律、醫療或社福專業簽證；未宣稱所有用戶端匯入、EPUBCheck或全部外站連通。About首頁設定仍待處理。清除本次不再需要的/mnt/data、/tmp及dist暫存，保留原始附件，不交付字型、依賴或私人資料。
''')
print(json.dumps({k:report[k] for k in ('publication_completed_entries','unique_draft_entries','registry_sources','unresolved_reference_occurrences')},ensure_ascii=False))

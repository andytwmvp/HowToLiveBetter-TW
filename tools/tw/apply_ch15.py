"""本輪第15章整合；保留既有內容，僅在指定fork與工作分支使用。"""
from pathlib import Path
import hashlib
import json
import subprocess
from content_validation import load_json, validate_runtime_data
from ci_language_policy import audit_drafts
ROOT=Path(__file__).resolve().parents[2]
BASE='8607d4dbcaf6bd54a891b227faa0f0b3f711409d'
BRANCH='tw/ch15-housing-20261017'
def get(path):return load_json(ROOT/path)
def save(path,value):
    p=ROOT/path;p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(value if isinstance(value,str) else json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def base(path):return json.loads(subprocess.check_output(['git','show',BASE+':'+path],cwd=ROOT,text=True))
def change(path,before,after):
    value=(ROOT/path).read_text(encoding='utf-8')
    if value.count(before)!=1:raise ValueError('預期文字不唯一：'+path+' '+before)
    save(path,value.replace(before,after,1))

if subprocess.check_output(['git','branch','--show-current'],cwd=ROOT,text=True).strip()!=BRANCH:raise ValueError('非指定分支')
if subprocess.check_output(['git','remote','get-url','origin'],cwd=ROOT,text=True).strip().removesuffix('.git')!='https://github.com/andytwmvp/HowToLiveBetter-TW':raise ValueError('非授權fork')
subprocess.run(['git','merge-base','--is-ancestor',BASE,'HEAD'],cwd=ROOT,check=True)
# 來源與正文以明文JSON傳遞，沒有執行任意編碼內容；正文校正僅作用於新批次。
meta=get('tools/tw/ch15-input-0.json')
defaults=meta.pop('source_defaults')
meta['sources']=[dict(defaults,**s) for s in meta['sources']]
meta['entries']=[e for n in range(1,4) for e in get(f'tools/tw/ch15-input-{n}.json')['entries']]
for e in meta['entries']:e['source_ids']=list(e['source_claims'])
from text_integrity import normalized
def clean(value):
    if isinstance(value,str):
        return value if value.startswith('https://') else normalized(value,[]).replace('不是隻','不是只').replace('釦款','扣款').replace('一只警報器','一個警報器').replace('一隻警報器','一個警報器').replace('還是隻','還是只')
    if isinstance(value,list):return [clean(v) for v in value]
    if isinstance(value,dict):return {k:clean(v) for k,v in value.items()}
    return value
batch=clean(meta)
# 測試過的完整明文批次，忽略JSON排版但不忽略內容差異。
canonical=lambda value:json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
if hashlib.sha256(canonical(batch)).hexdigest()!='8a2fd78678dcf49fcb7184c87123a3ceb70be1d08bfd1dacd486432fd5ae05c2':raise ValueError('內容與已核對批次不一致')
save('localization/ch15-batch.json',batch)
for n in range(4):(ROOT/f'tools/tw/ch15-input-{n}.json').unlink()
manifest=get('localization/manifest.json');runtime=get('localization/tw-edition/runtime.json')
if manifest!=base('localization/manifest.json') or runtime!=base('localization/tw-edition/runtime.json'):raise ValueError('基線已有其他變更')
if len(runtime['items'])!=105 or len(batch['entries'])!=18:raise ValueError('數量不符')
ids={f'TW-15-{n:03}' for n in range(1,19)}
if {e['id'] for e in batch['entries']}!=ids:raise ValueError('18條ID不符')
sources={s['id']:s for s in batch['sources']}
if len(sources)!=22 or set(sources)&{s['id'] for s in runtime['sources']}:raise ValueError('來源數量或既有來源衝突')
registry={s[0]:s for p in (ROOT/'localization/tw-edition/sources').glob('*.json') for s in load_json(p)['sources']}
for key,s in sources.items():
    if key in registry and registry[key][2]!=s['url']:raise ValueError('既有來源ID網址不符')
entries={e['id']:e for e in manifest['entries']};links=[]
for e in batch['entries']:
    key=e['id'];path=f'locales/zh-TW/book/ch15/{key}.md'
    if (ROOT/path).exists() or entries[key]['status']=='verified':raise ValueError('不能覆寫既有正文')
    if set(e['source_ids'])!=set(e['source_claims']):raise ValueError('來源主張缺漏')
    body=f"<!-- TW-ID: {key} -->\n\n# {e['title']}\n\n"
    for title,field in [('適用情境與第一步','action'),('實際辦理與判斷','procedure'),('成本與預期效益','cost'),('限制與容易誤讀的地方','limits'),('來源與改寫說明','changes')]:
        body+=f"## {title}\n\n{e[field]}\n\n"
    checks=[]
    for sid in e['source_ids']:
        s=sources[sid];claim=e['source_claims'][sid]
        body+=f"[{s['title']}]({s['url']})\n\n{claim}\n\n"
        checks.append(dict(url=s['url'],claim=claim,supporting_passage='編者摘要（非逐字引文）：'+s['supports'],accessed_at=s['accessed_at'],retrieval_method=s['retrieval_method']))
    body+='核對日期：2026-10-17。複查期限：2026-12-31。AI輔助來源核對，非獨立法律、地政、建築或金融專業簽證；契約與法規按適用時點及個案查核，不保證核貸、交易或求償結果。\n'
    if len(body)<850:raise ValueError('正文不足：'+key)
    save(path,body)
    save(f'localization/reviews/{key}.json',dict(id=key,reviewer=batch['reviewer'],jurisdiction='TW',reviewed_at=batch['reviewed_at'],review_due_at=batch['review_due_at'],target_path=path,target_sha256=hashlib.sha256(body.encode()).hexdigest(),source_checks=checks,localization_changes=e['changes'],review_method='AI輔助核對指定官方條文與段落；每筆來源方法及限制明列，摘要不是逐字引文。',limits=batch['limits']))
    entries[key].update(status='verified',treatment='rewritten',target_path=path,sources=[sources[s]['url'] for s in e['source_ids']],verified_at=batch['reviewed_at'])
    runtime['items'].append(dict(id=key,title=e['title'],body=body,limits=e['limits'],question=e['question'],review_status='source_checked',reviewed_at=batch['reviewed_at'],review_due_at=batch['review_due_at'],source_ids=e['source_ids'],eligibility={},target_path=path))
    links.append(f"- [{key} {e['title']}]({key}.md)")
runtime['sources'].extend(sources.values())
runtime.update(scope='114條核心臺灣正文加9則補充導航，共123項；其餘主題仍在編修。AI輔助來源核對不是獨立專業簽證。',updated_at=batch['reviewed_at'])
validate_runtime_data(runtime)
new_sources=[s for key,s in sources.items() if key not in registry]
if len(new_sources)!=14:raise ValueError('預期新增14個來源ID')
save('localization/tw-edition/sources/19-housing.json',{'sources':[[s['id'],s['title'],s['url'],s['supports']] for s in new_sources]})
save('localization/manifest.json',manifest);save('localization/tw-edition/runtime.json',runtime)
save('locales/zh-TW/book/ch15/README.md','# 第15章：租屋與買房\n\n18條原作主題完成臺灣改寫、AI輔助來源核對及閱讀整合；不是個案法律、建築或核貸簽證。租賃權利、付款授權、預售保障、農舍、房貸與修繕期限按各自制度處理，不沿用中國法規或保證交易結果。\n\n'+'\n'.join(links)+'\n\n[來源與取材限制](../../../../localization/ch15-batch.json) · [臺灣閱讀說明](../../README.md)\n')
change('README.md','[第19章：勞動、職災與離職權益（24條）]','[第15章：租屋、買房與房貸（18條）](locales/zh-TW/book/ch15/README.md) · [第19章：勞動、職災與離職權益（24條）]')
for file in ['README.md','REPOSITORY_GUIDE.md','locales/zh-TW/README.md']:
    change(file,'第7章23條、第14章12條、第19章24條','第7章23條、第14章12條、第15章18條、第19章24條')
for file in ['README.md','locales/zh-TW/README.md']:change(file,'共105項','共123項')
for file in ['REPOSITORY_GUIDE.md','locales/zh-TW/README.md']:change(file,'96／765','114／765')
change('REPOSITORY_GUIDE.md','[第19章24條正文]','[第15章18條正文](locales/zh-TW/book/ch15/README.md) · [第19章24條正文]')
change('locales/zh-TW/README.md','[第19章勞動、職災與離職權益]','[第15章租屋與買房](book/ch15/README.md) · [第19章勞動、職災與離職權益]')
change('locales/zh-TW/README.md','相同96條核心正文','相同114條核心正文')
change('tools/tw/assets_and_browser.py',"            result['checks'].extend(check_ch07_browser(page,context,url,review))","            result['checks'].extend(check_ch07_browser(page,context,url,review))\n            from check_ch15_browser import check_ch15_browser\n            result['checks'].extend(check_ch15_browser(page,context,url,review))")
for name in ['tools/tw/apply_ch15.py','.github/workflows/ch15-snapshot.yml','.github/workflows/ch15-integrate.yml']:
    (ROOT/name).unlink(missing_ok=True)
report=audit_drafts()
assert report['publication_completed_entries']==114 and report['unique_draft_entries']==410 and report['entries_without_any_draft']==355
save('localization/tw-edition/coverage.json',report)
count=report['registry_sources'];missing=len(report['unresolved_source_ids']);refs=report['unresolved_reference_occurrences']
change('locales/zh-TW/README.md','審閱整合者314個。來源登錄237個ID，尚有118個來源ID、345處引用',f'審閱整合者296個。來源登錄{count}個ID，尚有{missing}個來源ID、{refs}處引用')
save('locales/zh-TW/README.md',(ROOT/'locales/zh-TW/README.md').read_text()+'\n第15章完成租金押金、代理收款、買賣不破租賃例外、預售貸款差額、面積找補、交屋期限、青安3.0及瑕疵期間分流。[本批來源與限制](../../localization/ch15-batch.json)明列政策草案、正式契約版本與個案專業核對的差別。\n')
save('PROJECT_STATE.md',f"""# HowToLiveBetter-TW 工作狀態

唯一寫入目標：`andytwmvp/HowToLiveBetter-TW`。上游只讀，保留署名、授權及原作；不部署Pages、不發布Release、不強制推送、不刪除分支、不改通知。

## 本輪正文與基線

承接PR #12合併 `{BASE}`，保留既有105項閱讀資料與全部來源物件。第15章18個主題原本已有結構化草稿；新增18份完整臺灣正文、18份逐條審閱紀錄與22份官方來源核對，其中8個來源ID沿用原登錄網址且不覆寫，新增14個來源ID。

[第15章租屋買房](locales/zh-TW/book/ch15/README.md) · [來源與取材限制](localization/ch15-batch.json) · [第7章生活支持](locales/zh-TW/book/ch07/README.md) · [閱讀指南](REPOSITORY_GUIDE.md)

租賃代收看代管、包租與授權，不沿用中國一律不得代收的規則；押金、法定終止、任意退租與電費分開。買賣不破租賃有公證／年限與抵押執行例外。預售差額30%按預定貸款計，面積不足全找補、超出2%上限與超過3%解除分開；交屋保留款為房地總價5%，四個月備件申辦與六個月通知交屋不混用。

農舍資格、預告登記、房貸總費用、青安3.0、管委會權限及瑕疵期間依各自制度判斷。第365條六個月／五年不是所有請求的單一期限；政策上限、信託名稱、審閱或CI都不是核貸、完工、退款或勝訴保證。

## 進度

核心114／765，651條仍待實質審閱與閱讀整合；runtime、網站、自查、Skill及HTML／EPUB／Anki共123項，另9則導航不計入核心數。
全部稿件去重410個主題，355個尚無稿、296個已有稿未完成；結構化草稿14章373條維持。來源登錄{count}個ID，尚有{missing}個未登錄ID、{refs}處引用。解除2個舊ID與38處引用的索引缺口，不代表其他章節相關主張皆已核對。

## 來源與測試界線

本批核對日2026-10-17，複查期限2026-12-31。官方PDF相關正文與關鍵頁面已檢視；租賃採2025修正，預售採取得的2023整編並對照2026查核，草案消息不自動當成已施行。謄本分級一筆僅取得官方搜尋索引的明確段落；未宣稱取得個案謄本、查驗建物、測試全部外站或申請貸款。青安區域房價與舊案轉換的未讀附件細節不自行補出。

審閱者明示AI輔助來源核對，不是獨立法律、地政、建築或金融專業簽證。既有原作、醫療導航、先前正文、圖片與授權不變。全書完整出版門檻仍不通過。

新增第15章ID、正文、來源、雜湊、數字適用範圍與既有內容保全回歸，瀏覽器測試搜尋、貸款差額書籤、手機押金自查及離線18條一致性。日常CI保留全部125項既有測試、各類匯出、連結與瀏覽器，不略過失敗。最新PR及main結果以本輪Actions為準，不在合併前填成功SHA。

一次性輸入、整合腳本與可寫流程移除；不以新章節凍結後續進度。About首頁設定仍待處理。/mnt/data、/tmp及dist的本次專用暫存不再需要時清除，保留原始附件，不交付字型、依賴或私人資料。
""")
print(json.dumps({k:report[k] for k in ['publication_completed_entries','registry_sources','unresolved_reference_occurrences']},ensure_ascii=False))

"""本批第21章整合：只接續固定基線，不變更已核對的前版正文。"""
import hashlib,json,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
BASE='5b9341aba7d85ab00a9602ebaa34f97cc9a362c1'
BRANCH='tw/ch21-travel-safety-20261017'
def read(p):return json.loads((ROOT/p).read_text(encoding='utf-8'))
def save(p,data):
 p=ROOT/p;p.parent.mkdir(parents=True,exist_ok=True)
 p.write_text(data if isinstance(data,str) else json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def old(p):return json.loads(subprocess.check_output(['git','show',BASE+':'+p],cwd=ROOT,text=True))
def replace(p,a,b):
 t=(ROOT/p).read_text();assert t.count(a)==1,(p,a);save(p,t.replace(a,b,1))
branch=subprocess.check_output(['git','branch','--show-current'],cwd=ROOT,text=True).strip()
origin=subprocess.check_output(['git','remote','get-url','origin'],cwd=ROOT,text=True).strip().removesuffix('.git')
assert branch==BRANCH and origin=='https://github.com/andytwmvp/HowToLiveBetter-TW'
subprocess.run(['git','merge-base','--is-ancestor',BASE,'HEAD'],cwd=ROOT,check=True)
batch=read('tools/tw/ch21-input-0.json');batch['entries']=[]
for i in range(1,4):batch['entries'].extend(read(f'tools/tw/ch21-input-{i}.json')['entries'])
raw=json.dumps(batch,ensure_ascii=False,indent=2)+'\n'
assert hashlib.sha256(raw.encode()).hexdigest()=='a209e1b2c751f629575b4525d76a51297c8aefb02351d1a83e7d20f5651d35d2','批次輸入與已檢查本地版本不符'
manifest=read('localization/manifest.json');runtime=read('localization/tw-edition/runtime.json')
assert manifest==old('localization/manifest.json') and runtime==old('localization/tw-edition/runtime.json'),'正文基線已有其他編修'
assert len(runtime['items'])==123 and len(batch['entries'])==13
ids={f'TW-21-{i:03}' for i in range(1,14)}
assert {e['id'] for e in batch['entries']}==ids
sources={s['id']:s for s in batch['sources']};assert len(sources)==20
registry={s[0] for p in (ROOT/'localization/tw-edition/sources').glob('*.json') for s in json.loads(p.read_text())['sources']}
assert not registry & set(sources)
by_id={e['id']:e for e in manifest['entries']};links=[]
for entry in batch['entries']:
 key=entry['id'];target=f'locales/zh-TW/book/ch21/{key}.md'
 assert by_id[key]['status']!='verified' and not (ROOT/target).exists()
 assert set(entry['source_ids'])==set(entry['source_claims'])
 body=f"<!-- TW-ID: {key} -->\n\n# {entry['title']}\n\n"
 for heading,field in [('適用情境與第一步','action'),('實際辦理與判斷','procedure'),('成本與預期效益','cost'),('限制與容易誤讀的地方','limits'),('來源與改寫說明','changes')]:body+=f"## {heading}\n\n{entry[field]}\n\n"
 checks=[]
 for sid in entry['source_ids']:
  s=sources[sid];claim=entry['source_claims'][sid]
  body+=f"[{s['title']}]({s['url']})\n\n{claim}\n\n"
  checks.append(dict(url=s['url'],claim=claim,supporting_passage='編者摘要（非逐字引文）：'+s['supports'],accessed_at=s['accessed_at'],retrieval_method=s['retrieval_method']))
 body+='來源核對日：2026-10-17；複查期限：2026-12-31。規則可能隨法域、身分與行程改變，出發前再向官方確認。AI輔助來源核對不是獨立領務、法律、保險或醫療專業簽證；本條未代辦入出境、理賠或許可申請。\n'
 assert len(body)>850,(key,len(body))
 save(target,body)
 review=dict(id=key,reviewer=batch['reviewer'],jurisdiction='TW',reviewed_at=batch['reviewed_at'],review_due_at=batch['review_due_at'],target_path=target,target_sha256=hashlib.sha256(body.encode()).hexdigest(),source_checks=checks,localization_changes=entry['changes'],limits=batch['limits'])
 save(f'localization/reviews/{key}.json',review)
 by_id[key].update(status='verified',treatment='rewritten',target_path=target,sources=[sources[s]['url'] for s in entry['source_ids']],verified_at=batch['reviewed_at'])
 runtime['items'].append(dict(id=key,title=entry['title'],body=body,limits=entry['limits'],question=entry['question'],source_ids=entry['source_ids'],review_status='source_checked',reviewed_at=batch['reviewed_at'],review_due_at=batch['review_due_at'],eligibility={},target_path=target))
 links.append(f"- [{key} {entry['title']}]({key}.md)")
runtime['sources'].extend(batch['sources']);runtime.update(updated_at=batch['reviewed_at'],scope='127條核心臺灣正文加9則補充導航，共136項；其餘主題尚在編修。AI輔助來源核對不是獨立專業簽證。')
from content_validation import validate_runtime_data
validate_runtime_data(runtime)
save('localization/ch21-batch.json',batch);save('localization/manifest.json',manifest);save('localization/tw-edition/runtime.json',runtime)
save('localization/tw-edition/sources/20-travel-safety.json',{'sources':[[s['id'],s['title'],s['url'],s['supports']] for s in batch['sources']]})
save('locales/zh-TW/book/ch21/README.md','# 第21章：出國、旅行與境外安全\n\n13條原作主題完成臺灣實質改寫、AI輔助來源核對與閱讀整合。不同國家、旅行文件、警示、保險與檢疫制度分開；不是個案旅行、入境、醫療或法律簽證。\n\n'+'\n'.join(links)+'\n\n[來源、適用範圍與取材限制](../../../../localization/ch21-batch.json) · [臺灣閱讀說明](../../README.md)\n')
replace('README.md','[第23章：學習技能與職涯發展（25條）]','[第21章：出國、旅行與境外安全（13條）](locales/zh-TW/book/ch21/README.md) · [第23章：學習技能與職涯發展（25條）]')
replace('README.md','第19章24條、第23章25條與第25章12條實質改寫，加9則補充導航，共123項','第19章24條、第21章13條、第23章25條與第25章12條實質改寫，加9則補充導航，共136項')
replace('REPOSITORY_GUIDE.md','第19章24條、第23章25條與第25章12條臺灣改寫，以及9則急救／篩檢補充導航；核心進度為114／765','第19章24條、第21章13條、第23章25條與第25章12條臺灣改寫，以及9則急救／篩檢補充導航；核心進度為127／765')
replace('REPOSITORY_GUIDE.md','[第23章25條正文]','[第21章13條正文](locales/zh-TW/book/ch21/README.md) · [第23章25條正文]')
replace('locales/zh-TW/README.md','[第23章學習技能與職涯發展]','[第21章旅行與境外安全](book/ch21/README.md) · [第23章學習技能與職涯發展]')
replace('locales/zh-TW/README.md','第19章24條、第23章25條與第25章12條核心正文','第19章24條、第21章13條、第23章25條與第25章12條核心正文')
replace('locales/zh-TW/README.md','共123項。核心完成114／765','共136項。核心完成127／765')
replace('locales/zh-TW/README.md','去重涵蓋410個主題，355個尚無稿件','去重涵蓋423個主題，342個尚無稿件')
replace('locales/zh-TW/README.md','來源登錄251個ID','來源登錄271個ID')
replace('locales/zh-TW/README.md','相同114條核心正文','相同127條核心正文')
save('locales/zh-TW/README.md',(ROOT/'locales/zh-TW/README.md').read_text()+'\n第21章新增13個原先尚無臺灣稿的主題，包含領務求助、出國登錄、失照、保險、駕車、帶藥與返臺檢疫；不照搬中國的电话、提款或禁止品名單。[本批來源](../../localization/ch21-batch.json)區分目的地例子及未讀附件。\n')
replace('tools/tw/assets_and_browser.py',"            result['checks'].extend(check_ch15_browser(page,context,url,review))","            result['checks'].extend(check_ch15_browser(page,context,url,review))\n            from check_ch21_browser import check_ch21_browser\n            result['checks'].extend(check_ch21_browser(page,context,url,review))")
for path in ['tools/tw/apply_ch21.py','.github/workflows/ch21-integrate.yml','.github/workflows/ch21-snapshot.yml']+[f'tools/tw/ch21-input-{i}.json' for i in range(4)]:
 p=ROOT/path
 if p.exists():p.unlink()
from ci_language_policy import audit_drafts
report=audit_drafts()
assert report['publication_completed_entries']==127 and report['unique_draft_entries']==423 and report['registry_sources']==271 and len(report['unresolved_source_ids'])==116 and report['unresolved_reference_occurrences']==307
save('localization/tw-edition/coverage.json',report)
save('PROJECT_STATE.md',f'''# HowToLiveBetter-TW 工作狀態

唯一寫入目標：`andytwmvp/HowToLiveBetter-TW`。上游只讀；原作署名、授權、圖片與移除廣告成果保留。不部署、不發行、不強制推送、不刪除分支或修改通知。

## 本批第21章

承接PR #13合併 `{BASE}`，既有123項閱讀內容及所有來源物件保持不變。新增13份臺灣正文、13份逐條審閱紀錄與20筆官方來源登錄，並整合网站、自查、Skill及HTML／EPUB／Anki。

[第21章旅行與境外安全](locales/zh-TW/book/ch21/README.md) · [來源與取材限制](localization/ch21-batch.json) · [閱讀指南](REPOSITORY_GUIDE.md)

旅遊警示、入境資格與退費／理賠分開；外交部國內免付費及境外國際電話自付分開；緊急借款例外不是免費補助，也不能說一切狀況絕無協助。境外健保核退由就醫或出院日起算，不是返臺日起算。現金申報不會把超額新臺幣或人民幣合法化；臺灣國際駕照與日本認可譯本制度不同。

護照遺失補發保留當地警方不受理的說明書例外；邀請、移民、帶藥及返臺檢疫按各自法域和實際目的處理，不使用原作中國12308電話、年度提款限制或奶蛋全禁名單。主動申報不等於禁止品可放行。

## 精確進度

核心127／765，638條仍待實質審閱及閱讀整合。網站、自查、Skill與匯出共136項：127條核心加9則補充導航，導航不計入核心完成數。

全部稿件去重423個主題，342個尚無稿、296個已有稿但未完成審閱整合；結構化草稿維持14章373條。此章13個主題原先無臺灣稿，確實增加13個主題覆蓋。來源登錄271個ID，仍缺116個來源ID／307處既有草稿引用；沒有只為降低缺漏數而把不同主張套用相同來源。

## 來源與驗證界線

核對日2026-10-17，複查期限2026-12-31。本章20筆來源均核對指定官方HTML相關正文，未讀附件不當全文；防檢署舊PDF參考表未成功取得，不用它判斷個別奶蛋食品。國別警示、疫情與簽證可能變動，不列未重新確認的當日名單。美國、日本、新加坡僅作各自規則的例子，不泛化為全球或臺灣規定。

AI輔助核對不是獨立領務、法律、醫療、保險或移民專業簽證。未代辦入出境、核貸、理賠、許可或海關申報。完整全書出版門檻仍不通過；不把程式測試代替個案或內容審查。

新增章節ID、正文、來源、日期、雜湊與錯誤推論回歸，保留原有138項測試、來源保全、1,809處交叉引用、圖片、匯出及瀏覽器測試。新增瀏覽器涵蓋13條、現金申報搜尋、求助電話書籤、手機失照自查及離線一致性。最新PR／main結果以實際Actions為準，不提前填成功或合併SHA。

一次性快照、輸入與整合工具在正式PR前移除；日常CI保持唯讀。About首頁設定仍待處理。本批/mnt/data、/tmp與dist專用暫存不再需要時清除，保留原始附件，不交付字型、依賴或私人資料。
'''.replace('网站','網站'))
# One explicit spelling fix in newly written progress prose.
p=ROOT/'locales/zh-TW/README.md';p.write_text(p.read_text().replace('的电话','的電話'))
print({k:report[k] for k in ('publication_completed_entries','unique_draft_entries','registry_sources','unresolved_reference_occurrences')})

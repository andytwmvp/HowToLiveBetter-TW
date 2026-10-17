#!/usr/bin/env python3
"""One-time Taiwan chapter26 integration. Runs only on authorized fork branch after verifying baseline."""
from __future__ import annotations
import hashlib
import json
import subprocess
from pathlib import Path
import text_integrity as guard

ROOT = Path(__file__).resolve().parents[2]
BASE = "212f9e3019a3f8682113a6dcb880817cc44074a3"
BRANCH = "tw/ch26-platform-compliance-20261017"
DAY = "2026-10-17"
DUE = "2026-12-31"
REPO = "andytwmvp/HowToLiveBetter-TW"

# Official text, status and guidance. No new ID replaces historical source records.
NEW = [
("ch26_vat", "財政部：境內網路交易應注意事項", "https://www.etax.nat.gov.tw/etwmain/tax-info/network-transaction-taxtation-area/seller/notice", "114年起純網路銷售貨物每月10萬元及勞務5萬元為特定稅籍起徵點；所得申報、商業登記及統一發票義務另依身分判斷。"),
("ch26_consumer", "消費者保護法第18及19條：通訊交易揭露與解除", "https://law.moj.gov.tw/LawClass/LawAll.aspx?pcode=J0170001", "通訊交易應揭露經營者、價格、付款、解除權及申訴方式；7日解除權有法定合理例外，不是所有數位服務均一律不得退費。"),
("ch26_exception", "通訊交易解除權合理例外情事適用準則", "https://law.moj.gov.tw/LawClass/LawAll.aspx?pcode=J0170012", "無形數位內容或提供即完成的線上服務，須事先同意提供及告知排除7日解除權等前提，不能因商品是數位的就一概免除。"),
("ch26_aml", "數發部：第三方支付洗錢防制及服務能量登錄辦法", "https://law.moj.gov.tw/LawClass/LawAll.aspx?pcode=J0080063", "提供第三方支付須依法具備營業登記、登錄及內控要求；與經金管會許可的電子支付機構業務須依實際金流分別判斷。"),
("ch26_stream", "智慧財產局：網路直播翻唱涉及公開傳輸及重製", "https://www.tipo.gov.tw/tw/copyright/692-63396.html", "直播演唱他人歌曲涉及公開傳輸，提供回看另涉重製；音樂、錄音及表演權利範圍不能混同。"),
("ch26_childsexual", "兒童及少年性剝削防制條例第8條", "https://law.moj.gov.tw/LawClass/LawAll.aspx?pcode=D0050023", "法定條件下網路業者24小時內限制瀏覽或移除兒少性剝削犯罪相關內容，並保存特定資料180日；不適用為所有留言通用保留期。"),
("ch26_siarc", "衛福部性影像處理中心：下架及當事人協助", "https://siarc.mohw.gov.tw/service.php", "非法性影像處理含保留網址線索、隱私保護、通知平台移除及法律轉介；成人與兒少防護途徑有不同要求。"),
("ransomware", "國家資通安全研究院：共通資安及營運持續參考指引", "https://www.nics.nat.gov.tw/cybersecurity_resources/reference_guide/Common_Standards/", "提供系統安全、備援、事件應變與營運持續等實務參考；不等於所有民間小站都有相同法定標準，也不保證付贖金可恢復。"),
("ch26_pdpa_status", "個資委員會籌備處：現行個資法及尚未施行修正", "https://www.pdpc.gov.tw/News_Html/100/", "114年11月修正個資法部分條文包括新第12條尚待施行；當事人通知、業別通報及時限須按實際生效條文處理。")
]

REFS = {
1:"epayment thirdpay ch26_aml",
2:"ch26_vat ch26_consumer companyact",
3:"copyright ch26_stream childact",
4:"pdpa ch26_pdpa_status ransomware",
5:"ch26_consumer ch26_vat pdpa",
6:"ch26_childsexual ch26_siarc copyrightnotice adtakedown",
7:"pdpa ch26_pdpa_status adverify",
8:"childact lsa ch26_consumer",
9:"copyright copyrightnotice",
10:"pdpa ch26_pdpa_status",
11:"ransomware govai pdpa",
12:"pdpa ch26_pdpa_status ransomware",
13:"ch26_consumer ch26_exception renewaldraft"
}

# Additional Taiwan-specific examples; these are editorial implementation advice, not statutory text.
DETAILS = {
1:("先畫出買家、賣家、平台與金流業者的交易圖，逐段標示代收、保管、結算、退款與爭議款實際由誰控制。單純自售與替其他賣家保管款項不可合併稱為技術服務。","登錄、許可及洗錢防制依真實業務判斷，不能只憑網站寫著不經手資金就認定免責；決策前備好實際契約及資金流圖。"),
2:("2026年9月財政部網路交易說明列自2025年起特定網路銷售貨物每月10萬元、勞務5萬元起徵點；這不是全部公司、所得稅或特許營業的免登記門檻。","營利所得、稅籍登記、商業登記、統一發票與特定業務許可是不同流程，實際行業別應向主管機關核對。"),
3:("以偶像演出、球賽轉播或短片為例，先盤點詞曲、錄音、影音畫面、表演及肖像的權利；直播、回看、剪輯、重播與跨平台散布分別核對授權。","智財局指出直播他人歌曲可能涉及公開傳輸，有回看另有重製問題；平台代取得部分授權，不代表離開平台後全部用途也被授權。"),
4:("先做資料流圖，列出雲端區域、遠端維運、客服、AI供應商、備份與次處理者，明訂資料取回、停止服務及銷毀程序。","個資法114年11月修正部分條文尚未施行，不能拿最新法規頁面直接套用尚未生效的第12條新版通報要求。"),
5:("逐筆定義由誰銷售、收款、開立憑證、出貨、退貨與申訴；在訂單、退款、客訴系統留下可供合法查核的紀錄，避免事後分不清責任。","消保法通訊交易原則有7日解除權及法定例外，交易紀錄保存需兼顧稅務必要與個資最小化，不能一律永久保留完整身分證影像。"),
6:("建立分流：一般社群違規、著作權、詐騙廣告、兒少性剝削與成人非自願私密影像，安排不同的緊急處置、申復、封存及稽核權限。","兒少性剝削防制條例第8條的24小時下架與180日保存有明確法定情境，不可套為所有論壇貼文的通用義務；必要時可聯繫衛福部性影像處理中心。"),
7:("把註冊帳號、賣家KYC及受管制廣告主驗證區分，對每種個資列特定目的、權限與保存期限；一般留言不先假設必須交身分證和臉部照片。","個資法的合法事由與告知、安全義務並非只要勾選同意就可以任意蒐集；適用大型廣告平台的規定也不可強加給所有小站。"),
8:("區分兒少註冊、觀看、購買、直播表演與實際受僱工作；設清楚費用、取消、申訴及必要的家長機制，減少兒少被誘導過量消費。","台灣民事成年與童工年齡、兒少性剝削保護及特定商品限齡並非同一門檻，不能直接複製中國未滿16歲一律禁止直播的規則。"),
9:("權利通知要留存作品、權利證明、涉及網址、通知與回復日期，並向被移除內容的使用者提供合理申復方式，不由客服自行做最終權屬裁判。","著作權法第90條之9規定權利人接獲轉送通知次日起10個工作日內提出訴訟證明，與平台最遲自轉送回復通知次日起14個工作日回復之起算點不同。"),
10:("盤點跨境資料的收集、存放、讀取、AI輸入、雲端維運及備援，與廠商契約約定委外責任、事件聯絡、資料退出及是否有次處理者。","國際傳輸不只指硬碟存放海外，跨國處理與遠端利用同樣須檢查；特定金融醫療業別限制及114年個資修法生效狀態不能用一張通用同意書取代。"),
11:("先建立最小可用部署、MFA、更新及權限控管，定義最大可接受停機與備份還原目標，實測供應商停用帳號或資料庫毀損時能否還原。","主機月費之外另算流量、域名、備份、警報、轉出費與維運工時；NICS是重要的資安實務參考，但不是所有民間企業一律適用同等級政府強制標準。"),
12:("啟動事件指揮與分工，優先隔離受入侵帳號、撤換憑證、保全日誌及確認受影響資料；在適當時間以可核對事實通知當事人或主管機關。","114年個資法修正含部分尚未施行通報規範，必須依事故時現行個資法及特定業別辦法核對期限，不能因新聞標題或最新條文頁就說所有企業都須同一時限。"),
13:("在付款處清楚顯示價格、試用到期、下次扣款時間、計費週期、如何取消與退款條件；記錄同意與取消時間，避免預設勾選及模糊選項。","消保法通訊交易7日解除權對數位內容有明確例外條件；2026年網路交易自動續約修正預告不等於已普遍施行固定提醒期限。")
}

def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()

def get(path):
    return json.loads((ROOT/path).read_text(encoding="utf-8"))

def put(path, value):
    p=ROOT/path
    p.parent.mkdir(parents=True, exist_ok=True)
    raw=value if isinstance(value,str) else json.dumps(value,ensure_ascii=False,indent=2)+"\n"
    p.write_text(raw,encoding="utf-8")

def norm(value):
    if isinstance(value,str):return guard.normalized(value,guard.protected_paths())
    if isinstance(value,list):return [norm(x) for x in value]
    if isinstance(value,dict):return {k:norm(v) for k,v in value.items()}
    return value

def replace(path, old, new):
    p=ROOT/path
    raw=p.read_text(encoding="utf-8")
    if raw.count(old)!=1:
        raise RuntimeError("nonunique or missing replacement: "+path+" / "+old[:60])
    p.write_text(raw.replace(old,new,1),encoding="utf-8")

def main():
    if git("branch","--show-current")!=BRANCH or git("remote","get-url","origin").removesuffix(".git")!="https://github.com/"+REPO:
        raise RuntimeError("Only the authorized fork and isolated branch are permitted.")
    subprocess.run(["git","merge-base","--is-ancestor",BASE,"HEAD"],cwd=ROOT,check=True)
    draft=get("localization/tw-edition/chapters/26.json")
    manifest=get("localization/manifest.json")
    runtime=get("localization/tw-edition/runtime.json")
    if len(draft["entries"])!=13 or len(runtime["items"])!=136:
        raise RuntimeError("Baseline changed; stop rather than overwrite new work.")
    registry={}
    for path in sorted((ROOT/"localization/tw-edition/sources").glob("*.json")):
        for row in json.loads(path.read_text(encoding="utf-8"))["sources"]:
            if row[0] in registry and registry[row[0]]!=row:
                raise RuntimeError("Conflicting registered source: "+row[0])
            registry[row[0]]=row
    for row in NEW:
        if row[0] in registry:raise RuntimeError("Duplicate source: "+row[0])
        registry[row[0]]=row
    record={e["id"]:e for e in manifest["entries"]}
    source_runtime={e["id"] for e in runtime["sources"]}
    old_runtime=runtime["items"][:]
    links=[]
    reviewer="ChatGPT（AI輔助來源核對；非獨立法律、支付、稅務、個資或資安專業簽證）"
    for row in draft["entries"]:
        n,title,action,procedure,limits,legacy_refs,level,cost=row
        id=f"TW-26-{n:03}"
        target=f"locales/zh-TW/book/ch26/{id}.md"
        if record[id]["status"]!="pending" or (ROOT/target).exists():
            raise RuntimeError("Already reviewed; refuse overwrite: "+id)
        refs=REFS[n].split()
        if not all(ref in registry for ref in refs):raise RuntimeError("Unregistered cited source")
        context,risk=DETAILS[n]
        source_text="\n\n".join(f"[{registry[s][1]}]({registry[s][2]})\n\n{registry[s][3]}" for s in refs)
        body=(f"<!-- TW-ID: {id} -->\n\n# {title}\n\n"
              f"## 適用情境與第一步\n\n{action}\n\n{context}\n\n"
              f"## 實際辦理與判斷\n\n{procedure}\n\n{risk}\n\n"
              f"## 成本與預期效益\n\n{cost}\n\n先評估法遵、資料治理及事故應變的人力與固定支出；效益是減少不必要的罰則、重工和營運中斷，不是保證營收成長或免除申訴。\n\n"
              f"## 限制與容易誤讀的地方\n\n{limits}\n\n"
              f"## 來源與改寫說明\n\n本條將原作中國網站許可、支付及內容審查規則改成臺灣按實際業務與生效條文核對；技術指引、行政草案與法律不得混為一談。\n\n"
              f"{source_text}\n\n來源核對日：{DAY}；複查期限：{DUE}。上述為編者來源摘要而非逐字引文，AI輔助核對不是獨立專業認證；遇個案前需核實官方現行公告與法域。\n")
        body=guard.normalized(body.replace("不是隻","不是只").replace("到賬","入帳"),guard.protected_paths())
        if len(body)<880:raise RuntimeError("Body too short: "+id+" "+str(len(body)))
        put(target,body)
        source_checks=[dict(url=registry[s][2],claim=f"{id}：{registry[s][3]}",supporting_passage="編者摘要（非逐字引文）："+registry[s][3],accessed_at=DAY,retrieval_method="官方指定條文、說明或指引；沿用既有來源者核對本章適用範圍，未讀附件不作依據。") for s in refs]
        review=dict(id=id,reviewer=reviewer,jurisdiction="TW",reviewed_at=DAY,review_due_at=DUE,target_path=target,target_sha256=hashlib.sha256(body.encode()).hexdigest(),source_checks=source_checks,localization_changes="按臺灣支付、稅籍、消保、著作權、兒少、個資及資安情境重寫；草案與法定義務分開。",review_method="AI輔助逐條對讀官方來源與適用範圍，非獨立專業簽證。",limits=["個資法2025年部分修正尚待施行，不能把新第12條通報機制當現行全部業者共同時限。","第三方支付能量登錄與電子支付許可、消保7日解除與數位內容例外均須個別判斷。","2026自動續約預告及政府資安參考指引不得冒稱現行所有民間業者強制法規。"])
        put(f"localization/reviews/{id}.json",norm(review))
        record[id].update(status="verified",treatment="rewritten",target_path=target,verified_at=DAY,sources=[registry[s][2] for s in refs])
        runtime["items"].append(norm(dict(id=id,title=title,body=body,limits=limits,question="已核對「"+title+"」的法域、適用對象、官方來源與時間條件嗎？",review_status="source_checked",reviewed_at=DAY,review_due_at=DUE,source_ids=refs,eligibility={},target_path=target)))
        links.append(f"- [{id} {title}]({id}.md)")
    for id in sorted(set(" ".join(REFS.values()).split())):
        if id in source_runtime:continue
        r=registry[id]
        runtime["sources"].append(norm(dict(id=id,title=r[1],url=r[2],supports=r[3],published_at=None,accessed_at=DAY,evidence_type="官方法律、行政說明或非強制技術參考",retrieval_method="已核對本章所需條文與適用範圍，未讀附件未作判斷。")))
    runtime["scope"]="140條核心臺灣正文加9則補充導航，共149項；其餘尚在逐條編修，未完成全書正式出版或專業審閱。"
    runtime["updated_at"]=DAY
    put("localization/manifest.json",manifest)
    put("localization/tw-edition/runtime.json",runtime)
    put("localization/tw-edition/sources/21-platform-compliance.json",norm({"sources":[list(s) for s in NEW]}))
    put("localization/ch26-batch.json",{"schema_version":1,"chapter":26,"base_commit":BASE,"reviewed_at":DAY,"review_due_at":DUE,"title":"經營網站與平台：金流、交易、內容與資料治理","reviewer":reviewer,"sources":[dict(id=s[0],title=s[1],url=s[2],supports=s[3],published_at=None,accessed_at=DAY,evidence_type="法規、政府說明或技術指引") for s in NEW],"entries":[dict(id=f"TW-26-{e[0]:03}",title=e[1],source_ids=REFS[e[0]].split()) for e in draft["entries"]],"limits":["草案、尚未施行條文與法定義務分開。","來源摘述並非逐字引文，AI輔助查核不是法律或資安簽證。","原有13個草稿主題進入閱讀整合，覆蓋數不重複增加。"]})
    put("locales/zh-TW/book/ch26/README.md","# 第26章：在臺灣經營網站與平台\n\n13條核心正文已完成AI輔助來源核對與閱讀整合，但不是專業合規簽證。支付、稅務、消保、兒少與個資法依真實業務及施行狀態分開。\n\n"+"\n".join(links)+"\n\n[來源限制](../../../../localization/ch26-batch.json) · [臺灣閱讀說明](../../README.md)\n")
    replace("README.md","[第25章：親友離世後的處理（12條）](locales/zh-TW/book/ch25/README.md) · [臺灣版閱讀說明]","[第25章：親友離世後的處理（12條）](locales/zh-TW/book/ch25/README.md) · [第26章：網站與平台經營（13條）](locales/zh-TW/book/ch26/README.md) · [臺灣版閱讀說明]")
    replace("README.md","第23章25條與第25章12條實質改寫，加9則補充導航，共136項","第23章25條、第25章12條與第26章13條實質改寫，加9則補充導航，共149項")
    replace("REPOSITORY_GUIDE.md","第23章25條與第25章12條臺灣改寫，以及9則急救／篩檢補充導航；核心進度為127／765","第23章25條、第25章12條與第26章13條臺灣改寫，以及9則急救／篩檢補充導航；核心進度為140／765")
    replace("REPOSITORY_GUIDE.md","[第25章12條正文](locales/zh-TW/book/ch25/README.md) · [第7章23條正文]","[第25章12條正文](locales/zh-TW/book/ch25/README.md) · [第26章13條正文](locales/zh-TW/book/ch26/README.md) · [第7章23條正文]")
    replace("locales/zh-TW/README.md","[第25章親友離世後的處理](book/ch25/README.md) · [本地閱讀與匯出]","[第25章親友離世後的處理](book/ch25/README.md) · [第26章網站與平台經營](book/ch26/README.md) · [本地閱讀與匯出]")
    replace("locales/zh-TW/README.md","第23章25條與第25章12條核心正文具AI輔助來源核對","第23章25條、第25章12條與第26章13條核心正文具AI輔助來源核對")
    replace("locales/zh-TW/README.md","共136項。核心完成127／765","共149項。核心完成140／765")
    replace("locales/zh-TW/README.md","三種產物含相同127條核心正文與9則補充導航","三種產物含相同140條核心正文與9則補充導航")
    with (ROOT/"locales/zh-TW/README.md").open("a",encoding="utf-8") as f:f.write("\n第26章補齊平台支付資格、稅籍、訂閱、侵權反通知、兒少內容處置及個資施行差異。[來源摘要](../../localization/ch26-batch.json)不代替實際業者許可與個案專業查核。\n")
    replace("tools/tw/assets_and_browser.py","            result['checks'].extend(check_ch21_browser(page,context,url,review))","            result['checks'].extend(check_ch21_browser(page,context,url,review))\n            from check_ch26_browser import check_ch26_browser\n            result['checks'].extend(check_ch26_browser(page,context,url,review))")
    from ci_language_policy import audit_drafts
    report=audit_drafts()
    if report["publication_completed_entries"]!=140 or report["unique_draft_entries"]!=423:raise RuntimeError("Coverage audit mismatch")
    put("localization/tw-edition/coverage.json",report)
    old_project=(ROOT/"PROJECT_STATE.md").read_text(encoding="utf-8")
    header=(f"# HowToLiveBetter-TW 工作狀態\n\n## 2026-10-17 第26章最新結果\n\n"
            f"新增13條臺灣正文、13份審閱紀錄及9個來源登錄，完整核心140／765，共用閱讀149項。"
            f"仍有625條未完成；423個主題有稿、342個未起稿，283個已有稿待完成審閱。"
            f"來源登錄{report['registry_sources']}個ID，待登錄{len(report['unresolved_source_ids'])}個ID、{report['unresolved_reference_occurrences']}處引用。"
            f"全書出版門檻未通過，工程CI不等於專業審閱。\n\n"
            f"[第26章](locales/zh-TW/book/ch26/README.md) · [來源紀錄](localization/ch26-batch.json)。"
            f"本章分清電子支付與第三方支付、2025個資法尚未施行修正及2026訂閱預告。"
            f"只更新本fork，不向上游寫入、不發布或部署、不改通知。\n\n---\n\n## 第21章前版紀錄（歷史數字，非最新總計）\n\n")
    put("PROJECT_STATE.md",header+old_project.replace("# HowToLiveBetter-TW 工作狀態","",1))
    # Check expected fields and cleanup ephemeral writer before running any unit tests.
    from review_contract import validate_runtime, publication_report
    from pathlib import Path
    validated=validate_runtime()
    if len(validated["items"])!=149 or not set(f"TW-26-{i:03}" for i in range(1,14)).issubset({e["id"] for e in validated["items"]}):
        raise RuntimeError("Validation failed")
    if publication_report()["publication_completed_entries"]!=140:raise RuntimeError("Publication progress mismatch")
    (ROOT/"tools/tw/apply_ch26.py").unlink()
    (ROOT/".github/workflows/ch26-integrate.yml").unlink()
    print("PASS: 13 platform entries, 149 shared runtime items, 140 completed core; temporary workflow removed.")

if __name__=="__main__":main()

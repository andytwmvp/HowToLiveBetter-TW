# HowToLiveBetter-TW 工作狀態

唯一寫入目標：`andytwmvp/HowToLiveBetter-TW`。上游僅供來源比對，不提出PR、issue、留言或推送。保留分支與歷史，不強制推送，不擅自部署Pages或發布Release。

## 已整合基線與目前批次

PR #2已合併至main：`3fac3aa355b19b08497c3dd54a8d315ec4c92f52`，包含臺灣安全導航與稽核修正。

PR #3已合併至main：`1ecec1a605b1959d7feb530d9af12a6d17256d6a`，包含本repo連結治理、隱藏Skill入口、閱讀使用說明、問題回報及來源匯出連結修正。不能再把上一批修補ZIP當成尚未套用的最新成果。GitHub About的homepage仍需另外處理，檔案修改不會自動更新設定。

本輪工作分支`fix/export-integrity-20261015`以PR #3合併版本為基線。修正來源Anki／EPUB沿用上游識別的問題、Anki時間標籤與來源提示，並新增匯出內部連結及離線依賴驗證。隔離驗證`38739114523`成功後才提交來源模組變更；一次性腳本與工作流程已移除，新增檢查整合到日常CI。最後PR／main合併狀態以GitHub實際結果為準，不在合併前填入假造SHA。

[本輪匯出修正與注意事項](localization/export-integrity.md) · [repo閱讀入口](REPOSITORY_GUIDE.md) · [先前連結紀錄](localization/link-audit.md) · [安全稽核修正](localization/audit-fixes.md)

## 預設閱讀與來源稿

index.html、自查、Skill及預設HTML／EPUB／Anki匯出，只使用`localization/tw-edition/runtime.json`中的9則來源核對導航。這些TW-NAV補充ID不計入765個原作主題的全書查核完成數。

原作完整34章、765條繁體稿保留於book/、docs/及source.html；來源搜尋、分級與交叉引用仍可用，但不是臺灣現行制度。需明確指定`--source-preview`才匯出原作預覽。未審閱草稿不成為預設建議，載入錯誤不回退到原作。

## 全書仍未完成

結構化臺灣草稿14章、373條；加入其他Markdown稿去重後為385個主題，380個主題尚無草稿。來源登錄83個ID，另有168個未登錄ID、涉及662處引用。這是草稿與來源索引的缺漏，不是662個已確認失效網址，也不是查核完成數。

本輪未更改上述正文、草稿、醫療導航、圖片像素或來源查核狀態。後續須補齊來源、剩餘主題與實質審閱，不能用新增工程檢查充當完成。`python3 tools/tw/review_contract.py --require-complete`目前應拒絕正式全書輸出。

## 協作與驗收

使用者已明確授權通過驗證後合併安全與工程階段。合併前重新讀取main、工作分支及最新Checks；若已有並行修改則重新比對，不覆寫新成果。一般CI綠燈不代表全書在地化、專業審閱、所有閱讀器或Anki用戶端匯入已完成。

本輪新增13項回歸，共51項。涵蓋兩次來源匯出的穩定且獨立ID、來源卡片提示／時區、HTML錯誤連結與外部依賴、EPUB檔案與錨點。正常CI保留文字、JSON、來源保全、統計、1,809處交叉引用、圖片及瀏覽器測試，未關閉通知或使用continue-on-error。

原作署名、原始版本、來源雜湊與兩份授權保留；不恢復廣告、打賞、贊助或追蹤碼。專案本輪/mnt/data、/tmp與dist中不再需要的暫存完成後清除，保留原始附件，不交付字型或私人資料。

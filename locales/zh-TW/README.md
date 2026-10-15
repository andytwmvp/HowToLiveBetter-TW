# 臺灣版閱讀與編修入口

[第14章：帳號與資訊安全](book/ch14/README.md) · [repo閱讀與建置說明](../../REPOSITORY_GUIDE.md) · [工作狀態](../../PROJECT_STATE.md)

目前預設頁面包含第14章12條臺灣實質改寫及9則急救／篩檢補充導航，共21項。核心進度是12／765，不是765條全書完成，也不是用補充導航充作核心正文。

網站、自查、Skill與HTML／EPUB／Anki共用[runtime.json](../../localization/tw-edition/runtime.json)。每條有適用條件、限制、來源及核對日期；沒有符合項目或資料載入失敗時，不改讀原作或未核對草稿填補。GitHub檔案頁不是部署網站，實際本地閱讀步驟見上述使用說明。

## 內容狀態

[第14章12份正文](book/ch14/README.md)完成本批AI輔助來源核對及閱讀整合，不代表獨立法律或資安專業簽證。PR #6先前的[整章帳號安全稿](book/14-帳號與資訊安全.md)、[第23章3條職涯草稿](book/23-學習技能與職涯發展.md)及來源稽核紀錄仍保留，不以本批覆蓋。

[結構化草稿](../../localization/tw-edition/chapters/)仍為14章373條。全部稿件去重涵蓋388個原作主題，377個尚無稿件；已覆蓋的376個主題仍未完成審閱與正式閱讀整合。163個來源ID、583處引用尚未完成登錄，不能當成全部已查核或全部已失效的網址。

[原作繁體來源稿](../../source.html)保留34章765條及原有搜尋、分級、長文功能，只供來源研究，不是臺灣現行制度。原始版本與兩份授權可追溯。

## 本地匯出

在專案根目錄執行：

```sh
node tools/offline/build.mjs
node tools/epub/build.mjs
node tools/anki/build.mjs
```

產物位於dist，包含相同的12條核心正文與9則補充導航。HTML可離線使用；EPUB／Anki的結構與資料測試不等於所有閱讀器或用戶端匯入驗收。明確需要原作來源預覽時，另依[建置說明](../../REPOSITORY_GUIDE.md#source-preview)使用`--source-preview`，不混稱臺灣版。

全書正式完成門檻：`python3 tools/tw/review_contract.py --require-complete`。目前應回報未完成，不能因CI綠燈或階段合併而改列全書定稿。

[本批來源核對與限制](../../localization/ch14-localization.md) · [署名與授權](../../ATTRIBUTION.md)

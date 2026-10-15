# 臺灣版閱讀與編修入口

[第14章：帳號與資訊安全](book/ch14/README.md) · [第19章：勞動契約與離職權益](book/ch19/README.md) · [閱讀與建置說明](../../REPOSITORY_GUIDE.md)

預設頁面目前提供第14章12條、第19章13條臺灣實質改寫，加9則急救／篩檢補充導航，共34項。核心完成25／765，不把補充導航充作全書正文，也不把第19章其餘11條列為完成。

網站、自查、Skill與HTML／EPUB／Anki共用[runtime.json](../../localization/tw-edition/runtime.json)，每條有適用條件、限制、來源及核對日期。沒有符合項目或資料載入失敗時，不改讀未核對草稿或原作填補。GitHub檔案頁不是已部署的網站，請依本地閱讀說明使用。

## 內容狀態

25條核心正文具AI輔助來源核對紀錄及閱讀整合；不是獨立法律、資安或醫療專業簽證。[第19章本批來源與限制](../../localization/ch19-localization.md)列明法定規則、官方說明及編者建議的界線。

[結構化草稿](../../localization/tw-edition/chapters/)仍有14章373條。去重共388個主題有內容、377個尚無稿件，已有內容但未完成審閱整合者363個。另有154個來源ID、549處引用未完成登錄，不代表全部網址失效或全部主張均錯誤。

原有[帳號安全整章稿](book/14-帳號與資訊安全.md)、[第23章3條職涯草稿](book/23-學習技能與職涯發展.md)與先前來源稽核保留；已核對正文以逐條目錄及runtime為準，不把整個資料夾一律當成已審閱。

[原作繁體來源稿](../../source.html)保留34章765條與搜尋、分級及長文功能，只供來源研究，不作臺灣現行制度建議。

## 本地匯出

在專案根目錄執行：

```sh
node tools/offline/build.mjs
node tools/epub/build.mjs
node tools/anki/build.mjs
```

dist產物包含相同的25條核心正文與9則補充導航。HTML可離線使用，EPUB／Anki結構及資料測試不等於所有用戶端實際匯入驗收。需要原作預覽時，依[來源建置說明](../../REPOSITORY_GUIDE.md#source-preview)明確指定`--source-preview`，不混稱臺灣定稿。

全書完成門檻：`python3 tools/tw/review_contract.py --require-complete`。目前應拒絕完整出版；CI綠燈與階段合併不會讓其自動通過。

[工作狀態](../../PROJECT_STATE.md) · [來源核對紀錄](../../localization/ch19-localization.md) · [署名與授權](../../ATTRIBUTION.md)

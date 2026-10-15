# 臺灣版閱讀與編修入口

[臺灣安全導航開啟方式](../../REPOSITORY_GUIDE.md#reading) · [臺灣自查原始碼](../../selfcheck.html) · [完整工作狀態](../../PROJECT_STATE.md)

目前預設頁面是9則已核對官方來源的急救求助與公費篩檢導航，不是765條全書臺灣版。資料、適用條件、來源與查核日期集中於 [runtime.json](../../localization/tw-edition/runtime.json)，網站、自查、Skill、HTML、EPUB與Anki共用同一份資料。無符合項目或來源載入失敗時，不會改讀未查核草稿填補。

## 原作與草稿分開

[原作繁體來源稿](../../source.html)保留34章、765條與原有搜尋、分級及長文功能，僅供原作研究背景查閱，不能當作臺灣現行制度。原始版本與授權仍可追溯。

[結構化臺灣草稿](../../localization/tw-edition/chapters/)及本目錄的book/尚在編修。14章、373條結構化草稿；合併其他草稿去重為385個主題，380個尚無草稿。另有168個來源ID尚未登錄，涉及662處引用。這些不是正式查核完成數，亦不是已確認失效網址數。

## 本地閱讀與匯出

```sh
python3 -m http.server 8000 --bind 127.0.0.1
# 瀏覽 http://127.0.0.1:8000/ ，停止時按 Ctrl+C。
node tools/offline/build.mjs
node tools/epub/build.mjs
node tools/anki/build.mjs
```

預設產物為dist/HowToLiveBetter-TW.html、.epub、.apkg，僅含目前9則已核對導航。HTML可離線使用；EPUB與Anki已做結構／資料驗證，不宣稱已完成所有閱讀器與Anki用戶端匯入驗收。

明確需要原作工程預覽時，另加 `--source-preview`；EPUB來源版仍需先安裝原有marked依賴。來源預覽與臺灣版不可混稱，原作產物不要當成正式臺灣建議發布。

全書正式完成門檻：`python3 tools/tw/review_contract.py --require-complete`。目前應回報未完成，不會因一般CI綠燈自動改成完成。

[本輪修正與驗收](../../localization/audit-fixes.md) · [署名與授權](../../ATTRIBUTION.md)

連結一律依[目前 repo 入口](../../REPOSITORY_GUIDE.md)與[回報方式](../../SUPPORT.md)使用；沒有發布的產物不導向上游下載。

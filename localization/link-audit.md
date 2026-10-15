# 目前 repo 連結修正紀錄

本輪基線：main `3fac3aa355b19b08497c3dd54a8d315ec4c92f52`。目的為修正導覽與工具取材，不改寫原作研究、臺灣草稿或醫療查核結果。

## 已處理的路徑

| 原本問題 | 本輪處理 |
| --- | --- |
| README 的原作者 PDF／EPUB／Anki／HTML 下載 | 移除，改連結到本 repo 的本地建置說明；沒有捏造本 repo Release 資產。 |
| README 的上游 clone 指令 | 改成 andytwmvp/HowToLiveBetter-TW 與正確的目錄名稱，本地服務只綁定127.0.0.1。 |
| .claude 隱藏 Skill 的上游規則下載 | 改成本地共用 Skill 與此 repo 的唯讀版本；缺檔不回退到上游。 |
| Issue 範本指向初始化分支 | 改成本 repo main 的 SUPPORT.md；Issues 尚未啟用，不提供無效的新建Issue入口。 |
| 原作來源頁的原作者導流 | 改成本地 ATTRIBUTION.md，必要原作署名仍可追溯。 |
| 原作 EPUB 固定最新版下載、Anki 的未部署網站書籤 | 改到實際存在的本 repo 建置說明、原作章節檔與來源。 |
| GitHub Pages 圖片、canonical 與 sitemap | 圖片改用本 repo 實際 PNG 檔；移除尚未部署網站的假定canonical／sitemap及來源頁舊JSON-LD。 |
| 原作手動建置流程誤叫臺灣預設輸出 | 明確加入 --source-preview 及符合原有產物名稱的輸出路徑。 |
| 舊版首頁的 #e-章-條 書籤 | 僅在本地HTTP或未來自有部署中導向source.html，保留相同書籤；不接受任意外站重定向。 |
| README 的其他翻譯／衍生服務宣傳入口 | 從本版主要導覽移除；不改動歷史來源文件與第三方研究。 |

[目前閱讀與建置入口](../REPOSITORY_GUIDE.md) · [問題回報](../SUPPORT.md)

## 刻意保留

原作者作品連結集中在 ATTRIBUTION.md，保留姓名標示與來源；另外保留一份原作歷史核實記錄中對上游issue的引用，避免替換成此repo不相干的同號問題。精確檔案、URL、理由與允許次數列在 link-policy.json。授權與作者姓名不是廣告，不能為了清理連結而抹除。

其他內容的DOI、政府機關、研究來源與原作固定版本識別不做全域替換。這次也不修改來源文件內容、圖片像素、查核日期或狀態。

## GitHub 設定與外部網址限制

本輪讀取repo metadata確認：has_pages=false、has_issues=false，Release清單為空。About的homepage欄位仍繼承原作者網站；檔案提交不會修改GitHub儲存庫設定，目前可用連接器沒有修改此欄位的動作，因此**尚未變更homepage**。適合的新值是本repo的閱讀說明或儲存庫首頁，不能填未部署的Pages位址。

不能修改原作者網站、GitHub或下載服務的HTTP重定向；本輪是修改本repo引用位置及自有頁面的舊書籤相容，不宣稱已把上游網域改成301／302。

## 驗證

日常CI透過ci_language_policy呼叫link_policy.py，檢查上游連結例外、repo檔案／目錄是否存在、Markdown錨點、舊分支及未發布資產引用。新回歸測試會故意放入錯誤目的地，確認檢查能攔截，並保留原有來源、字形、JSON、圖片、建置與閱讀功能測試。

單次外部HTTP失敗不混入本地導覽檢查；本輪不宣稱全書研究來源已全部有效或在地化完成。實際遠端執行與合併結果以本輪PR、main檢查及提交紀錄為準。

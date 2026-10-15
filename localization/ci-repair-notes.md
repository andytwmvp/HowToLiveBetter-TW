# PR 失敗通知：原因、修復與驗證

本次診斷以 PR #2 修復前提交 `7a50ee003c51467629f2362906390a4379892d8c`、失敗執行 `38713229311` 為準。日誌顯示來源保留檢查通過，隨後因文字正規化比較失敗而停止；Node.js 淘汰提示不是該次失敗原因。

## 已修復的問題

字形檢查原本把 OpenCC 建議寫法直接視為唯一合法繁體寫法，誤報「雇主」「公布」「占有」等臺灣用字。新政策接受列明的合法異體，同時仍阻擋實際簡體字。新草稿的漏轉文字已修正，來源網址與數字保持不變。

第 11 章草稿 JSON 導言含未跳脫換行，已修正並新增全數 JSON 解析、重複鍵及條目欄位檢查。未完成來源登錄另列在 coverage.json，不能以結構測試通過推定來源已查核。

原工作分支的每次提交會同時觸發 push 與 pull_request。現在工作分支只經 PR 事件驗證，main 保留提交後驗證；手動 workflow_dispatch 仍可用。沒有關閉使用者電子郵件通知，也沒有修改 Gmail。

圖片稽核原本會用實際檔案重新產生盤點，可能覆寫原先的雜湊及審閱狀態。現在非重製模式只比較圖片、徽章及 SVG 與盤點是否一致；不修改盤點。已加入錯誤雜湊必須被拒絕的測試。

## 正式檢查入口

Python 須安裝 `OpenCC==1.1.9`；完整瀏覽器測試另需 `playwright==1.55.0` 及其 Chromium。專案使用 Node.js 22。

```sh
python3 tools/tw/traditionalize.py --check
python3 tools/tw/ci_language_policy.py --check --audit
python3 -m unittest discover -s tools/tw/tests -v
node tools/check-refs.mjs --check
node tools/check-split.mjs
node tools/sync-stats.mjs --check
python3 tools/tw/image_copy.py --check
node tools/offline/build.mjs dist/tw-source-preview.html
npm ci --prefix tools/epub
node tools/epub/build.mjs
node tools/anki/build.mjs
python3 tools/tw/assets_and_browser.py --browser
```

`text_integrity.py` 是既有遷移輔助模組；日常字形驗證改用 `ci_language_policy.py`，不可再以舊版全檔正規化比較作為唯一合併依據。`ci_language_policy.py --repair` 僅供此次隔離分支使用；不得在日常 CI 內自動修正內容後直接宣告通過。

八項回歸測試涵蓋合法臺灣用字、真正簡體字、網址保留、無效 JSON、重複 JSON 鍵、圖片稽核唯讀性、錯誤圖片雜湊，以及草稿數不得當成出版完成。

## 驗證與完成範圍

隔離分支完整驗證已成功：[執行 38718545154](https://github.com/andytwmvp/HowToLiveBetter-TW/actions/runs/38718545154)。原 PR 整批更新後，仍須再次確認其最新檢查；舊失敗紀錄保留作追溯，不刪除、不改寫成成功。

工程測試通過不代表全書在地化完成。本輪沒有新增實質章節內容，也沒有完成全部來源核對、正式閱讀整合、PDF 排版驗收或部署。後續交付以 PROJECT_STATE.md 與草稿清單為準。

測試產生的 dist 與本次專用暫存資料不再需要時即清除，保留原始附件，不提交字型、環境依賴或私人資料。

# 臺灣 repo 閱讀、建置與連結入口

<a id="reading"></a>
## 閱讀

目前以本 repo 檔案為準，沒有啟用 GitHub Pages，也沒有正式 Release。GitHub 點開 `.html` 會看到原始碼，不是已部署的閱讀網站；不要用原作者網站或猜測的 Pages 網址替代。

```sh
git clone https://github.com/andytwmvp/HowToLiveBetter-TW.git
cd HowToLiveBetter-TW
python3 -m http.server 8000 --bind 127.0.0.1
```

在瀏覽器開啟 `http://127.0.0.1:8000/` 閱讀臺灣導航，`http://127.0.0.1:8000/selfcheck.html` 使用自查。完成後按 Ctrl+C 停止伺服器。預設資料來自 [runtime.json](localization/tw-edition/runtime.json)，只包含已核對導航，不代表765條全書已完成。

<a id="exports"></a>
## 本地匯出

在儲存庫根目錄使用 Python 3 與 Node.js 22 執行：

```sh
node tools/offline/build.mjs
node tools/epub/build.mjs
node tools/anki/build.mjs
```

輸出分別是 `dist/HowToLiveBetter-TW.html`、`dist/HowToLiveBetter-TW.epub`、`dist/HowToLiveBetter-TW.apkg`，僅收錄目前已核對的導航。沒有公開下載資產時，連結導向這份建置說明，不建立不存在的固定 Release 下載網址。

HTML 可離線使用；EPUB 與 Anki 的工程驗證不等於所有閱讀器或用戶端匯入驗收。正式臺灣全書 PDF 尚未完成，不能把原作 PDF 改名後當成臺灣版。

<a id="source-preview"></a>
## 原作繁體來源預覽

完整34章、765條原作繁體稿保存在 [book/](book/) 與 [docs/](docs/)。在本機開啟 `http://127.0.0.1:8000/source.html` 才是含原作搜尋與分級的來源閱讀器；不是臺灣制度建議。

原作工程預覽需要明確指定，不能和臺灣導航產物混用：

```sh
npm ci --prefix tools/epub
node tools/offline/build.mjs --source-preview dist/HowToLiveBetter-source-preview.html
node tools/epub/build.mjs --source-preview dist/HowToLiveBetter-source-preview.epub
node tools/anki/build.mjs --source-preview dist/HowToLiveBetter-source-preview.apkg
```

原作 PDF 工具是 `tools/pdf/build.mjs`，另需該工具記載的 Pandoc 與 Typst 依賴；它仍是原作來源預覽，不是臺灣全書。手動原作工作流程也不發布 Release 或部署網站。

<a id="contributing"></a>
## 回報、取材與署名

[問題回報](SUPPORT.md)、[Skill 共用規則](skills/life-decision-guide/SKILL.md)、[協作規則](AGENTS.md)、[原作署名與授權](ATTRIBUTION.md)與[連結處理紀錄](localization/link-audit.md)都在本 repo。資料未核對時不回退到上游，原作歷史引文亦不任意改成另一個 repo 的 issue。

本次不部署網站、不發布電子書；不再需要的 `dist/`、`/mnt/data` 與 `/tmp` 測試中間檔須清除，保留使用者原始附件。字型、依賴安裝目錄及私人資料不提交。

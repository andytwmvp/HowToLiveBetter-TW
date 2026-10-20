> **2026-10-20五篇安全再審：** 動物暴露、蜱蟲、野外飲水、性侵後照護及斷肢已逐主張再核對；累計41篇AI來源實質再審，專業審閱仍待取得。[本批證據](localization/bites-ticks-water-assault-amputation-20261020.json)。

> **2026-10-20安全再審：** 地震、雷擊、高山症與穿刺異物已逐主張再核對；累計36篇AI來源實質再審，專業審閱仍待取得。[本批證據](localization/disaster-altitude-trauma-20261020.json)。

# 臺灣 repo 閱讀、建置與連結入口

<a id="reading"></a>
## 閱讀

目前以本 repo 檔案為準，沒有啟用 GitHub Pages，也沒有正式 Release。GitHub 點開 `.html` 會看到原始碼，不是已部署的閱讀網站；不要用原作者網站或猜測的 Pages 網址替代。

```sh
git clone https://github.com/andytwmvp/HowToLiveBetter-TW.git
cd HowToLiveBetter-TW
python3 -m http.server 8000 --bind 127.0.0.1
```

在瀏覽器開啟 `http://127.0.0.1:8000/` 閱讀臺灣導航，`http://127.0.0.1:8000/selfcheck.html` 使用自查。完成後按 Ctrl+C 停止伺服器。預設資料只讀 [runtime.json](localization/tw-edition/runtime.json)。截至 2026-10-19，已完成臺灣核心278／765條與11則補充指引與導航，共289項；未來增修請以 [coverage.json](localization/tw-edition/coverage.json) 和 runtime 實際數字為準，不依歷史文字凍結完成數。原作繁體來源稿與未審閱草稿不能充當臺灣現行制度建議。

[第14章12條正文](locales/zh-TW/book/ch14/README.md) · [第15章18條正文](locales/zh-TW/book/ch15/README.md) · [第19章24條正文](locales/zh-TW/book/ch19/README.md) · [第21章13條正文](locales/zh-TW/book/ch21/README.md) · [第23章25條正文](locales/zh-TW/book/ch23/README.md) · [第25章12條正文](locales/zh-TW/book/ch25/README.md) · [第26章13條正文](locales/zh-TW/book/ch26/README.md) · [第7章23條正文](locales/zh-TW/book/ch07/README.md)。這是AI輔助來源核對與編修，不是獨立法律或資安專業簽證。

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

本fork來源Anki及EPUB現在使用獨立識別碼。第一次匯入此版Anki可能新增獨立來源牌組，不會自動遷移、合併或刪除既有原作／舊版預覽的學習紀錄。請先備份，再確認匯入選項；這不是所有版本皆相容的保證。[匯出識別、測試與限制](localization/export-integrity.md)記錄完整處理方式。

原作 PDF 工具是 `tools/pdf/build.mjs`，另需該工具記載的 Pandoc 與 Typst 依賴；它仍是原作來源預覽，不是臺灣全書。手動原作工作流程也不發布 Release 或部署網站。

<a id="contributing"></a>
## 回報、取材與署名

[臺灣原創、出處及再利用政策](localization/TAIWAN_REUSE_POLICY.md)、[問題回報](SUPPORT.md)、[Skill 共用規則](skills/life-decision-guide/SKILL.md)、[協作規則](AGENTS.md)、[原作署名與授權](ATTRIBUTION.md)與[連結處理紀錄](localization/link-audit.md)都在本 repo。資料未核對時不回退到上游，原作歷史引文亦不任意改成另一個 repo 的 issue。

本次不部署網站、不發布電子書；不再需要的 `dist/`、`/mnt/data` 與 `/tmp` 測試中間檔須清除，保留使用者原始附件。字型、依賴安裝目錄及私人資料不提交。

## 公開資料與爬蟲限制

本 fork 是公開 GitHub 儲存庫，跨地區讀取及依法複製的權利不能只靠 `robots.txt` 停止。詳細授權、臺灣獨立寫作、追溯和未公開資料保護見 [再利用政策](localization/TAIWAN_REUSE_POLICY.md)。目前沒有部署 Pages，來源檔案中的爬蟲要求不代表已經對任何地區、公司或模型提供存取控制，也不會妨礙既有合法離線匯出。

獨立工作安全閱讀：[職業安全與健康](locales/zh-TW/guides/職業安全與健康.md)（TW-NAV-011），與個別機械、局限空間及急救條目分開，仍共用正式runtime。

2026-10-20接續：[PEP、骨折、牙齒與遇獸四篇實質再審](localization/pep-fracture-dental-wildlife-20261020.json)，累計45筆AI來源再核對且專業待審；核心278／765不變，612來源登錄。

2026-10-20接續：[威脅、鬥毆與施救權益三篇實質再審](localization/conflict-rescue-rights-20261020.json)；第13章48篇均有AI來源再核對紀錄且專業待審，核心278／765不變，619來源登錄。

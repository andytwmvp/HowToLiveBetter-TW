# HowToLiveBetter-TW｜閱讀說明

<a id="reading"></a>
## 在電腦上閱讀

這份說明介紹如何在電腦上閱讀台灣生活指南。先安裝 Git 和 Python 3，再下載專案；文章可透過搜尋或[章節目錄](locales/zh-TW/README.md)找到。找不到想看的主題時，可以換個關鍵字或從章節目錄瀏覽；目錄未列出的主題，目前沒有可供閱讀的台灣版指引。

開啟終端機，下載專案並切換到資料夾：

~~~sh
git clone https://github.com/andytwmvp/HowToLiveBetter-TW.git
cd HowToLiveBetter-TW
~~~

Windows 使用者請執行：

~~~sh
py -3 -m http.server 8000 --bind 127.0.0.1
~~~

macOS 或 Linux 使用者請執行：

~~~sh
python3 -m http.server 8000 --bind 127.0.0.1
~~~

閱讀頁開啟後，在瀏覽器前往 http://127.0.0.1:8000/；使用生活自我檢視工具時，前往 http://127.0.0.1:8000/selfcheck.html。使用完畢後，回到終端機按 Ctrl+C 停止本機閱讀頁。

在 GitHub 上直接開啟 HTML 檔會看到程式碼；也可以直接從[章節目錄](locales/zh-TW/README.md)閱讀文章。

<a id="exports"></a>
## 製作離線閱讀檔

要自行製作離線閱讀檔，電腦需要安裝 Python 3 和 Node.js 22。切換到專案資料夾後執行：

~~~sh
node tools/offline/build.mjs
node tools/epub/build.mjs
node tools/anki/build.mjs
~~~

輸出的 HTML、EPUB 和 Anki 牌組會放在 dist 資料夾，可離線使用。HTML 可用瀏覽器開啟，EPUB 可用電子書 App 閱讀；Anki 牌組可匯入 Anki。

<a id="source-preview"></a>
## 查找和對照原作內容

原作對照頁保留原作者的文字和情境，方便查找原文與比對來源。要找台灣生活中的實際做法，請從[文章目錄](locales/zh-TW/README.md)閱讀。

本機閱讀頁開啟時，可在瀏覽器輸入 http://127.0.0.1:8000/source.html 查找原作內容。製作原作預覽檔時，先執行 `npm ci --prefix tools/epub`，再執行：

~~~sh
node tools/offline/build.mjs --source-preview dist/HowToLiveBetter-source-preview.html
node tools/epub/build.mjs --source-preview dist/HowToLiveBetter-source-preview.epub
node tools/anki/build.mjs --source-preview dist/HowToLiveBetter-source-preview.apkg
~~~

原作內容的 Anki 牌組和 EPUB 檔使用另一組識別碼。第一次匯入會新增一組資料，不會自動搬移或合併既有學習紀錄。匯入前請先備份並確認畫面上的選項；不同版本的相容方式可能不同。詳情見[匯出識別與完整性說明](localization/export-integrity.md)。

要製作原作 PDF，請先安裝 Pandoc 3.1 以上版本和 Typst 0.13 以上版本，再於專案資料夾執行 `node tools/pdf/build.mjs`。PDF 會輸出到 `dist/HowToLiveBetter.pdf`，供查閱原作內容；要找台灣生活指引，請從[文章目錄](locales/zh-TW/README.md)進入。

<a id="contributing"></a>
## 回報問題與授權

遇到文章、連結或閱讀功能問題時，請依[問題回報方式](SUPPORT.md)提供必要資訊。請勿在公開回報中貼上病歷、帳號密碼、驗證碼或其他個人資料。

原作署名、授權與修改說明見 [ATTRIBUTION.md](ATTRIBUTION.md)；台灣指引的來源和再利用方式見[台灣內容治理政策](localization/TAIWAN_REUSE_POLICY.md)。

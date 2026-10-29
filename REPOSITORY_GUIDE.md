# HowToLiveBetter-TW｜閱讀說明

<a id="reading"></a>
## 在電腦上閱讀

先把專案下載到電腦，並確認已安裝 Git 和 Python 3。閱讀頁、生活自我檢視和離線檔共用同一份台灣版內容，目前只顯示已收錄的文章。找不到主題時，可以換個關鍵字，或從[章節目錄](locales/zh-TW/README.md)瀏覽。

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

伺服器啟動後，在瀏覽器輸入 http://127.0.0.1:8000/ 閱讀；要使用生活自我檢視，請開啟 http://127.0.0.1:8000/selfcheck.html。讀完後回到終端機按 Ctrl+C 停止伺服器。

在 GitHub 上直接開啟 HTML 檔只會看到程式碼。各章文章也可以從[章節目錄](locales/zh-TW/README.md)閱讀。

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

原作對照頁保留原作者的文字和情境，供查找來源與比對主題。原作中的制度、法律、費用和服務方式不一定適用台灣；閱讀台灣生活指南，請從[文章目錄](locales/zh-TW/README.md)進入。

本機閱讀頁開啟時，可在瀏覽器輸入 http://127.0.0.1:8000/source.html 查找原作內容。製作原作預覽檔時，先執行 `npm ci --prefix tools/epub`，再執行：

~~~sh
node tools/offline/build.mjs --source-preview dist/HowToLiveBetter-source-preview.html
node tools/epub/build.mjs --source-preview dist/HowToLiveBetter-source-preview.epub
node tools/anki/build.mjs --source-preview dist/HowToLiveBetter-source-preview.apkg
~~~

原作內容的 Anki 牌組和 EPUB 檔使用另一組識別碼。第一次匯入會新增一組資料，不會自動搬移或合併既有學習紀錄。匯入前請先備份並確認畫面上的選項；不同版本的相容方式可能不同。詳情見[匯出識別與完整性說明](localization/export-integrity.md)。

要製作原作內容的 PDF 預覽，請先安裝 Pandoc 3.1 以上版本和 Typst 0.13 以上版本，再於專案資料夾執行 `node tools/pdf/build.mjs`。PDF 會輸出到 `dist/HowToLiveBetter.pdf`，保留原作內容與用語，不是台灣版生活指南。

<a id="contributing"></a>
## 回報問題與授權

遇到文章、連結或閱讀功能問題時，請依[問題回報方式](SUPPORT.md)提供必要資訊。請勿在公開回報中貼上病歷、帳號密碼、驗證碼、憑證或其他個人資料。

原作署名、授權與修改說明見 [ATTRIBUTION.md](ATTRIBUTION.md)；台灣版內容的來源和再利用方式見[台灣內容治理政策](localization/TAIWAN_REUSE_POLICY.md)。開始編修前，請先閱讀 [AGENTS.md](AGENTS.md) 的協作與查核規範。

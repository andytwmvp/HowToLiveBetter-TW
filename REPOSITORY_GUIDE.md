# 臺灣生活指南｜閱讀說明

<a id="reading"></a>
## 在電腦上閱讀

下載專案後，可以用瀏覽器開啟閱讀頁面，也可以製作離線檔。閱讀頁面、生活自我檢視和離線檔使用同一份臺灣版內容。閱讀器只顯示目前收錄的指引；若找不到想看的主題，可以換個關鍵字，或從[章節目錄](locales/zh-TW/README.md)找找看。有些主題目前還沒有可用的臺灣版指引。

要在自己的電腦上開啟閱讀頁面，先下載專案，再啟動本機網站：

~~~sh
git clone https://github.com/andytwmvp/HowToLiveBetter-TW.git
cd HowToLiveBetter-TW
python3 -m http.server 8000 --bind 127.0.0.1
~~~

接著在瀏覽器開啟 http://127.0.0.1:8000/ 閱讀；要使用生活自我檢視，請開啟 http://127.0.0.1:8000/selfcheck.html。看完後回到命令列按 Ctrl+C 停止本機網站。

在 GitHub 上直接點開 HTML 檔只會看到程式碼。各章文章請從[章節目錄](locales/zh-TW/README.md)進入。

<a id="exports"></a>
## 製作離線閱讀檔

電腦需安裝 Python 3 和 Node.js 22；在專案資料夾中執行：

~~~sh
node tools/offline/build.mjs
node tools/epub/build.mjs
node tools/anki/build.mjs
~~~

完成後，HTML、EPUB 和 Anki 牌組檔會放在 dist 資料夾，可供離線閱讀。HTML 可用瀏覽器開啟，EPUB 可用電子書閱讀器開啟；Anki 牌組檔可匯入 Anki App。

<a id="source-preview"></a>
## 對照原作內容

原作內容對照頁保留原作者的文字、情境與用語，方便查找及比對來源；頁面內容不代表臺灣現行制度或生活建議。閱讀臺灣生活指南，請從[章節目錄](locales/zh-TW/README.md)進入。

在本機開啟 http://127.0.0.1:8000/source.html，可查找原作內容。建立原作預覽檔時，請加上 `--source-preview`：

~~~sh
npm ci --prefix tools/epub
node tools/offline/build.mjs --source-preview dist/HowToLiveBetter-source-preview.html
node tools/epub/build.mjs --source-preview dist/HowToLiveBetter-source-preview.epub
node tools/anki/build.mjs --source-preview dist/HowToLiveBetter-source-preview.apkg
~~~

原作版 Anki 和 EPUB 使用另一組識別碼。第一次匯入會新增一組資料，不會自動搬移或合併既有學習紀錄。匯入前請先備份並確認畫面上的選項；不同版本的相容情況可能不同。詳情見[匯出識別與完整性說明](localization/export-integrity.md)。

要製作原作內容的 PDF 預覽，請先安裝 Pandoc 3.1 以上版本和 Typst 0.13 以上版本，再於專案資料夾執行 `node tools/pdf/build.mjs`。檔案會輸出到 `dist/HowToLiveBetter.pdf`。這份 PDF 保留原作內容與用語，不是臺灣版生活指南。

<a id="contributing"></a>
## 回報問題與授權

若發現文章、連結或閱讀功能有問題，請依[問題回報方式](SUPPORT.md)提供必要資訊。請勿在公開討論區貼上病歷、帳號密碼、驗證碼、憑證或其他個人資料。

原作署名、授權與修改說明見 [ATTRIBUTION.md](ATTRIBUTION.md)；臺灣版內容的來源和再利用方式見[臺灣內容治理政策](localization/TAIWAN_REUSE_POLICY.md)。編修前請閱讀 [AGENTS.md](AGENTS.md) 的協作與查核規範。

# 臺灣版閱讀與建置說明

<a id="reading"></a>
## 閱讀臺灣版

臺灣版網站、自我檢視與離線閱讀檔共用同一套完成來源核對的內容。尚無臺灣版指引的主題會直接顯示說明，不會改用原作內容或未核對的資料。

將專案下載到本機後，在專案資料夾執行：

~~~sh
git clone https://github.com/andytwmvp/HowToLiveBetter-TW.git
cd HowToLiveBetter-TW
python3 -m http.server 8000 --bind 127.0.0.1
~~~

在瀏覽器開啟 http://127.0.0.1:8000/ 閱讀臺灣版導航，或開啟 http://127.0.0.1:8000/selfcheck.html 使用自我檢視。結束後回到命令列按 Ctrl+C 停止。

GitHub 上直接點選 HTML 檔只會看到原始碼。各章入口請見[臺灣版閱讀說明](locales/zh-TW/README.md)。

<a id="exports"></a>
## 建立離線閱讀檔

在專案資料夾使用 Python 3 與 Node.js 22 執行：

~~~sh
node tools/offline/build.mjs
node tools/epub/build.mjs
node tools/anki/build.mjs
~~~

檔案會輸出到 dist 資料夾，分別是 HTML、EPUB 與 Anki 套件；內容與臺灣版閱讀器相同，可供離線閱讀。HTML 可直接開啟，EPUB 可用電子書閱讀器開啟，Anki 套件則依 Anki App 的匯入步驟加入牌組。

<a id="source-preview"></a>
## 原作來源預覽

這裡提供原作來源預覽，方便查找與比對原文。臺灣版生活指引請從[章節目錄](locales/zh-TW/README.md)閱讀。

在本機開啟 http://127.0.0.1:8000/source.html，可使用原作來源閱讀器。建立原作來源預覽時，請明確指定 --source-preview：

~~~sh
npm ci --prefix tools/epub
node tools/offline/build.mjs --source-preview dist/HowToLiveBetter-source-preview.html
node tools/epub/build.mjs --source-preview dist/HowToLiveBetter-source-preview.epub
node tools/anki/build.mjs --source-preview dist/HowToLiveBetter-source-preview.apkg
~~~

來源版 Anki 和 EPUB 使用獨立識別碼。第一次匯入時，會新增另一組來源資料；舊有學習紀錄不會自動搬移或合併。匯入前請先備份並確認畫面上的選項；不同版本的相容狀況可能不同。詳細說明見[匯出識別與完整性說明](localization/export-integrity.md)。

原作 PDF 建置工具需要 Pandoc 與 Typst，詳見工具目錄中的說明；產出的 PDF 是原作來源預覽。臺灣版內容請從[章節目錄](locales/zh-TW/README.md)閱讀。

<a id="contributing"></a>
## 回報問題與授權

若發現內容、連結或無障礙閱讀問題，請依[問題回報方式](SUPPORT.md)提供可公開分享的資訊。不要在公開討論中貼上病歷、帳號密碼、驗證碼、憑證或其他個人資料。

原作署名、授權與修改說明見 [ATTRIBUTION.md](ATTRIBUTION.md)；臺灣版內容的來源和再利用方式見[臺灣內容治理政策](localization/TAIWAN_REUSE_POLICY.md)。如需編修內容，請先閱讀 [AGENTS.md](AGENTS.md) 的協作與查核規範。

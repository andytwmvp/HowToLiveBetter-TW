# 臺灣生活決策 Skill

這個 Skill 只使用專案內已核對臺灣來源的內容，協助整理生活問題的下一步、適用條件、主要風險和參考資料。遇到緊急狀況時先說明安全處置和求援方式；資料不足就直接指出，不拿原作或尚未審閱的草稿補出結論。

正式閱讀資料以 [runtime.json](../../localization/tw-edition/runtime.json) 為準。各章臺灣版內容可從[章節目錄](../../locales/zh-TW/README.md)閱讀；用途、限制與查核規則詳見 [SKILL.md](SKILL.md)。

## 在專案資料夾執行

~~~sh
python3 tools/tw/edition.py --list
python3 tools/tw/edition.py --id TW-14-003
~~~

執行後會列出目前可讀取的臺灣版條目，或顯示指定條目的正文和來源。使用時也要查看適用條件、來源日期及限制。

[臺灣版閱讀說明](../../locales/zh-TW/README.md) · [原作署名與授權](../../ATTRIBUTION.md)

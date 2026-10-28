# 臺灣生活決策 Skill

這個 Skill 會依據專案中已完成臺灣來源核對的內容，協助整理生活問題的下一步、適用條件、主要風險與資料來源。緊急情況先說明安全處置與求援方式；資料不足時會直接指出缺漏，不以原作或未審閱草稿補出結論。

正式閱讀資料以 [runtime.json](../../localization/tw-edition/runtime.json) 為準。各章臺灣版內容可從[章節目錄](../../locales/zh-TW/README.md)閱讀；用途、限制與查核規則詳見 [SKILL.md](SKILL.md)。

## 在專案資料夾執行

~~~sh
python3 tools/tw/edition.py --list
python3 tools/tw/edition.py --id TW-14-003
~~~

命令會列出目前可讀取的臺灣版條目，或顯示指定條目的正文與來源。執行時請一併查看適用條件、來源日期及限制。

[臺灣版閱讀說明](../../locales/zh-TW/README.md) · [原作署名與授權](../../ATTRIBUTION.md)

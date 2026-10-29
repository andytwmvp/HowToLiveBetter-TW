# 專案接續入口

本檔只保留長期適用的接續方式，不逐批重述研究、正文修改或 PR 進度。正式狀態以 fork 的最新 `main`、GitHub Actions 和下列資料檔為準。

## 正式狀態與查核紀錄

- 核心條目、可閱讀內容和來源待辦：`localization/tw-edition/coverage.json`。
- 原作固定 ID、來源版本和條目狀態：`localization/manifest.json`。
- 正式閱讀內容及其引用來源：`localization/tw-edition/runtime.json`。
- 歷史再審、正文前後 SHA、來源核對、統計判斷和待解限制：`localization/retroactive-review-register-20261019.json` 與 `localization/reviews/`。
- 每次研究的來源擷取方式和完整證據：`localization/` 內相應的結構化 JSON。這些資料供查核，不是讀者指南或批次工作日誌。
- 目前 PR、合併狀態及必要 Actions：在 [HowToLiveBetter-TW GitHub 儲存庫](https://github.com/andytwmvp/HowToLiveBetter-TW) 查看；每批開始與合併前都重新核對，不沿用舊 SHA 或數字。

## 接續方式

1. 先讀 `AGENTS.md`、本檔、manifest、runtime、coverage 和最近的 PR／Actions。
2. 從最新 `main` 核對指定條目、既有稿件、來源及歷史審查狀態，再依台灣實際風險安排工作。
3. 正式正文只用繁體中文和台灣慣用說法；刪除不適合台灣情境的例子，依本地情境重寫。未完成查證的主題不提供原作或未審草稿作為台灣建議。
4. 文章只保留讀者需要的背景、步驟、適用界線、成本風險及來源。PR 摘要、審查批次、修改計數和工作進度不放進正式讀者內容。
5. 逐條更新正文、來源、審閱、manifest、runtime 和 SHA；沒有代表性台灣統計時明說資料不足，不以案件數推算個人機率。
6. 執行工作流程要求的完整驗證，建立以 fork `main` 為 base 的 PR。只有必要檢查通過且無衝突時才合併，並在合併後確認 `main` CI。

AI 輔助查核不等於醫療、法律、統計或其他專業審閱。工程檢查通過不代表全書完成在地化或已達正式出版條件；完整度以最新資料和 `publication_ready` 判斷為準。

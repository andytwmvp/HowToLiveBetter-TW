> **繁體字形轉換稿，非台灣制度定稿。** 本頁保留原作的論述、數字與來源；中國大陸法規、補助、客服電話及醫療制度尚未完成台灣查核，不可直接當作台灣現行依據。來源引文亦經字形轉換，精確原文請查固定版本與所附來源。

# issue #28：八處條目補來源（2026-09-23）

任務來源：GitHub issue #28（dlgrv），提議給 8 處標著「作者經驗」「待核實」「TODO」的條目補原始文獻，每條附了引文和鏈接。issue 裡的引文只當線索，下表每一條都是本輪自己抓原文逐字核的。

## 逐條核對與處理

| 條目 | 來源 | 複核 | 原文要點 | 處理 |
|---|---|---|---|---|
| 第 13 節第 18 條（觸電） | <https://www.cdc.gov/natural-disasters/response/what-to-do-protect-yourself-from-electrical-hazards.html> | 是（curl 403，無頭 Chrome 取得） | First aid 一節：「Look first. Don't touch. The person may still be in contact with the electrical source.」「Turn off the source of electricity if possible. If not, move the source away from you and the affected person using a non-conducting object made of cardboard, plastic or wood.」「If either has stopped or seems dangerously slow or shallow, begin cardiopulmonary resuscitation (CPR) immediately.」 | 採納 |
| 同上 | <https://doi.org/10.7326/0003-4819-145-7-200610030-00011>（Spies & Trohman 2006） | 是（Europe PMC 摘要） | 「patients successfully resuscitated after cardiopulmonary arrest often have a favorable prognosis」 | 採納 |
| 同上 | Moran 1986 JAMA（10.1001/jama.1986.03370160055007） | 否 | Europe PMC 無摘要，內容核不了 | 不採納 |
| 同上 | ERC 2021 特殊情況心臟驟停（10.1016/j.resuscitation.2021.02.011） | 是（摘要） | 摘要列出的特殊原因、場景和人群裡都沒有觸電，issue 說「2021 版無觸電章節」屬實 | 從來源欄刪掉；原來源欄說它「含觸電章節」是錯的 |
| 第 20 節第 9 條（不搖晃嬰兒） | <https://doi.org/10.15585/mmwr.mm6520a1>（MMWR 2016） | 是（摘要） | 「During this period, AHT resulted in nearly 2,250 deaths among U.S. resident children aged <5 years」 | 採納 |
| 同上 | <https://doi.org/10.1007/s00247-018-4149-1>（Choudhary 2018 共識聲明） | 是（摘要） | 「Abusive head trauma (AHT) is the leading cause of fatal head injuries in children younger than 2 years」；病因「multifactorial (shaking, shaking and impact, impact, etc.)」；「subdural hematoma… complex retinal hemorrhages」 | 採納 |
| 同上 | AAP 背書版（10.1542/peds.2018-1504） | 未核 | 和共識聲明是同一內容的背書，不另加 | 不採納 |
| 第 13 節第 27 條（無人區） | <https://www.nps.gov/articles/000/desertdrivingsafety.htm> | 是（curl 直取） | 「Staying with your car is the most important thing you can do in the event of an emergency. While not often, people have died from exposure trying to walk back to the paved roads.」 | 採納，等級不變 |
| 第 4 節第 15 條（刷屏上限） | CNNIC 第 56 次報告 PDF | 是（pdftotext 可逐字抽中文） | 第 821 行「截至 2025 年 6 月，我國網民的人均每週上網時長為 30.6 個小時，較 2024 年 12 月提升 1.9 個小時」；第 94 行「短視頻用戶規模達 10.68 億人，佔網民整體的 95.1%」 | 採納，TODO 移除 |
| 第 5 節第 17 條（指數基金） | SPIVA U.S. Scorecard Year-End 2024 | 是（官網 403 且無頭 Chrome 被拒，按 Wayback 2025-05-12 快照核） | 「65% of all active large-cap U.S. equity funds underperformed the S&P 500, worse than the 60% rate observed in 2023 and slightly above the 64% average annual rate reported over the 24-year history」；「Over the 15-year period ending December 2024, there were no categories in which a majority of active managers outperformed.」 | 採納，TODO 移除。條目缺的是「長期」數字，所以除了 issue 引的單年 65%，另加 24 年均值和 15 年的結論 |
| 同上 | SPIVA Institutional Scorecard Year-End 2024 PDF | 未用 | 機構賬戶和 wrap 賬戶，普通讀者買不到這類產品 | 不採納 |
| 第 14 節第 2 條（郵箱密碼） | <https://www.cisa.gov/secure-our-world/use-strong-passwords> | 是（curl 直取） | 「Create long, random, unique passwords with a password manager」；「At least 16 characters—longer is stronger!」；「Use a different strong password for each account」 | 採納，等級不變 |
| 第 14 節第 3 條（SIM 卡 PIN） | FCC DOC-398483A1（2023-11-15 新聞稿） | 是（pdftotext） | 管的是運營商在轉號、換卡前核驗身份，針對的是「without ever gaining physical control of a consumer's phone」的換卡詐騙 | **不採納**。條目防的是手機丟了、卡被拔下來插進別的手機，這正好是對方拿到了實體卡的情形，兩件事不是一回事 |
| 第 14 節第 4 條（手機丟了） | <https://www.fcc.gov/consumers/guides/protect-your-mobile-device> | 是（curl 403，無頭 Chrome 取得） | 「Even if you think you may have only lost the device, you should remotely lock it to be safe. If the device was stolen, immediately report the theft to the police, including the make and model, serial and IMEI or MEID or ESN number.」「Immediately report the theft or loss to your service provider.」 | 採納；步驟先後順序仍是作者經驗，來源欄寫明 |

## 定級

**只有兩條改了等級：第 13 節第 18 條和第 20 節第 9 條，都是 C 升 B。** 兩條現在都有官方指南或專業共識，另有一篇研究支撐，但都沒有能直接換算成「做了少死多少」的數字，按口徑是 B。

其餘幾條等級不變。官方機構的操作提示（NPS、CISA、FCC）不是研究，按本書慣例仍定 C（第 13 節第 27 條一直就是這個處理）。第 4、5 節兩條只是移除 TODO、補上數字，等級不動。

## 沒照 issue 做的地方

- 翻譯本身不合入本倉庫（CLAUDE.md 規則），這次只處理對中文原文的來源建議。
- issue 提議可以直接開 PR。本輪已經在本地改完，不需要 PR。

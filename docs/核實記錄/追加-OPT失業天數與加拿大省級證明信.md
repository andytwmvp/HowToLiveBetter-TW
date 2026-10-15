> **繁體字形轉換稿，非台灣制度定稿。** 本頁保留原作的論述、數字與來源；中國大陸法規、補助、客服電話及醫療制度尚未完成台灣查核，不可直接當作台灣現行依據。來源引文亦經字形轉換，精確原文請查固定版本與所附來源。

# 追加：第 32 節第 11、12 條，美國 OPT 失業天數上限、加拿大省級證明信

2026-10-14。兩條都追加在第 32 節末尾，沒有插在中間。本節不到 20 條，不需要節首導覽。查重：全書 grep「OPT」「PAL」「省級證明信」「STEM」都沒有命中。

四問：① 去美國、加拿大讀書的讀者會碰上；② OPT 失業天數是會丟身份的硬線，很多人只知道「有 OPT 可以找工作」，不知道沒工作的天數有上限；加拿大 2026 年起碩士博士豁免是新變化，被拒後要重拿證明信也少有人知道；③ 動作是新的（記天數、畢業前遞申請；拿信前問清退學費）；④ 有官方原文。

## 第 11 條：OPT 失業天數

### 1. 8 CFR 214.2(f)(10)(ii)(E)
- URL：<https://www.ecfr.gov/current/title-8/chapter-I/subchapter-B/part-214/section-214.2>；本次用 eCFR 版本接口取 2026-10-09 版全文（`/api/versioner/v1/full/2026-10-09/title-8.xml?part=214&section=214.2`，要帶代理和 `--compressed`）。
- 原文：「(E) Periods of unemployment during post-completion OPT. During post-completion OPT, F-1 status is dependent upon employment. Students may not accrue an aggregate of more than 90 days of unemployment during any post-completion OPT period described in 8 CFR 274a.12(c)(3)(i)(B). Students granted a 24-month OPT extension under paragraph (f)(10)(ii)(C)(2) of this section may not accrue an aggregate of more than 150 days of unemployment during a total OPT period, including any post-completion OPT period described in 8 CFR 274a.12(c)(3)(i)(B) and any subsequent 24-month extension period.」
- 2026-09-01 版和 2026-10-09 版這一段逐字相同，固定入境期限新規沒動它。

### 2. 申請時間：60 天還是 30 天
- 2026-09-14 版 (f)(11)(i)(B)(2)：「the student may properly file his or her Form I-765 or successor form up to 90 days prior to his or her program end date and no later than 60 days after his or her program end date. The student must also file his or her Form I-765 or successor form with USCIS within 30 days of the date the DSO enters the recommendation for OPT into his or her SEVIS record.」
- 2026-09-15 版起同一句變成「no later than 30 days after his or her program end date」。eCFR 版本列表顯示 214.2 在 2026-09-15 有一次實質修改，對應 2026-07-17 公佈、原定 2026-09-15 生效的固定入境期限規則（第 32 節第 2 條）。eCFR 不反映法院暫停，所以網站「current」頁現在顯示 30 天。
- 法院暫停期間按舊規矩，USCIS 頁面仍寫 60 天：<https://www.uscis.gov/working-in-the-united-states/students-and-exchange-visitors/optional-practical-training-opt-for-f-1-students>（2026-10-14 取）——「Initial post-completion OPT … Must apply within 30 days after your DSO enters the recommendation for OPT into your SEVIS record, and May apply up to 90 days before you complete your degree, but no later than 60 days after you complete your degree.」
- 所以條目寫 60 天，備註提示新規會改成 30 天，建議畢業前就遞。

### 3. SEVP 說明：沒登記僱主算失業、可被手動終止
- URL：<https://studyinthestates.dhs.gov/sevis-help-hub/student-records/fm-student-employment/f-1-optional-practical-training-opt>（2026-10-14 帶代理取到）
- 原文：「While students are not required to have an employer when OPT is requested in SEVIS, students authorized for post-completion OPT are expected to be employed. A student on post-completion OPT can be unemployed for a total of 90 days. A student whose record lacks employer information is considered unemployed. SEVP officials can manually terminate a student who accrues 90 total days of unemployment.」

### 4. OPT 收費提議
- Federal Register API 取 2026-20660 號文件摘要：「This rule proposes new fees for Optional Practical Training (OPT) … $70,000 for initial OPT; and $30,000 for any subsequent OPT.」類型 Proposed Rule，2026-10-08 公佈，comments_close_on 2026-11-09。
- URL：<https://www.federalregister.gov/documents/2026/10/08/2026-20660/optional-practical-training-fees>
- 只是提議，條目備註寫明沒有生效。

### 等級與量級
- 證據等級 A：聯邦法規原文加官方說明。
- 收益大、口徑自由：超限的後果是 F-1 身份被終止，和本節第 3、4 條（違反簽證條件、身份斷掉）同一量級，沿用本節標法。

## 第 12 條：加拿大省級證明信（PAL/TAL）

### 1. IRCC，Provincial attestation letter or territorial attestation letter
- URL：<https://www.canada.ca/en/immigration-refugees-citizenship/services/study-canada/study-permit/get-documents/provincial-attestation-letter.html>（curl 超時，無頭 Chrome 帶代理取到；頁面 dcterms.modified 為 2026-09-02）
- 是什麼：「The provincial attestation letter or territorial attestation letter (PAL/TAL) is a letter from the province or territory where you plan to study that confirms there's space for you provided by the designated learning institution (DLI) you plan to attend usually required to apply for a study permit」；「It confirms that you've been assigned one of the available spaces to study in that province or territory.」
- 怎麼拿、何時交：「You should contact your school (DLI) to find out how to apply for a PAL/TAL.」；「You should submit a PAL/TAL with your study permit application, not after」
- 豁免（節選）：「preschool primary school (including kindergarten) secondary school (up to grade 12) degree-granting graduate program at the master's or doctoral level at a public DLI starting January 1, 2026」；「You're an exchange student studying under an exchange arrangement between your home institution and a DLI in Canada, and you don't pay tuition fees to the DLI.」；「You're applying for a study permit extension at the same DLI and level of study as your current study permit.」；「You need to provide proof that you meet one of the above exceptions if you don't provide a PAL/TAL with your study permit application.」
- 魁北克：「If you want to study in Quebec, you need an attestation of issuance of your Quebec Acceptance Certificate (CAQ), which is issued by the Government of Quebec.」
- 有效期：「until December 31, 2026, for the 2026 study permit cap year」；「Your PAL/TAL needs to be valid when you apply for your study permit. It does not need to be valid when you start your studies.」
- 重新拿：「You can't reapply with the same PAL/TAL if your study permit application was approved or refused.」；「As of January 22, 2025, you must get a new PAL/TAL before you submit your study permit application when changing schools.」

### 2. IRCC，Study permit: Get the right documents
- URL：<https://www.canada.ca/en/immigration-refugees-citizenship/services/study-canada/study-permit/get-documents.html>（無頭 Chrome 帶代理取到；dcterms.modified 2026-10-06）
- 原文：「Get a provincial or territorial attestation letter (PAL/TAL) from your school. In most cases, you need to accept your offer and pay your tuition fees, either in part or in full, to get your PAL/TAL.」

### 等級與量級
- 證據等級 A：移民局官網原文。
- 收益中、口徑金錢，憑判斷：沒交證明信或拿舊信再申請，損失的是申請費、時間和可能退不全的學費，後果是錢和時間，不涉及人身自由。官網沒有給出被拒時學費退多少的統一規定，所以條目只讓讀者問學校，沒寫數字。
- 沒寫「沒有證明信會被退件」：這一說法在兩頁原文裡沒有逐字找到。

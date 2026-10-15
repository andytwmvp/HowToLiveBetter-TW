> **繁體字形轉換稿，非台灣制度定稿。** 本頁保留原作的論述、數字與來源；中國大陸法規、補助、客服電話及醫療制度尚未完成台灣查核，不可直接當作台灣現行依據。來源引文亦經字形轉換，精確原文請查固定版本與所附來源。

# 追加：第 6 節第 31 條，別靠 AI 聊天機器人自己判斷病情和法律問題

2026-10-09，issue #103「AI 什麼時候不可信」。讀者想讓書回答三件事：大模型為什麼會產生幻覺，怎麼靠外部來源核對，重大決定前別盲信 AI 的專業回答。四問：普通讀者現在常拿 AI 問病情和法律；AI 回答的語氣很肯定，多數人想不到要核；全書原有的 AI 條目只講中轉站（第 11 節第 19 條、第 14 節第 10 條）、AI 造圖（第 9 節第 1 條）和服務備案（第 11 節第 17 條），沒有「信不信它的回答」這件事；來源是同行評審的隨機試驗和法學期刊。用戶定放第 6 節反面清單。

原理（issue 第 1 點）按全書規矩不展開，只在備註寫一句。

## 1. 普通人用 AI 判斷病情的隨機試驗
- 題錄：Bean AM 等 (2026). Nature Medicine 32(2):609-615. <https://doi.org/10.1038/s41591-025-04074-y>（PMID 41663592，PMC12920132），全文 XML 經 Europe PMC REST 取得。卷期頁碼經 Crossref 核對。
- 摘要原文：「We tested whether LLMs can assist members of the public in identifying underlying conditions and choosing a course of action (disposition) in ten medical scenarios in a controlled study with 1,298 participants. Participants were randomly assigned to receive assistance from an LLM (GPT-4o, Llama 3, Command R+) or a source of their choice (control). Tested alone, LLMs complete the scenarios accurately, correctly identifying conditions in 94.9% of cases and disposition in 56.3% on average. However, participants using the same LLMs identified relevant conditions in fewer than 34.5% of cases and disposition in fewer than 44.2%, both no better than the control group.」
- 正文原文：「Participants in the control group had 1.76 (95% CI = 1.45–2.13) times higher odds of identifying a relevant condition than the aggregate of the participants using LLMs. They were also 1.57 (95% CI = 1.28–1.92) times more likely to identify conditions from the more serious 'red flag' list.」
- 正文原文：「Participants using LLMs did not have statistically significant differences in disposition accuracy from the control group」
- 對照組用什麼：「Post-treatment surveys indicated that most participants used a search engine or went directly to trusted websites, most often the NHS website」
- 失敗原因：「with both users providing LLMs with incomplete information and LLMs suggesting correct answers but not effectively conveying this information to the users」；「Despite these correct suggestions appearing in the conversations, users did not consistently include them in the final responses」
- 每人兩個病例：「We assigned each participant two scenarios to complete consecutively.」樣本按英國人口結構分層：「stratified to reflect the demographics of the UK」。
- 「AI 單獨考試的成績預測不了普通人用它的效果」：「Standard benchmarks for medical knowledge and simulated patient interactions do not predict the failures we find with human participants.」

## 2. 通用大模型答法律問題
- 題錄：Dahl M, Magesh V, Suzgun M, Ho DE (2024). Journal of Legal Analysis 16(1):64-93. <https://doi.org/10.1093/jla/laae003>，摘要經 Crossref 取得。
- 摘要原文：「Using OpenAI's ChatGPT 4 and other public models, we show that LLMs hallucinate at least 58% of the time, struggle to predict their own hallucinations, and often uncritically accept users' incorrect legal assumptions.」幻覺的定義：「textual output that is not consistent with legal facts」。
- 同一篇的 arXiv 版（<https://arxiv.org/abs/2401.01301>，經 arXiv API 取得）摘要寫明瞭題目範圍和各模型的數：「legal hallucinations are alarmingly prevalent, occurring between 58% of the time with ChatGPT 4 and 88% with Llama 2, when these models are asked specific, verifiable questions about random federal court cases」。條目「問美國聯邦法院的判例」「Llama 2 高到 88%」按這句寫。作者單位沒逐一核，條目只寫「一個美國研究團隊」。

## 3. 專業法律 AI 工具
- 題錄：Magesh V 等 (2025). Journal of Empirical Legal Studies 22(2):216-242. <https://doi.org/10.1111/jels.12413>，摘要經 Crossref 取得。
- 摘要原文：「the AI research tools made by LexisNexis (Lexis+ AI) and Thomson Reuters (Westlaw AI-Assisted Research and Ask Practical Law AI) each hallucinate between 17% and 33% of the time」；「certain legal research providers have touted methods such as retrieval-augmented generation (RAG) as "eliminating" or "avoid[ing]" hallucinations」

## 4. 幻覺的成因（只進備註）
- 題錄：Kalai AT, Nachum O, Vempala SS, Zhang E (2025). Why Language Models Hallucinate. arXiv:2509.04664，經 arXiv API 取得。issue 附的 OpenAI 中文頁面對應這篇。未經同行評審，所以只在備註裡寫一句，不進收益欄。
- 摘要原文：「We argue that language models hallucinate because the training and evaluation procedures reward guessing over acknowledging uncertainty」；「language models are optimized to be good test-takers, and guessing when uncertain improves test performance」

## 5. 反方
- 題錄：Ayers JW 等 (2023). JAMA Internal Medicine 183(6):589. <https://doi.org/10.1001/jamainternmed.2023.1838>，摘要經 Europe PMC 取得。
- 摘要原文：「a public and nonidentifiable database of questions from a public social media forum (Reddit's r/AskDocs) was used to randomly draw 195 exchanges」；「evaluators preferred chatbot responses to physician responses in 78.6% (95% CI, 75.0%-81.8%) of the 585 evaluations」
- 它評的是回答的質量和同理心，沒看提問的人最後判斷對沒有，所以和 Bean 2026 不矛盾。備註寫明瞭這一點。

## 沒收
- Mata v. Avianca（美國律師用 ChatGPT 編判例被罰）：CourtListener 搜索 API 沒檢索到這份意見書，原文書沒取到，沒寫。
- 國內普通人用 AI 問病情或法律出錯的官方統計和判決，這次沒有去查。
- 收益定小：Bean 2026 的終點是「認沒認出相關疾病」，屬於中間指標，沒有死亡或住院的數字。

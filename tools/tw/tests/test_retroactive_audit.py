"""回溯稽核：既有正式正文、導航和原作 765 條均須動態覆蓋。"""
import json
import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import retroactive_audit as audit


class RetroactiveAuditTests(unittest.TestCase):
    def test_reader_copy_cleanup_removes_process_footer_but_keeps_source_and_limits(self):
        normalize = getattr(audit, "normalize_reader_copy", None)
        self.assertTrue(callable(normalize), "稽核器需提供可重現的讀者正文整理規則")
        body = (
            "# 指引標題\n\n"
            "目前沒有能代表全臺個人風險的統計資料。緊急情況請先撥119。\n\n"
            "## 官方來源及改寫說明\n\n"
            "- [主管機關：現行規定](https://example.gov.tw/rule)\n\n"
            "原作固定ID：TW-01-001。AI輔助來源核對：2026-10-28；"
            "預定複查：2027-01-31。未取得獨立專業審閱。\n"
        )
        cleaned, removed = normalize(body)
        self.assertEqual(
            cleaned,
            "# 指引標題\n\n"
            "目前沒有能代表全臺個人風險的統計資料。緊急情況請先撥119。\n\n"
            "## 參考資料\n\n"
            "- [主管機關：現行規定](https://example.gov.tw/rule)\n",
        )
        self.assertEqual(len(removed), 1)
        self.assertIn("AI輔助來源核對", removed[0])

    def test_reader_copy_cleanup_keeps_useful_current_law_limits_from_process_footer(self):
        body = (
            "# 指引標題\n\n本文整理一般辦理步驟。\n\n"
            "資料查閱日期：2026-10-28。AI輔助來源核對，尚未取得獨立法律專業審閱。"
            "法規資料庫整編截至2026-10-16；之後的修正、個案資格及申辦期限，請向主管機關確認。\n"
        )
        cleaned, removed = audit.normalize_reader_copy(body)
        self.assertEqual(
            cleaned,
            "# 指引標題\n\n本文整理一般辦理步驟。\n\n"
            "法規可能更新，個案資格及申辦期限請向主管機關確認。\n",
        )
        self.assertEqual(len(removed), 1)
        self.assertIn("AI輔助來源核對", removed[0])

    def test_reader_copy_cleanup_removes_review_status_inside_article_without_losing_facts(self):
        body = (
            "# 指引標題\n\n"
            "目前沒有同口徑的個人暴露分母可用來估算發生率。"
            "雇主補償、保險給付及民事賠償是不同請求，是否適用由個案依法判斷，"
            "本輪AI來源核對不是醫療或法律專業簽證。\n\n"
            "## 參考資料\n\n請依所在地主管機關資訊確認實際辦理方式。\n"
        )
        cleaned, _ = audit.normalize_reader_copy(body)
        self.assertEqual(
            cleaned,
            "# 指引標題\n\n"
            "目前沒有同口徑的個人暴露分母可用來估算發生率。"
            "雇主補償、保險給付及民事賠償是不同請求，是否適用由個案依法判斷。\n\n"
            "## 參考資料\n\n請依所在地主管機關資訊確認實際辦理方式。\n",
        )

    def test_reader_copy_cleanup_keeps_a_source_link_embedded_in_an_editor_note(self):
        url = "https://example.gov.tw/statistics"
        body = (
            "# 指引標題\n\n"
            f"本輪以[主管機關統計表]({url})核對資料。\n\n"
            "緊急情況請先撥119。\n"
        )
        cleaned, _ = audit.normalize_reader_copy(body)
        self.assertNotIn("本輪", cleaned)
        self.assertIn(f"[主管機關統計表]({url})", cleaned)
        self.assertIn("119", cleaned)

    def test_reader_copy_cleanup_removes_cross_jurisdiction_editorial_comparison(self):
        body = (
            "若可能暴露尚在72小時內，先儘速就醫評估PEP。"
            "臺灣不是照搬中國疾控中心服務。"
            "一般想確認感染狀況者，可預約疾管署列出的匿名篩檢點。\n"
        )
        cleaned, _ = audit.normalize_reader_copy(body)
        self.assertNotIn("中國", cleaned)
        self.assertIn("先儘速就醫評估PEP", cleaned)
        self.assertIn("疾管署列出的匿名篩檢點", cleaned)

    def test_reader_item_cleanup_covers_every_exported_field_and_keeps_taiwan_guidance(self):
        normalize = getattr(audit, "normalize_reader_item", None)
        self.assertTrue(callable(normalize), "稽核器需整理網站與離線匯出會顯示的所有文章欄位")
        item = {
            "id": "TW-17-007",
            "title": "長期失能先撥1966申請照管評估，別找中國長護險",
            "body": (
                "# 長期失能先撥1966申請照管評估，別找中國長護險\n\n"
                "照顧需求先撥1966，急症先撥119。\n\n"
                "目前沒有同定義的全臺失能發生率資料，不推估個人風險。\n\n"
                "臺灣不是中國醫保制度；AI輔助再審尚待專業簽證。\n"
            ),
            "limits": "聘有外籍家庭看護者仍可能符合部分長照服務；AI輔助審閱尚未取得專業簽證。",
            "question": "我已理解「長期失能先撥1966申請照管評估，別找中國長護險」的做法嗎？",
            "source_ids": ["ch17_ltc"],
            "target_path": "locales/zh-TW/book/ch17/TW-17-007.md",
        }
        cleaned, removed = normalize(item)
        self.assertEqual(cleaned["title"], "長期失能照護服務：先撥1966申請評估")
        self.assertTrue(cleaned["body"].startswith("# 長期失能照護服務：先撥1966申請評估\n"))
        self.assertIn("急症先撥119", cleaned["body"])
        self.assertIn("目前沒有同定義的全臺失能發生率資料", cleaned["body"])
        self.assertNotIn("中國", cleaned["body"] + cleaned["title"] + cleaned["limits"] + cleaned["question"])
        self.assertNotIn("AI輔助", cleaned["body"] + cleaned["limits"])
        self.assertIn("部分長照服務", cleaned["limits"])
        self.assertIn("申請評估", cleaned["question"])
        self.assertEqual(cleaned["source_ids"], item["source_ids"])
        self.assertTrue(removed)

    def test_reader_item_cleanup_record_hashes_every_reader_field(self):
        normalize = getattr(audit, "normalize_reader_item", None)
        validate = getattr(audit, "documented_reader_item_cleanup", None)
        self.assertTrue(callable(normalize))
        old = {
            "id": "TW-17-007",
            "title": "長期失能先撥1966申請照管評估，別找中國長護險",
            "body": "# 長期失能先撥1966申請照管評估，別找中國長護險\n\n可撥1966申請評估。\n",
            "limits": "AI輔助審閱，仍待專家簽證。",
            "question": "我已理解「長期失能先撥1966申請照管評估，別找中國長護險」的臺灣適用對象、費用、來源與例外嗎？",
            "source_ids": ["ch17_ltc"],
        }
        new, _ = normalize(old)
        record = audit.make_reader_copy_cleanup_record(old, new, "1011138aaf550b9376f3cb11ec2c3fc657daf850")
        self.assertTrue(validate(old, new, record))
        altered = dict(new, limits="changed")
        self.assertFalse(validate(old, altered, record))

    def test_reader_copy_cleanup_record_allows_only_the_declared_transform(self):
        validate = getattr(audit, "documented_reader_cleanup", None)
        self.assertTrue(callable(validate), "稽核器需驗證非實質性正文整理紀錄")
        before_body = (
            "# 指引標題\n\n可執行的安全步驟。\n\n"
            "## 官方來源及改寫說明\n\n"
            "- [主管機關](https://example.gov.tw/rule)\n\n"
            "原作固定ID：TW-01-001。AI輔助來源核對：2026-10-28。\n"
        )
        after_body, _ = audit.normalize_reader_copy(before_body)
        old = {"id": "TW-01-001", "title": "指引標題", "body": before_body,
               "reviewed_at": "2026-10-28", "source_ids": ["source"]}
        new = dict(old, body=after_body)
        import hashlib
        record = {
            "id": old["id"],
            "before_sha256": hashlib.sha256(before_body.encode()).hexdigest(),
            "after_sha256": hashlib.sha256(after_body.encode()).hexdigest(),
            "transform": "reader_copy_cleanup_v1",
        }
        self.assertTrue(validate(old, new, record))
        altered = dict(new, body=after_body.replace("可執行的安全步驟", "錯誤的安全步驟"))
        self.assertFalse(validate(old, altered, record))
        altered_title = dict(new, title="其他標題")
        self.assertFalse(validate(old, altered_title, record))

    def test_reader_guides_replace_internal_item_ids_with_descriptive_links(self):
        root = audit.ROOT
        emergency = (root / "locales/zh-TW/guides/全民安全與防災準備.md").read_text(encoding="utf-8")
        workplace = (root / "locales/zh-TW/guides/職業安全與健康.md").read_text(encoding="utf-8")
        emergency_clean, _ = audit.normalize_reader_copy(emergency)
        workplace_clean, _ = audit.normalize_reader_copy(workplace)
        self.assertNotIn("對照本專案的 TW-13-030", emergency_clean)
        self.assertIn("[地震時先保護頭頸", emergency_clean)
        self.assertNotIn("依TW-01-046", workplace_clean)
        self.assertIn("[局限空間安全指引]", workplace_clean)
        self.assertNotIn("本文查閱日為", emergency_clean)
        self.assertNotIn("本輪專業審查", workplace_clean)

    def test_chapter_menus_use_reader_facing_article_titles_without_internal_ids(self):
        root = audit.ROOT / "locales/zh-TW/book"
        for path in sorted(root.glob("ch*/README.md")):
            with self.subTest(path=path.name):
                source = path.read_text(encoding="utf-8")
                self.assertNotRegex(source, r"\[(?:TW-\d{2}-\d{3}|TW-NAV-\d{3})\s")

    def test_reader_runtime_has_no_internal_review_workflow_copy(self):
        runtime = json.loads((audit.ROOT / "localization/tw-edition/runtime.json").read_text(encoding="utf-8"))
        workflow = re.compile(
            r"原作固定\s*ID|原作條目ID|本文條目ID|臺?灣獨立改寫|"
            r"本(?:次|輪|批)(?:AI輔助|實質再審|直接讀取|逐頁核對|讀取|實讀|查核|查閱|檢索|未通讀|未讀|未取得|再核對|沒有核實)|"
            r"本輪|本批|臺?灣事件頻率再審|本次補入|本次補充實讀|本次以研究摘要|"
            r"本(?:次|輪)(?:只讀|目視|讀取並目視|沒有實測|只見入口)|"
            r"本文以臺灣政府及公立醫院公開HTML資料獨立編修|依臺灣警政求援流程重寫|"
            r"改(?:為|成)臺灣|(?:加入|補入|新增)臺灣|改採院前症狀|此為公開臺灣.*編輯核對|"
            r"本篇不是.{0,35}(?:專業|正式認證|驗收)|本文不採用.{0,60}(?:比率|比例|風險)|"
            r"查閱日期：20\d{2}|實質再審（20\d{2}|資料查閱日期：|"
            r"AI輔助(?:來源)?(?:核對|再審)|資料庫整編(?:截止|至)|"
            r"預定複查日|下次複查|非獨立(?:法律|醫療|專業)審閱"
        )
        for item in runtime["items"]:
            cleaned, _ = audit.normalize_reader_item(item)
            self.assertEqual(cleaned, item, f"{item['id']} 尚未整理成實際閱讀文字")
            if item.get("target_path"):
                target = audit.ROOT / item["target_path"]
                self.assertEqual(target.read_text(encoding="utf-8"), item["body"])
            for field in ("title", "body", "limits", "question"):
                with self.subTest(item=item["id"], field=field):
                    self.assertFalse(workflow.search(cleaned.get(field, "")))

    def test_reader_runtime_uses_taiwan_terms_and_descriptive_cross_references(self):
        runtime = json.loads((audit.ROOT / "localization/tw-edition/runtime.json").read_text(encoding="utf-8"))
        internal_id = re.compile(r"\bTW-(?:\d{2}-\d{3}|NAV-\d{3})\b")
        for item in runtime["items"]:
            for field in ("title", "body", "limits", "question"):
                value = item.get(field, "")
                with self.subTest(item=item["id"], field=field):
                    self.assertNotIn("用戶", value)
                    if field == "limits":
                        self.assertTrue(value.strip(), "每篇都要留下讀者看得懂的適用限制")
                    visible = re.sub(r"<!--.*?-->", "", value, flags=re.DOTALL)
                    visible = re.sub(r"\[[^\]]+\]\([^)]+\)", "", visible)
                    self.assertFalse(internal_id.search(visible))

        items = {item["id"]: item for item in runtime["items"]}
        item_text = "\n".join(item["body"] for item in runtime["items"])
        self.assertIn("[大量出血處理](TW-13-012.md)", item_text)
        self.assertIn("[疑似HIV暴露後儘早評估PEP](TW-13-038.md)", item_text)
        self.assertIn("公開摘要未列完整方法與補充資料", items["TW-23-002"]["limits"])
        self.assertIn("法律責任依個案事證判斷", items["TW-15-001"]["limits"])
        self.assertIn("法律扶助申請須經資格與個案審查", items["TW-15-002"]["limits"])
        self.assertIn("付款前仍要核對契約", items["TW-15-003"]["limits"])
        self.assertIn("請向1966", items["TW-17-007"]["limits"])

    def test_reader_copy_cleanup_rewrites_batch_notes_as_useful_taiwan_guidance(self):
        runtime = json.loads((audit.ROOT / "localization/tw-edition/runtime.json").read_text(encoding="utf-8"))
        items = {item["id"]: item for item in runtime["items"]}
        self.assertIn("這項研究不代表所有科目和課程", items["TW-23-017"]["body"])
        self.assertIn("臺灣考試或資訊科技職務", items["TW-23-019"]["body"])
        self.assertIn("全道路死亡數不能用來估算安全座椅的保護效果", items["TW-01-010"]["body"])
        self.assertIn("分齡死亡率也不是個人年度跌倒機率", items["TW-01-013"]["body"])
        self.assertIn("不能視為臺灣目前盛行率", items["TW-01-029"]["body"])
        self.assertIn("2021年結果", items["TW-01-044"]["body"])
        self.assertNotIn("罰則依物品、來源地、行為及現行法令判斷，罰則", items["TW-21-013"]["body"])
        self.assertNotIn("本篇另核對", items["TW-NAV-011"]["body"])
        self.assertNotIn("人民幣改標新臺幣", items["TW-07-009"]["body"])
        self.assertNotIn("改按臺灣戶政司", items["TW-07-011"]["body"])
        self.assertIn("頭部外傷離院後的觀察事項", items["TW-13-002"]["body"])
        self.assertNotIn("本次頭部外傷分流來源", items["TW-13-002"]["body"])
        self.assertNotIn("保留前次查閱日", items["TW-13-023"]["body"])
        self.assertNotIn("AI未實際登入", items["TW-24-005"]["body"])
        self.assertIn("整理資料有助醫療人員瞭解病況", items["TW-24-005"]["body"])
        for key in ("TW-24-010", "TW-24-015", "TW-17-005"):
            self.assertNotIn("AI不是", items[key]["body"], key)
        self.assertIn("止血帶只用於危及生命的四肢大量出血", items["TW-13-012"]["body"])
        self.assertNotIn("將止血帶限縮", items["TW-13-012"]["body"])
        self.assertNotIn("補上失溫", items["TW-13-014"]["body"])
        self.assertNotIn("明確區分可逃生路線", items["TW-13-024"]["body"])
        for key in ("TW-13-021", "TW-13-022", "TW-13-027"):
            self.assertNotIn("不是個案診療或作業合格認證", items[key]["body"], key)
        self.assertIn("工作場所的機具防護、風險評估與教育訓練", items["TW-01-042"]["body"])

    def test_recent_reader_copy_normalization_is_reproducible_and_complete(self):
        runtime = json.loads((audit.ROOT / "localization/tw-edition/runtime.json").read_text(encoding="utf-8"))
        items = {item["id"]: item for item in runtime["items"]}
        register = audit.load(audit.ROOT, "localization/retroactive-review-register-20261019.json")
        cleanup_rows = {row["id"]: row for row in register["reader_copy_cleanups"]}

        for key in ("TW-13-012", "TW-13-023", "TW-13-027"):
            row = cleanup_rows[key]
            previous_runtime = audit._git_json(
                audit.ROOT, row["prior_revision"], "localization/tw-edition/runtime.json"
            )
            previous = next(item for item in previous_runtime["items"] if item["id"] == key)
            normalized, _ = audit.normalize_reader_item(previous)
            self.assertEqual(normalized, items[key], key)

        self.assertNotIn("特殊傷勢依119指導，\n", items["TW-13-012"]["body"])
        self.assertIn("迷路或受困時", items["TW-13-027"]["body"])
        self.assertIn("本指南不能取代醫療診斷或職安人員對工作現場的評估。", items["TW-13-023"]["body"])

    def test_high_risk_reader_copy_keeps_its_professional_review_limit(self):
        runtime = json.loads((audit.ROOT / "localization/tw-edition/runtime.json").read_text(encoding="utf-8"))
        item = next(value for value in runtime["items"] if value["id"] == "TW-13-042")
        notice = audit.READER_PROFESSIONAL_LIMITS["TW-13-042"]
        normalized, _ = audit.normalize_reader_item(item)
        self.assertIn(notice, item["body"])
        self.assertIn(notice, normalized["body"])
        self.assertNotIn("器官條例", item["body"])
        self.assertNotIn("本次實質再審", item["body"])

    def test_readme_and_reading_guide_present_plain_taiwan_reading_directions(self):
        readme = (audit.ROOT / "README.md").read_text(encoding="utf-8")
        guide = (audit.ROOT / "REPOSITORY_GUIDE.md").read_text(encoding="utf-8")
        edition_index = (audit.ROOT / "locales/zh-TW/README.md").read_text(encoding="utf-8")
        self.assertIn("開始閱讀", readme)
        self.assertIn("依章節找文章", readme)
        self.assertIn("在電腦上閱讀及使用生活自我檢視", readme)
        self.assertNotIn("](selfcheck.html)", readme)
        self.assertNotIn("已核對的臺灣內容", readme)
        self.assertIn("在本機開啟閱讀頁面", readme)
        self.assertNotIn("請從網站", readme)
        self.assertIn("在電腦上閱讀", guide)
        self.assertIn("在瀏覽器開啟 http://127.0.0.1:8000/ 閱讀", guide)
        self.assertNotIn("已核對的臺灣內容", guide)
        self.assertIn("找不到想看的主題", guide)
        self.assertIn("尚無該主題的臺灣指引", (audit.ROOT / "assets/tw-runtime.js").read_text(encoding="utf-8"))
        self.assertIn("目前收錄的指引", readme)
        self.assertIn("本目錄整理目前收錄的臺灣版文章", edition_index)
        self.assertIn("原作內容的 PDF 預覽", guide)
        self.assertIn("node tools/pdf/build.mjs", guide)
        self.assertIn("不是臺灣版生活指南", guide)

    def test_reader_entry_pages_do_not_contain_batch_audit_logs(self):
        paths = (
            audit.ROOT / "README.md",
            audit.ROOT / "REPOSITORY_GUIDE.md",
            audit.ROOT / "SUPPORT.md",
            audit.ROOT / "ATTRIBUTION.md",
            audit.ROOT / "locales/zh-TW/README.md",
            audit.ROOT / "locales/zh-TW/book/14-帳號與資訊安全.md",
            audit.ROOT / "locales/zh-TW/book/07-失業與生活困難時的支持.md",
            audit.ROOT / "locales/zh-TW/book/15-租屋與買房.md",
            audit.ROOT / "locales/zh-TW/book/19-在職離職與職業災害.md",
            audit.ROOT / "locales/zh-TW/book/23-學習技能與職涯發展.md",
            audit.ROOT / "locales/zh-TW/guides/全民安全與防災準備.md",
            audit.ROOT / "locales/zh-TW/guides/職業安全與健康.md",
            *sorted((audit.ROOT / "locales/zh-TW/book").glob("ch*/README.md")),
        )
        workflow = re.compile(
            r"本批(?:證據|已|再審)|本輪(?:已|共|AI)|本次實質再審|"
            r"專業審閱仍待(?:取得|完成)|累計\d+筆AI|資料查閱日期：|"
            r"PR #\d+|本輪核對紀錄|來源與修改範圍|性質為額外導航|更新查核紀錄"
        )
        for path in paths:
            with self.subTest(path=path.name):
                self.assertFalse(workflow.search(path.read_text(encoding="utf-8")))
        self.assertIn(
            "[第14章文章目錄](ch14/README.md)",
            (audit.ROOT / "locales/zh-TW/book/14-帳號與資訊安全.md").read_text(encoding="utf-8"),
        )
        self.assertIn(
            "[第23章文章目錄](ch23/README.md)",
            (audit.ROOT / "locales/zh-TW/book/23-學習技能與職涯發展.md").read_text(encoding="utf-8"),
        )
        for number, filename, title, link in (
            ("7", "07-失業與生活困難時的支持.md", "失業與生活支持", "ch07/README.md"),
            ("15", "15-租屋與買房.md", "租屋、購屋與房貸", "ch15/README.md"),
            ("19", "19-在職離職與職業災害.md", "勞動權益、職災與離職", "ch19/README.md"),
        ):
            page = (audit.ROOT / "locales/zh-TW/book" / filename).read_text(encoding="utf-8")
            self.assertEqual(page, f"# 第{number}章：{title}\n\n本章文章依主題整理，請從[第{number}章文章目錄]({link})開始閱讀。\n")

    def test_audit_validates_registered_reader_copy_cleanup_edges(self):
        result = audit.audit()
        self.assertGreater(result["summary"].get("reader_copy_cleanups", 0), 0)
        self.assertFalse(result["summary"]["publication_ready"])

    def test_all_existing_and_future_core_and_navigation_are_included(self):
        result = audit.audit()
        root = audit.ROOT
        manifest = json.loads((root / "localization/manifest.json").read_text(encoding="utf-8"))
        runtime = json.loads((root / "localization/tw-edition/runtime.json").read_text(encoding="utf-8"))
        current = {e["id"] for e in manifest["entries"]}
        tracked = {e["id"] for e in result["core"]}
        self.assertEqual(tracked, current)
        self.assertEqual(len(tracked), len(result["core"]))
        self.assertEqual(
            {i["id"] for i in runtime["items"] if i["id"].startswith("TW-NAV-")},
            {i["id"] for i in result["navigation"]},
        )
        self.assertEqual(
            result["summary"]["published_core_retroactively_screened"],
            sum(e["status"] == "verified" for e in manifest["entries"]),
        )
        self.assertFalse(result["summary"]["publication_ready"])

    def test_prior_verified_status_never_automatically_certifies_new_standard(self):
        result = audit.audit()
        for page in result["core"]:
            if page["prior_status"] == "verified":
                self.assertEqual(
                    page["new_standard_review"],
                    "pending_substantive_taiwan_context_and_frequency_recheck",
                )
                self.assertIn("content_sha256", page)
            else:
                self.assertEqual(page["new_standard_review"], "not_published_research_pending")
                self.assertNotIn("evidence_markers_only", page)
        for page in result["navigation"]:
            self.assertEqual(
                page["new_standard_review"],
                "pending_substantive_taiwan_context_and_frequency_recheck",
            )

    def test_heuristic_is_a_marker_not_an_incidence_certificate(self):
        sample = "臺灣2025年官方統計資料顯示，2025年事件100件，但母數未知。"
        marks = audit.cues(sample)
        self.assertTrue(marks["frequency_term_marker"])
        self.assertTrue(marks["tw_context_marker"])
        self.assertTrue(marks["statistic_year_marker"])
        # 只有審閱者取得該年該地的母數與統計定義才可提供真正發生率。

    def test_review_date_or_medical_number_is_not_a_frequency_claim(self):
        markers = audit.cues("臺灣急救先撥119。AI輔助查閱2026-10-19。")
        self.assertTrue(markers["tw_context_marker"])
        self.assertFalse(markers["frequency_term_marker"])
        self.assertFalse(markers["statistic_year_marker"])
        self.assertFalse(markers["numeric_claim_marker"])

    def test_critical_event_prioritization_is_independent_of_frequency(self):
        self.assertEqual(audit.risk(13, "TW-13-001"), "P0")
        self.assertEqual(audit.risk(1, "TW-01-001"), "P0")
        self.assertEqual(audit.risk(14, "TW-14-001"), "P2")
        self.assertEqual(audit.risk(None, "TW-NAV-010"), "P0")


if __name__ == "__main__":
    unittest.main()

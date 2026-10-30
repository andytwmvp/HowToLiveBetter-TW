"""第23章六篇學習方法再審及臺灣讀者入口用語的同步檢查。"""
import hashlib
import json
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ci_language_policy import audit_drafts
from content_validation import load_json
from retroactive_audit import assert_preserved_or_rechecked, validate_recheck_history
from review_contract import ROOT, validate_runtime


BASE = "80b1df944cf6807d91bbf32a0c45a56d149c2136"
EVIDENCE = "localization/ch23-learning-methods-recheck-20261029.json"
ITEM_IDS = (
    "TW-23-014",
    "TW-23-015",
    "TW-23-016",
    "TW-23-017",
    "TW-23-018",
    "TW-23-019",
)
NEW_SOURCE_IDS = {
    "ch23_interleave_recheck_20261029",
    "ch23_learning_styles_meta_2024_20261029",
    "ch23_learning_styles_pashler_recheck_20261029",
    "ch23_learning_styles_review_2025_20261029",
    "ch23_moe_assessment_recheck_20261029",
    "ch23_moe_specialed_recheck_20261029",
    "ch23_retrieval_recheck_20261029",
    "ch23_skill_exam_20261029",
    "ch23_spacing_recheck_20261029",
    "ch23_techniques_recheck_20261029",
    "ch23_transfer_recheck_20261029",
}
READER_DOCUMENTS = {
    "README.md",
    "REPOSITORY_GUIDE.md",
    "locales/zh-TW/README.md",
    "locales/zh-TW/book/ch23/README.md",
    "skills/life-decision-guide/README.md",
}


def read(path):
    return load_json(ROOT / path)


def old(path):
    return json.loads(subprocess.check_output(
        ["git", "show", f"{BASE}:{path}"], cwd=ROOT, text=True
    ))


def runtime_at(revision):
    return json.loads(subprocess.check_output(
        ["git", "show", f"{revision}:localization/tw-edition/runtime.json"],
        cwd=ROOT, text=True,
    ))["items"]


class Ch23LearningMethodsRecheckTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.evidence = read(EVIDENCE)
        cls.runtime = validate_runtime()
        cls.items = {item["id"]: item for item in cls.runtime["items"]}
        cls.sources = {source["id"]: source for source in cls.runtime["sources"]}
        cls.manifest = {
            item["id"]: item for item in read("localization/manifest.json")["entries"]
        }
        cls.register = read("localization/retroactive-review-register-20261019.json")
        cls.base_register = old("localization/retroactive-review-register-20261019.json")
        cls.rows = cls.register["substantive_rechecks"]
        cls.evidence_items = {item["id"]: item for item in cls.evidence["items"]}

    def test_batch_progress_is_append_only_and_contains_no_new_core_articles(self):
        before = self.evidence["counts_before"]
        after = self.evidence["counts_after"]
        coverage = read("localization/tw-edition/coverage.json")
        self.assertEqual(self.evidence["base_main_sha"], BASE)
        self.assertEqual(set(self.evidence_items), set(ITEM_IDS))
        self.assertEqual(self.evidence["new_core_entries"], [])
        self.assertEqual(after["substantive_rechecks"], before["substantive_rechecks"] + len(ITEM_IDS))
        self.assertEqual(after["runtime_sources"], before["runtime_sources"] + len(NEW_SOURCE_IDS))
        self.assertEqual(after["source_registry"], before["source_registry"] + len(NEW_SOURCE_IDS))
        self.assertEqual(after["json_files_checked"], before["json_files_checked"] + 2)
        self.assertEqual(after["core_completed"], before["core_completed"])
        self.assertEqual(after["core_total"], before["core_total"])
        # Later batches append to the live register; this historical batch must
        # remain verifiable without requiring the register to stop at its old size.
        self.assertGreaterEqual(len(self.rows), after["substantive_rechecks"])
        self.assertEqual(self.rows[:len(self.base_register["substantive_rechecks"])],
                         self.base_register["substantive_rechecks"])
        for item_id in ITEM_IDS:
            self.assertEqual(
                sum(row["id"] == item_id for row in self.rows),
                sum(row["id"] == item_id for row in self.base_register["substantive_rechecks"]) + 1,
            )
        self.assertEqual(coverage, audit_drafts())
        self.assertFalse(self.evidence["publication_ready"])
        self.assertFalse(coverage["publication_ready"])

    def test_article_text_review_runtime_manifest_and_history_match(self):
        for item_id in ITEM_IDS:
            with self.subTest(item=item_id):
                current = self.items[item_id]
                evidence_item = self.evidence_items[item_id]
                path = current["target_path"]
                body = (ROOT / path).read_bytes()
                digest = hashlib.sha256(body).hexdigest()
                review = read(f"localization/reviews/{item_id}.json")
                history = next(
                    row for row in reversed(self.rows) if row["id"] == item_id
                )
                prior_body = subprocess.check_output(
                    ["git", "show", f"{BASE}:{path}"], cwd=ROOT
                )
                prior_review_path = f"localization/reviews/{item_id}.json"
                prior_review = subprocess.check_output(
                    ["git", "show", f"{BASE}:{prior_review_path}"], cwd=ROOT
                )

                self.assertEqual(body.decode("utf-8"), current["body"])
                self.assertEqual(digest, evidence_item["after_sha256"])
                self.assertEqual(digest, review["target_sha256"])
                self.assertEqual(hashlib.sha256(prior_body).hexdigest(), evidence_item["before_sha256"])
                self.assertEqual(hashlib.sha256(prior_review).hexdigest(), evidence_item["prior_review_sha256"])
                self.assertEqual(history["prior_revision"], BASE)
                self.assertEqual(history["before_sha256"], evidence_item["before_sha256"])
                self.assertEqual(history["after_sha256"], digest)
                self.assertEqual(history["source_ids"], current["source_ids"])
                self.assertEqual(history["source_checks"], review["source_checks"])
                self.assertEqual(history["limits"], review["limits"])
                self.assertEqual(history["status"], "ai_source_rechecked_professional_pending")
                self.assertEqual(review["reviewed_at"], self.evidence["reviewed_at"])
                self.assertEqual(review["review_due_at"], self.evidence["review_due_at"])
                self.assertEqual(
                    self.manifest[item_id]["sources"],
                    [self.sources[source_id]["url"] for source_id in current["source_ids"]],
                )
                self.assertEqual(
                    {check["url"] for check in review["source_checks"]},
                    {self.sources[source_id]["url"] for source_id in current["source_ids"]},
                )
                frequency_assessment = history["frequency_assessment"]
                self.assertIn("發生率", frequency_assessment)
                self.assertTrue(any(
                    wording in frequency_assessment
                    for wording in ("發生率不適用", "不是事件發生率", "不是自然事件發生率")
                ))
                self.assertTrue(history["taiwan_context"])
                self.assertTrue(history["source_checks"])
                self.assertTrue(history["statistics_assessed"] or item_id == "TW-23-016")
                validate_recheck_history(ROOT, history, current)

    def test_sources_are_additive_and_registered_in_the_batch_catalog(self):
        prior_sources = {source["id"]: source for source in old("localization/tw-edition/runtime.json")["sources"]}
        self.assertTrue(set(prior_sources).issubset(self.sources))
        for source_id, source in prior_sources.items():
            self.assertEqual(self.sources[source_id], source)

        added = {source["id"]: source for source in self.evidence["sources_added"]}
        self.assertEqual(set(added), NEW_SOURCE_IDS)
        catalog = read("localization/tw-edition/sources/ch23-learning-methods-recheck-20261029.json")
        self.assertEqual({row[0] for row in catalog["sources"]}, NEW_SOURCE_IDS)
        registry_rows = {row[0]: row for row in catalog["sources"]}
        for source_id, source in added.items():
            with self.subTest(source=source_id):
                self.assertEqual(self.sources[source_id], source)
                self.assertEqual(registry_rows[source_id][1], source["title"])
                self.assertEqual(registry_rows[source_id][2], source["url"])
                self.assertEqual(registry_rows[source_id][3], source["supports"])
                self.assertEqual(source["accessed_at"], self.evidence["reviewed_at"])
                self.assertTrue(source["retrieval_method"])

    def test_special_education_plan_types_and_article_9_limits_are_explicit(self):
        item = self.items["TW-23-018"]
        body = item["body"]
        self.assertIn("個別化教育計畫或個別輔導計畫", body)
        self.assertIn("符合辦法第9條條件", body)
        self.assertIn("調整後基準及定期評量的合理調整服務須載明於個別化教育計畫", body)
        source = self.sources["ch23_moe_specialed_recheck_20261029"]
        self.assertIn("第2條", source["supports"])
        self.assertIn("第9條", source["supports"])
        self.assertIn("個別化教育計畫或個別輔導計畫", source["supports"])

    def test_reader_facing_copy_uses_taiwan_wording_and_matches_article_titles(self):
        documents = {row["path"]: row for row in self.evidence["reader_documents"]}
        next_documents = {
            row["path"]: row
            for row in read("localization/ch15-ch21-high-risk-recheck-20261029.json")["reader_documents"]
        }
        cleanups = {
            row["path"]: row
            for row in read("localization/reader-language-cleanup-20261029.json")["reader_documents"]
        }
        current_cleanup = read("localization/reader-language-cleanup-20261031.json")
        current_surfaces = {row["path"]: row for row in current_cleanup["reader_surfaces"]}
        self.assertEqual(set(documents), READER_DOCUMENTS)
        self.assertEqual(set(cleanups), {"README.md", "REPOSITORY_GUIDE.md", "locales/zh-TW/README.md"})
        self.assertTrue(set(cleanups).issubset(current_surfaces))
        self.assertEqual(current_cleanup["prior_revision"], "b0367db7a5f817462020670bfafdfef3dd020fab")
        self.assertEqual(
            read("localization/reader-language-cleanup-20261029.json")["prior_revision"],
            "454c0b6a193b2503749a5f579c882311631edc41",
        )
        for path, row in documents.items():
            with self.subTest(path=path):
                prior = subprocess.check_output(["git", "show", f"{BASE}:{path}"], cwd=ROOT)
                current = (ROOT / path).read_bytes()
                self.assertEqual(hashlib.sha256(prior).hexdigest(), row["before_sha256"])
                current_sha256 = hashlib.sha256(current).hexdigest()
                if path in cleanups:
                    self.assertEqual(row["after_sha256"], next_documents[path]["before_sha256"])
                    self.assertEqual(next_documents[path]["after_sha256"], cleanups[path]["before_sha256"])
                    main_prior = subprocess.check_output(
                        ["git", "show", f"{current_cleanup['prior_revision']}:{path}"], cwd=ROOT
                    )
                    self.assertEqual(hashlib.sha256(main_prior).hexdigest(), cleanups[path]["after_sha256"])
                    self.assertEqual(current_surfaces[path]["before_sha256"], cleanups[path]["after_sha256"])
                    self.assertEqual(current_sha256, current_surfaces[path]["after_sha256"])
                else:
                    self.assertEqual(current_sha256, row["after_sha256"])

        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        guide = (ROOT / "REPOSITORY_GUIDE.md").read_text(encoding="utf-8")
        self.assertIn("目錄未列出的主題，目前沒有可供閱讀的台灣版指引", readme)
        self.assertIn("在 GitHub 上直接開啟 HTML 檔會看到程式碼", readme)
        self.assertIn("開啟終端機，下載專案並切換到資料夾", guide)
        self.assertIn("py -3 -m http.server 8000 --bind 127.0.0.1", guide)
        self.assertIn("python3 -m http.server 8000 --bind 127.0.0.1", guide)
        self.assertIn("按 Ctrl+C 停止本機閱讀頁", guide)
        self.assertIn("離線閱讀檔", guide)

        reader_paths = {
            ROOT / "README.md",
            ROOT / "REPOSITORY_GUIDE.md",
            ROOT / "locales/zh-TW/README.md",
            ROOT / "skills/life-decision-guide/README.md",
            *ROOT.glob("locales/zh-TW/book/*/README.md"),
            *ROOT.glob("locales/zh-TW/guides/*.md"),
        }
        process_notes = (
            "本批證據", "累計41篇AI來源實質再審", "累計36篇AI來源實質再審",
            "臺灣版尚在逐條改寫與查證", "僅在此 fork 維護",
            "還沒有完成查證", "尚未完成查證",
        )
        non_taiwan_terms = ("閉卷提取", "保留目標", "用戶", "視頻", "軟件", "登錄")
        for path in sorted(reader_paths):
            content = path.read_text(encoding="utf-8")
            with self.subTest(reader_document=path.relative_to(ROOT).as_posix()):
                self.assertFalse(any(note in content for note in process_notes))
                self.assertFalse(any(term in content for term in non_taiwan_terms))

        index = (ROOT / "locales/zh-TW/book/ch23/README.md").read_text(encoding="utf-8")
        self.assertNotIn("閉卷提取", index)
        self.assertNotIn("保留目標", index)
        for item_id in ITEM_IDS:
            article = (ROOT / f"locales/zh-TW/book/ch23/{item_id}.md").read_text(encoding="utf-8")
            title = article.splitlines()[0].removeprefix("# ")
            self.assertIn(f"[{title}]({item_id}.md)", index)

    def test_repo_status_and_review_pages_are_concise_record_indexes(self):
        project_state = (ROOT / "PROJECT_STATE.md").read_text(encoding="utf-8")
        review_index = (ROOT / "localization/RETROACTIVE_REVIEW.md").read_text(encoding="utf-8")
        self.assertIn("不逐批重述研究、正文修改或 PR 進度", project_state)
        self.assertIn("localization/retroactive-review-register-20261019.json", project_state)
        self.assertIn("不逐批刊載工作摘要", review_index)
        self.assertIn("retroactive-review-register-20261019.json", review_index)
        for page in (project_state, review_index):
            self.assertNotIn("# 2026-", page)
            self.assertNotIn("本批證據", page)

    def test_prior_reader_copy_cleanup_connects_to_this_substantive_recheck(self):
        cleanups = self.register["reader_copy_cleanups"]
        for item_id in ITEM_IDS:
            with self.subTest(item=item_id):
                cleanup = next(row for row in cleanups if row["id"] == item_id)
                prior = next(
                    item for item in runtime_at(cleanup["prior_revision"])
                    if item["id"] == item_id
                )
                assert_preserved_or_rechecked(self, prior, self.items[item_id])


if __name__ == "__main__":
    unittest.main()

"""台灣閱讀入口及正文不顯示內部編修紀錄。"""
import hashlib
import json
from pathlib import Path
import re
import sqlite3
import sys
import subprocess
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools/tw"))
from retroactive_audit import validate_reader_copy_cleanup_history, validate_recheck_history
from edition import build_anki, build_epub, refs as export_refs


INTERNAL_READER_NOTE_PATTERNS = (
    re.compile(r"20\d{2}-\d{2}-\d{2}.{0,20}(?:\d+篇)?(?:安全|高風險)?再審"),
    re.compile(r"(?:本批|本次|本輪).{0,24}(?:證據|再審|審查|回溯|來源盤點)"),
    re.compile(r"(?:累計|累積|共計)\s*\d+\s*(?:篇|則|條|項).{0,20}(?:AI來源|實質再審|審查|再審|專業審閱)"),
    re.compile(r"專業審閱(?:仍|尚)?待(?:取得|補足|完成|邀請)"),
    re.compile(r"僅在此\s*fork\s*(?:維護|修改)"),
    re.compile(r"臺灣版尚在逐條改寫與查證"),
    re.compile(r"下方.{0,12}原作.{0,16}(?:字形)?轉換稿"),
    re.compile(r"(?im)(?:^|\s)(?:PR|Pull Request)\s*#\d+"),
    re.compile(r"(?im)(?:^|\s)CI\s*(?:成功|通過|綠燈)"),
)


class ReaderLanguageCleanupTests(unittest.TestCase):
    def read(self, path):
        return (ROOT / path).read_text(encoding="utf-8")

    def test_recent_article_cleanup_matches_runtime_and_keeps_review_history(self):
        runtime = json.loads(self.read("localization/tw-edition/runtime.json"))
        register = json.loads(self.read("localization/retroactive-review-register-20261019.json"))
        items = {item["id"]: item for item in runtime["items"]}
        substantive = {row["id"]: row for row in register["substantive_rechecks"]}
        for item_id in ("TW-01-015", "TW-16-005", "TW-16-011", "TW-17-011", "TW-24-014", "TW-24-006", "TW-13-042"):
            item = items[item_id]
            body_sha = hashlib.sha256(item["body"].encode("utf-8")).hexdigest()
            with self.subTest(item_id=item_id):
                markdown = self.read(item["target_path"])
                self.assertEqual(markdown, item["body"])
                self.assertNotIn("逐來源實讀範圍", item["body"])
                self.assertNotIn("前後SHA", item["body"])
                self.assertNotIn("本篇核對現行法", item["body"])
                self.assertNotIn("尚未經醫療、社工、法律及急救專業人員獨立審閱", item["body"])
                matches = [row for row in register["reader_copy_cleanups"]
                           if row.get("id") == item_id and row.get("after_sha256") == body_sha]
                self.assertEqual(len(matches), 1)
                self.assertEqual(matches[0]["transform"], "reader_copy_cleanup_v3")
                validate_reader_copy_cleanup_history(ROOT, matches[0], item)
                if item_id in substantive:
                    validate_recheck_history(ROOT, substantive[item_id], item)

    def test_entry_points_use_reader_language_without_batch_status(self):
        paths = ("README.md", "REPOSITORY_GUIDE.md", "locales/zh-TW/README.md")
        for path in paths:
            text = self.read(path)
            with self.subTest(path=path):
                self.assertNotIn("tw-bootstrap-v1", text)
                self.assertNotRegex(text, r"本批證據|累計\d+篇|PR #\d+|CI 成功|下方為原作")
        self.assertIn("台灣生活中的實際做法", self.read("README.md"))
        self.assertIn("在電腦上開啟台灣生活指南", self.read("REPOSITORY_GUIDE.md"))
        review = json.loads(self.read("localization/reviews/TW-13-042.json"))
        self.assertIn("AI輔助", review["reviewer"])

    def test_published_reader_surfaces_exclude_internal_batch_notes(self):
        runtime = json.loads(self.read("localization/tw-edition/runtime.json"))
        reader_texts = {
            "runtime scope": runtime["scope"],
            "runtime title": runtime["title"],
        }
        for item in runtime["items"]:
            for field in ("title", "body", "limits", "question"):
                if item.get(field):
                    reader_texts[f"{item['id']} {field}"] = item[field]
            if item["id"].startswith("TW-") and not item["id"].startswith("TW-NAV-"):
                chapter = int(item["id"][3:5])
                path = Path(f"locales/zh-TW/book/ch{chapter:02d}/{item['id']}.md")
                reader_texts[str(path)] = self.read(path)

        reader_titles = runtime.get("reader_source_titles", {})
        for source in runtime["sources"]:
            source_id = source["id"]
            reader_texts[f"{source_id} reader source title"] = reader_titles.get(
                source_id, source["title"]
            )
            reader_texts[f"{source_id} reader source description"] = source["supports"]

        fixed_surfaces = (
            "README.md", "REPOSITORY_GUIDE.md", "locales/zh-TW/README.md",
            "index.html", "selfcheck.html", "source.html", "assets/tw-runtime.js",
            "skills/life-decision-guide/SKILL.md",
            "skills/life-decision-guide/README.md",
        )
        for path in fixed_surfaces:
            reader_texts[path] = self.read(path)
        for path in sorted((ROOT / "locales/zh-TW/guides").glob("*.md")):
            reader_texts[str(path.relative_to(ROOT))] = path.read_text(encoding="utf-8")

        for label, text in reader_texts.items():
            for pattern in INTERNAL_READER_NOTE_PATTERNS:
                with self.subTest(surface=label, pattern=pattern.pattern):
                    self.assertIsNone(pattern.search(text),
                                      f"讀者內容含有內部批次或審查註記：{label}")

    def test_internal_note_patterns_catch_common_editorial_variants(self):
        examples = (
            "2026-10-20五篇安全再審：已逐條核對。",
            "本批安全再審：已逐條核對。",
            "累計41篇AI來源實質再審。",
            "專業審閱仍待取得。",
            "僅在此 fork 維護。",
            "臺灣版尚在逐條改寫與查證。",
            "下方為原作的繁體字形轉換稿。",
            "PR #106 CI 成功。",
        )
        for text in examples:
            with self.subTest(text=text):
                self.assertTrue(any(pattern.search(text)
                                    for pattern in INTERNAL_READER_NOTE_PATTERNS))

    def test_source_preview_interface_uses_taiwan_phrasing(self):
        text = self.read("source.html")
        self.assertIn("正在載入內容…", text)
        self.assertNotIn("正在讀取正文", text)
        for phrase in ("搜索條目", "打開篩選", "薈萃/RCT", "高效益人生指南",
                       "不代表臺灣現行生活建議", "原作正文與標籤來自"):
            with self.subTest(phrase=phrase):
                self.assertNotIn(phrase, text)
        for phrase in ("搜尋原作內容", "開啟篩選", "原作成本效益", "家有長輩",
                       "要找台灣生活中的實際做法", "台灣文章目錄"):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)
        self.assertIn('目前顯示 <b id="cnt">–</b> 則，共 <span id="tot">–</span> 則', text)
        self.assertIn("本指南依臺灣生活情境整理", json.loads(
            self.read("localization/tw-edition/runtime.json"))["scope"])

    def test_visible_source_title_uses_reader_copy_and_keeps_source_history(self):
        base = "b747f1529e607d2970f1593be464b9f5e88203dc"
        runtime = json.loads(self.read("localization/tw-edition/runtime.json"))
        cleanup = json.loads(self.read("localization/reader-language-cleanup-20261029.json"))
        batches = [row for row in cleanup["source_annotation_batches"]
                   if row.get("reviewed_at") == "2026-10-30"]
        self.assertEqual(len(batches), 1)
        batch = batches[0]
        self.assertEqual(batch["base_main_sha"], base)
        self.assertEqual(batch["source_count"], len(batch["sources"]))
        self.assertEqual(runtime["updated_at"], "2026-10-30")

        before_runtime = json.loads(subprocess.check_output(
            ["git", "show", f"{base}:localization/tw-edition/runtime.json"],
            cwd=ROOT, text=True,
        ))
        before_sources = {row["id"]: row for row in before_runtime["sources"]}
        current_sources = {row["id"]: row for row in runtime["sources"]}

        def digest(value):
            canonical = json.dumps(
                value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
            ).encode("utf-8")
            return hashlib.sha256(canonical).hexdigest()

        self.assertEqual(batch["source_count"], 1)
        self.assertEqual(len(batch["sources"]), 1)
        self.assertEqual(set(runtime["reader_source_titles"]), {"criminal"})
        self.assertTrue(set(before_sources).issubset(current_sources))
        for source_id, previous in before_sources.items():
            self.assertEqual(current_sources[source_id], previous)
        for row in batch["sources"]:
            source_id = row["id"]
            with self.subTest(source_id=source_id):
                previous = before_sources[source_id]
                current = current_sources[source_id]
                self.assertEqual(previous["title"], row["title_before"])
                self.assertEqual(current, previous)
                self.assertEqual(digest(current), row["source_object_sha256"])
                self.assertEqual(runtime["reader_source_titles"][source_id], row["title_after"])
                self.assertEqual(
                    digest({"id": source_id, "title": row["title_before"]}),
                    row["reader_title_before_sha256"],
                )
                self.assertEqual(
                    digest({"id": source_id, "title": runtime["reader_source_titles"][source_id]}),
                    row["reader_title_after_sha256"],
                )
                self.assertNotIn("本批", runtime["reader_source_titles"][source_id])
                self.assertNotIn("核對", runtime["reader_source_titles"][source_id])
                catalog = ROOT / row["historical_catalog_path"]
                self.assertEqual(
                    hashlib.sha256(catalog.read_bytes()).hexdigest(),
                    row["historical_catalog_sha256"],
                )

        interface = self.read("assets/tw-runtime.js")
        self.assertIn("來源可佐證內容", interface)
        self.assertNotIn("來源支持範圍", interface)
        self.assertIn("catalog.reader_source_titles?.[id] ?? s.title", interface)

        reader_item = next(item for item in runtime["items"]
                           if "criminal" in item["source_ids"])
        exported_source = next(source for source in export_refs(reader_item, runtime)
                               if source["id"] == "criminal")
        self.assertEqual(exported_source["title"], runtime["reader_source_titles"]["criminal"])
        self.assertEqual(current_sources["criminal"]["title"], row["title_before"])

        with tempfile.TemporaryDirectory(prefix="htlb-reader-title-") as folder:
            epub_path = Path(folder) / "reader.epub"
            build_epub(epub_path, runtime)
            with zipfile.ZipFile(epub_path) as archive:
                epub_content = archive.read("OEBPS/content.xhtml").decode("utf-8")
            self.assertIn(row["title_after"], epub_content)
            self.assertNotIn(row["title_before"], epub_content)

            anki_path = Path(folder) / "reader.apkg"
            build_anki(anki_path, runtime)
            database_path = Path(folder) / "collection.anki2"
            with zipfile.ZipFile(anki_path) as archive:
                database_path.write_bytes(archive.read("collection.anki2"))
            with sqlite3.connect(database_path) as database:
                fields = [field for (field,) in database.execute("SELECT flds FROM notes")]
            self.assertTrue(any(row["title_after"] in field for field in fields))
            self.assertFalse(any(row["title_before"] in field for field in fields))


if __name__ == "__main__":
    unittest.main()

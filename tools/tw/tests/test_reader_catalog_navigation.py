"""已核對的正式文章須可由章節目錄及各章目錄找到。"""
import json
import re
import sys
import unittest
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from review_contract import ROOT


CORE_ID = re.compile(r"TW-(\d{2})-(\d{3})\Z")
CHAPTER_LINK = re.compile(r"\[第(\d+)章：[^\]]+\]\(book/ch(\d+)/README\.md\)")
ARTICLE_LINK = re.compile(r"\]\((TW-\d{2}-\d{3})\.md\)")


class ReaderCatalogNavigationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.runtime = json.loads(
            (ROOT / "localization/tw-edition/runtime.json").read_text(encoding="utf-8")
        )
        cls.manifest = json.loads(
            (ROOT / "localization/manifest.json").read_text(encoding="utf-8")
        )
        cls.core_items = {
            item["id"]: item
            for item in cls.runtime["items"]
            if CORE_ID.fullmatch(item.get("id", ""))
        }
        cls.items_by_chapter = defaultdict(set)
        for item_id in cls.core_items:
            cls.items_by_chapter[int(item_id[3:5])].add(item_id)

    def test_main_reader_entry_links_to_localized_chapter_catalog(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertRegex(readme, r"\]\(locales/zh-TW/README\.md\)")

    def test_catalog_lists_every_chapter_with_published_core_content(self):
        catalog = (ROOT / "locales/zh-TW/README.md").read_text(encoding="utf-8")
        links = CHAPTER_LINK.findall(catalog)
        listed = [int(chapter) for chapter, _path_number in links]
        linked_paths = [int(path_number) for _chapter, path_number in links]

        self.assertEqual(Counter(listed), Counter(linked_paths))
        self.assertEqual(set(listed), set(self.items_by_chapter))
        self.assertEqual(len(listed), len(set(listed)), "章節目錄不可重複列出同一章")
        for chapter in self.items_by_chapter:
            self.assertTrue(
                (ROOT / f"locales/zh-TW/book/ch{chapter:02d}/README.md").is_file(),
                f"第{chapter}章目錄不存在",
            )

    def test_each_chapter_catalog_links_every_published_core_article_once(self):
        manifest = {item["id"]: item for item in self.manifest["entries"]}
        for chapter, expected_ids in sorted(self.items_by_chapter.items()):
            with self.subTest(chapter=chapter):
                path = ROOT / f"locales/zh-TW/book/ch{chapter:02d}/README.md"
                contents = path.read_text(encoding="utf-8")
                linked_ids = ARTICLE_LINK.findall(contents)
                self.assertEqual(Counter(linked_ids), Counter(expected_ids))
                for item_id in expected_ids:
                    target_path = self.core_items[item_id]["target_path"]
                    self.assertEqual(manifest[item_id]["target_path"], target_path)
                    self.assertTrue((ROOT / target_path).is_file(), f"{item_id}正文不存在")


if __name__ == "__main__":
    unittest.main()

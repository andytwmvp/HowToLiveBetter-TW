"""Shared chapter-row history checks reject omissions and inconsistent publications."""
import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from recheck_history_assertions import assert_chapter_entries_preserved_or_rechecked

BASE = "886a47907fa0a70b9e9889357ccd2c92411ba519"
CHAPTER_PATH = "localization/tw-edition/chapters/02.json"
RUNTIME_PATH = "localization/tw-edition/runtime.json"
REGISTER_PATH = "localization/retroactive-review-register-20261019.json"
ITEM_ID = "TW-02-036"


def json_at(revision, path):
    return json.loads(subprocess.check_output(
        ["git", "show", f"{revision}:{path}"], cwd=ROOT
    ))


def by_id(rows):
    return {row["id"]: row for row in rows}


class ChapterRowHistoryAssertionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base_chapter = json_at(BASE, CHAPTER_PATH)
        cls.current_chapter = json_at("HEAD", CHAPTER_PATH)
        cls.base_runtime = json_at(BASE, RUNTIME_PATH)
        cls.current_runtime = json_at("HEAD", RUNTIME_PATH)
        cls.base_register = json_at(BASE, REGISTER_PATH)
        cls.current_register = json_at("HEAD", REGISTER_PATH)

    def _published_draft_case(self, current_items=None):
        old_row = next(row for row in self.base_chapter["entries"] if row[0] == 36)
        current_row = next(row for row in self.current_chapter["entries"] if row[0] == 36)
        baseline_items = by_id(self.base_runtime["items"])
        current_items = current_items or by_id(self.current_runtime["items"])
        return assert_chapter_entries_preserved_or_rechecked(
            self,
            chapter_number=2,
            baseline_entries=[old_row],
            current_entries=[current_row],
            baseline_items=baseline_items,
            current_items=current_items,
            baseline_rechecks=self.base_register["substantive_rechecks"],
            current_rechecks=self.current_register["substantive_rechecks"],
        )

    def test_first_publication_is_allowed_when_the_original_draft_hash_and_sources_match(self):
        self.assertEqual(self._published_draft_case(), {ITEM_ID})

    def test_first_publication_with_inconsistent_sources_is_rejected(self):
        current_items = by_id(self.current_runtime["items"])
        current_items[ITEM_ID] = dict(current_items[ITEM_ID], source_ids=[])
        with self.assertRaises(AssertionError):
            self._published_draft_case(current_items)

    def test_missing_chapter_row_is_rejected(self):
        with self.assertRaises(AssertionError):
            assert_chapter_entries_preserved_or_rechecked(
                self,
                chapter_number=2,
                baseline_entries=[[36, "title", "summary", "steps"]],
                current_entries=[],
                baseline_items={},
                current_items={},
                baseline_rechecks=[],
                current_rechecks=[],
            )


if __name__ == "__main__":
    unittest.main()

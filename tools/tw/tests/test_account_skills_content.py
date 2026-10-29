"""本輪正文、固定ID與來源索引一致性；不把工程測試當作法律或事實簽證。"""
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[3]
AUDIT = 'localization/source-audits/20261015-account-skills.json'


class AccountSkillsContentTests(unittest.TestCase):
    def load(self, path):
        return json.loads((ROOT / path).read_text(encoding='utf-8'))

    def test_item_ids_are_published_and_draft_sources_remain_registered(self):
        audit = self.load(AUDIT)
        manifest = {row['id']: row for row in self.load('localization/manifest.json')['entries']}
        sources = {row[0]: row for row in self.load(audit['source_registry'])['sources']}
        ids = [row['id'] for row in audit['items']]
        self.assertEqual(len(ids), len(set(ids)))
        for item in audit['items']:
            with self.subTest(item=item['id']):
                self.assertIn(item['id'], manifest)
                # The historical draft names an early chapter path and source
                # set. Check the ID in its current canonical article, while
                # keeping the draft citations attached to their own registry.
                target_path = manifest[item['id']]['target_path']
                section = (ROOT / target_path).read_text(encoding='utf-8')
                self.assertIn(f"<!-- TW-ID: {item['id']} -->", section)
                for source_id in item['source_ids']:
                    self.assertIn(source_id, sources)

    def test_registry_matches_source_notes_without_duplicate_ids(self):
        audit = self.load(AUDIT)
        registry = {}
        for path in sorted((ROOT / 'localization/tw-edition/sources').glob('*.json')):
            for row in json.loads(path.read_text(encoding='utf-8'))['sources']:
                self.assertEqual(len(row), 4)
                self.assertNotIn(row[0], registry)
                registry[row[0]] = row
        for source in audit['sources']:
            self.assertIn(source['id'], registry)
            self.assertTrue(registry[source['id']][2].startswith('https://'))
            self.assertTrue(registry[source['id']][3].strip())
            self.assertTrue(source['method'].strip())
            self.assertTrue(source['accessed_at'].strip())

    def test_batch_does_not_claim_publication_or_full_chapter_23(self):
        audit = self.load(AUDIT)
        self.assertEqual(audit['status'], 'draft_source_notes')
        new = {row['id'] for row in audit['items'] if row['id'].startswith('TW-23-')}
        self.assertEqual(new, {'TW-23-001', 'TW-23-008', 'TW-23-009'})
        self.assertTrue(all(row['stage'] == 'draft_with_source_notes' for row in audit['items']))
        self.assertIn('不是逐字引文', audit['summary_method'])


if __name__ == '__main__':
    unittest.main()

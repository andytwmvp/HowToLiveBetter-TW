"""第19章勞動契約與離職權益的正文、來源與增量整合回歸。"""
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from body_renderer import body_blocks
from review_contract import ROOT,validate_entry,validate_runtime,publication_report
from ci_language_policy import audit_drafts
BASE='23c6f7b506fa22b98cf0232c1f78c515308f6d6b'
IDS={f'TW-19-{n:03}' for n in (1,2,3,4,5,6,7,8,17,20,22,23,24)}

def read(path):return json.loads((ROOT/path).read_text(encoding='utf-8'))
def baseline(path):return json.loads(subprocess.check_output(['git','show',BASE+':'+path],cwd=ROOT,text=True))

class LaborChapterTests(unittest.TestCase):
    def test_thirteen_entries_have_matching_bodies_reviews_and_runtime(self):
        manifest=read('localization/manifest.json');runtime={e['id']:e for e in validate_runtime()['items']}
        entries=[e for e in manifest['entries'] if e['id'] in IDS]
        self.assertEqual({e['id'] for e in entries},IDS)
        for entry in entries:
            with self.subTest(id=entry['id']):
                self.assertEqual(entry['status'],'verified');self.assertTrue(validate_entry(entry))
                raw=(ROOT/entry['target_path']).read_bytes();review=read(f"localization/reviews/{entry['id']}.json")
                self.assertEqual(raw.decode(),runtime[entry['id']]['body']);self.assertGreater(len(raw.decode()),650)
                self.assertEqual(review['target_sha256'],hashlib.sha256(raw).hexdigest())
                self.assertEqual(review['review_due_at'],'2026-12-31');self.assertIn('AI',review['reviewer'])
                self.assertTrue(all('非逐字引文' in s['supporting_passage'] for s in review['source_checks']))
                self.assertEqual(len([b for b in body_blocks(runtime[entry['id']]) if b['tag']=='h3']),5)
        self.assertGreaterEqual(publication_report()['publication_completed_entries'],25)

    def test_previous_reviewed_runtime_items_and_sources_are_unchanged(self):
        old=baseline('localization/tw-edition/runtime.json');new=validate_runtime()
        old_ids={e['id'] for e in old['items']};old_sources={s['id'] for s in old['sources']}
        self.assertEqual(old['items'],[e for e in new['items'] if e['id'] in old_ids])
        self.assertEqual(old['sources'],[s for s in new['sources'] if s['id'] in old_sources])

    def test_new_sources_have_exact_registered_urls_and_claims(self):
        batch=read('localization/tw-edition/ch19-reviewed.json')
        runtime={s['id']:s for s in validate_runtime()['sources']}
        registry={r[0]:r for r in read('localization/tw-edition/sources/ch19.json')['sources']}
        self.assertEqual(len(registry),14)
        for source in batch['sources']:
            self.assertEqual(registry[source['id']][2],source['url']);self.assertEqual(runtime[source['id']],source)
        for item in batch['entries']:
            self.assertEqual(set(item['source_ids']),set(item['source_claims']))
            self.assertTrue(set(item['source_ids']).issubset(registry))
            self.assertTrue(all(len(c)>15 for c in item['source_claims'].values()))

    def test_original_identity_is_preserved_without_freezing_progress(self):
        old=baseline('localization/manifest.json')['entries'];new=read('localization/manifest.json')['entries']
        keys=('id','upstream_chapter','upstream_item','upstream_commit','upstream_text_sha256','upstream_path_uri','display_path','source_title_zh_tw')
        self.assertEqual(len(new),765)
        for before,after in zip(old,new,strict=True):
            for key in keys:self.assertEqual(before[key],after[key])

    def test_existing_draft_topics_not_double_counted(self):
        report=audit_drafts();self.assertGreaterEqual(report['unique_draft_entries'],388)
        self.assertEqual(report['structured_draft_entries'],373)
        self.assertEqual(report['unique_draft_entries']+report['entries_without_any_draft'],765)
        self.assertEqual(report['publication_total_entries'],765)
        # 本批13個原作主題原本全部存在於結構化草稿。
        draft=read('localization/tw-edition/chapters/19.json')
        self.assertTrue(IDS.issubset({f"TW-19-{row[0]:03}" for row in draft['entries']}))

    def test_both_example_amounts_and_ten_year_leave_boundary(self):
        entries={e['id']:e for e in validate_runtime()['items']}
        self.assertIn('滿10年為16日',entries['TW-19-002']['body'])
        self.assertIn('40,000×0.5×2.5＝50,000',entries['TW-19-004']['body'])
        self.assertIn('20×1,100＝22,000',entries['TW-19-005']['body'])
        self.assertIn('通知次日起按曆日',entries['TW-19-005']['body'])
        self.assertEqual(40000*.5*2.5,50000);self.assertEqual(20*1100,22000)

    def test_legal_qualifications_cannot_be_omitted(self):
        entries={e['id']:e for e in validate_runtime()['items']}
        required={
          'TW-19-003':['未滿3個月不代表','2026-01-01'],
          'TW-19-006':['不是申請即獲准','免費勞資爭議調解'],
          'TW-19-017':['經公立就業服務機構同意','七日補正'],
          'TW-19-022':['達50%不等於','最長2年','禁止預扣'],
          'TW-19-024':['經主管機關處罰或限期給付','90日','10日','30日']}
        for key,phrases in required.items():
            for phrase in phrases:self.assertIn(phrase,entries[key]['body'])

    def test_existing_ch14_regressions_allow_later_chapter_progress(self):
        import test_ch14_content as old
        old.ChapterContentTests('test_supplemental_medical_items_not_rewritten').test_supplemental_medical_items_not_rewritten()
        old.ChapterContentTests('test_core_metadata_preserves_upstream_provenance').test_core_metadata_preserves_upstream_provenance()
        old.ChapterContentTests('test_complete_core_chapter_with_evidence').test_complete_core_chapter_with_evidence()

if __name__=='__main__':unittest.main()

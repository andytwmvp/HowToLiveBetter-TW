"""第19章補完：實際正文、來源、生效時間界線及舊資料保全。"""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from body_renderer import body_blocks
from retroactive_audit import assert_preserved_or_rechecked
from review_contract import ROOT, validate_runtime, validate_entry, publication_report
from ci_language_policy import audit_drafts
from reader_copy_test_support import assert_professional_review_pending
BASE='c2472e69a50b9585b1a9e58576b0654fa238e3e2'
NEW_IDS={f'TW-19-{n:03}' for n in (9,10,11,12,13,14,15,16,18,19,21)}
ALL_IDS={f'TW-19-{n:03}' for n in range(1,25)}
def read(path):return json.loads((ROOT/path).read_text(encoding='utf-8'))
def before(path):return json.loads(subprocess.check_output(['git','show',BASE+':'+path],cwd=ROOT,text=True))

class Chapter19CompletionTests(unittest.TestCase):
    def test_full_chapter_has_exact_ids_and_verified_outputs(self):
        manifest=read('localization/manifest.json')['entries']
        chapter=[e for e in manifest if e['id'] in ALL_IDS]
        self.assertEqual({e['id'] for e in chapter},ALL_IDS)
        runtime={e['id']:e for e in validate_runtime()['items']}
        for item in chapter:
            self.assertTrue(validate_entry(item));self.assertEqual(item['status'],'verified')
            self.assertEqual((ROOT/item['target_path']).read_text(),runtime[item['id']]['body'])
        report=publication_report();self.assertGreaterEqual(report['publication_completed_entries'],36)
        self.assertFalse(report['publication_ready'])

    def test_eleven_bodies_and_review_evidence_match(self):
        batch=read('localization/tw-edition/ch19-completion-reviewed.json')
        runtime={e['id']:e for e in validate_runtime()['items']}
        self.assertEqual({e['id'] for e in batch['entries']},NEW_IDS)
        for item in batch['entries']:
            with self.subTest(id=item['id']):
                entry=runtime[item['id']];review=read('localization/reviews/'+item['id']+'.json')
                self.assertEqual(set(item['source_claims']),set(item['source_ids']))
                self.assertGreater(len(entry['body']),650)
                self.assertEqual(hashlib.sha256(entry['body'].encode()).hexdigest(),review['target_sha256'])
                assert_professional_review_pending(self, review['reviewer'])
                self.assertTrue(all('非逐字引文' in s['supporting_passage'] for s in review['source_checks']))
                self.assertEqual(len([b for b in body_blocks(entry) if b['tag']=='h3']),5)

    def test_old_thirty_four_items_and_sources_preserved(self):
        old=before('localization/tw-edition/runtime.json');new=validate_runtime()
        ids={e['id'] for e in old['items']};sources={s['id'] for s in old['sources']}
        current=[e for e in new['items'] if e['id'] in ids]
        self.assertEqual([e['id'] for e in old['items']],[e['id'] for e in current])
        for previous,item in zip(old['items'],current,strict=True):assert_preserved_or_rechecked(self,previous,item)
        self.assertEqual(old['sources'],[s for s in new['sources'] if s['id'] in sources])
        self.assertEqual(len(old['items']),34)

    def test_sources_registered_without_claiming_other_drafts_reviewed(self):
        batch=read('localization/tw-edition/ch19-completion-reviewed.json')
        registry={r[0]:r for r in read('localization/tw-edition/sources/ch19-completion.json')['sources']}
        sources={s['id']:s for s in validate_runtime()['sources']}
        self.assertEqual(len(registry),20)
        for source in batch['sources']:
            self.assertEqual(registry[source['id']][2],source['url'])
            self.assertEqual(sources[source['id']],source)
            self.assertIn('不代表其他草稿',source['scope_note'])
        for item in batch['entries']:
            self.assertTrue(set(item['source_ids']).issubset(sources))

    def test_health_rules_distinguish_delayed_effective_date(self):
        rows={e['id']:e for e in validate_runtime()['items']};body=rows['TW-19-009']['body']
        for phrase in ('65歲以上每年','40至64歲每3年','未滿40歲每5年','2028-01-01','60歲以上每年','40至59歲每2年','未滿40歲每3年'):
            self.assertIn(phrase,body)
        self.assertIn('LawOldVer.aspx',body)
        self.assertIn('到職前',body);self.assertIn('僱主負擔',body)

    def test_insurance_and_employer_responsibilities_remain_separate(self):
        rows={e['id']:e for e in validate_runtime()['items']}
        for key,phrases in {
            'TW-19-011':['第4日','前2個月','70%','最長2年','5年','2年','前3日'],
            'TW-19-013':['不以員工滿5人','第28條','不屬該強制類別','不能倒填'],
            'TW-19-014':['70%、50%、20%','2009年','身心障礙證明','不得同領'],
            'TW-19-015':['5個月平均工資','40個月平均工資','不等於保險各項都無條件'],
            'TW-19-019':['7日','不是可以少算','眷屬'],
            'TW-19-021':['不必然違法','罰鍰不會自動發給你','不能保證']}.items():
            for phrase in phrases:self.assertIn(phrase,rows[key]['body'])

    def test_bullying_effectiveness_and_scope_specific_deadlines(self):
        row=next(e for e in validate_runtime()['items'] if e['id']=='TW-19-016')
        for phrase in ('2026-07-01','情節重大','10人以上','30人以上','最高負責人','逾3年','離職起1年','不是所有內部申訴','1925'):
            self.assertIn(phrase,row['body'])

    def test_tax_example_is_income_not_tax_and_uses_correct_year(self):
        row=next(e for e in validate_runtime()['items'] if e['id']=='TW-19-018')
        for phrase in ('115年度','206,000','414,000','894,000','2027年','191,000元不是稅額'):
            self.assertIn(phrase,row['body'])
        years=3;received=1_000_000;low=206_000*years;high=414_000*years
        income=max(min(received,high)-low,0)/2+max(received-high,0)
        self.assertEqual(income,191_000)

    def test_progress_counts_topics_once_and_retains_original_metadata(self):
        old=before('localization/manifest.json')['entries'];new=read('localization/manifest.json')['entries']
        for a,b in zip(old,new,strict=True):
            for key in ('id','upstream_chapter','upstream_item','upstream_commit','upstream_text_sha256','upstream_path_uri','display_path'):
                self.assertEqual(a[key],b[key])
        report=audit_drafts();self.assertEqual(report['original_entries'],765)
        self.assertEqual(report['unique_draft_entries']+report['entries_without_any_draft'],765)
        self.assertGreaterEqual(report['unique_draft_entries'],388)
        old_chapter=before('localization/tw-edition/chapters/19.json')
        self.assertTrue(NEW_IDS.issubset({f'TW-19-{r[0]:03}' for r in old_chapter['entries']}))

if __name__=='__main__':unittest.main()

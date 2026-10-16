"""第25章來源與閱讀契約回歸；不把關鍵字或CI當成法律簽證。"""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from body_renderer import body_blocks
from content_validation import load_json
from review_contract import ROOT,validate_runtime,validate_entry
from ci_language_policy import audit_drafts
BASE='3d010bccdb5f86304c34b454977d65ecb990443a'
IDS={f'TW-25-{n:03}' for n in range(1,13)}
def read(path):return load_json(ROOT/path)
def old(path):return json.loads(subprocess.check_output(['git','show',BASE+':'+path],cwd=ROOT,text=True))
def bodies():return {e['id']:e['body'] for e in validate_runtime()['items']}
class AfterDeathChapterTests(unittest.TestCase):
    def test_all_12_bodies_reviews_and_runtime_match(self):
        runtime={e['id']:e for e in validate_runtime()['items']}
        entries=[e for e in read('localization/manifest.json')['entries'] if e['id'] in IDS]
        self.assertEqual({e['id'] for e in entries},IDS)
        for e in entries:
            with self.subTest(id=e['id']):
                self.assertEqual(e['status'],'verified');self.assertTrue(validate_entry(e))
                raw=(ROOT/e['target_path']).read_bytes();review=read(f"localization/reviews/{e['id']}.json")
                self.assertEqual(raw.decode(),runtime[e['id']]['body']);self.assertGreater(len(raw.decode()),850)
                self.assertEqual(review['target_sha256'],hashlib.sha256(raw).hexdigest())
                self.assertIn('AI',review['reviewer']);self.assertIn('非獨立',review['reviewer'])
                blocks=body_blocks(runtime[e['id']]);self.assertEqual(sum(b['tag']=='h3' for b in blocks),5)
                self.assertEqual(sum('url' in b for b in blocks),len(runtime[e['id']]['source_ids']))
    def test_baseline_items_sources_and_original_provenance_preserved(self):
        previous=old('localization/tw-edition/runtime.json');current=validate_runtime()
        items={e['id']:e for e in current['items']};sources={s['id']:s for s in current['sources']}
        self.assertEqual(len(previous['items']),70)
        for e in previous['items']:self.assertEqual(e,items[e['id']])
        for s in previous['sources']:self.assertEqual(s,sources[s['id']])
        fields=('id','upstream_chapter','upstream_item','upstream_commit','upstream_text_sha256','upstream_path_uri','source_title_zh_tw','display_path')
        before=old('localization/manifest.json')['entries'];after=read('localization/manifest.json')['entries']
        self.assertEqual(len(after),765)
        for a,b in zip(before,after,strict=True):
            for f in fields:self.assertEqual(a[f],b[f])
            if a['id'] not in IDS:self.assertEqual(a,b)
    def test_sources_claims_retrieval_methods_and_registry_agree(self):
        batch=read('localization/ch25-batch.json');runtime={s['id']:s for s in validate_runtime()['sources']}
        registry={s[0]:s for s in read('localization/tw-edition/sources/17-after-death.json')['sources']}
        self.assertEqual(len(batch['sources']),27);self.assertEqual(set(registry),{s['id'] for s in batch['sources']})
        for s in batch['sources']:
            self.assertEqual(runtime[s['id']],s);self.assertEqual(registry[s['id']][2],s['url'])
            self.assertGreater(len(s['retrieval_method']),15)
        for e in batch['entries']:
            self.assertEqual(set(e['source_ids']),set(e['source_claims']))
            review=read(f"localization/reviews/{e['id']}.json")
            self.assertEqual({s['url'] for s in review['source_checks']},{runtime[s]['url'] for s in e['source_ids']})
            self.assertTrue(all('非逐字引文' in s['supporting_passage'] for s in review['source_checks']))
    def test_existing_topics_not_double_counted_or_full_publication_claimed(self):
        data=audit_drafts()
        self.assertGreaterEqual(data['publication_completed_entries'],73);self.assertFalse(data['publication_ready'])
        self.assertGreaterEqual(data['unique_draft_entries'],410)
        self.assertEqual(data['unique_draft_entries']+data['entries_without_any_draft'],765)
        previous=old('localization/tw-edition/chapters/25.json')
        self.assertEqual({f'TW-25-{e[0]:03}' for e in previous['entries']},IDS)
        self.assertEqual(previous,read('localization/tw-edition/chapters/25.json'))
    def test_emergency_documents_and_judicial_authority_not_conflated(self):
        texts=bodies()
        requirements={1:['119','現場安全','可疑非病死'],2:['正本','不歸還','境外'],4:['第217條','不等於','不是每件相驗都一定解剖'],5:['30日','自然人憑證','完成通知']}
        for n,phrases in requirements.items():
            for phrase in phrases:self.assertIn(phrase,texts[f'TW-25-{n:03}'])
    def test_public_facility_relief_and_complaint_deadline_are_limited(self):
        texts=bodies()
        for phrase in ('2026-01-01','中低收入戶','公立','私立','櫃位','全部費用'):self.assertIn(phrase,texts['TW-25-006'])
        for phrase in ('15日','不是退款保證','75%','生前契約'):self.assertIn(phrase,texts['TW-25-007'])
    def test_beneficiaries_and_digital_access_do_not_mean_estate_or_unlock(self):
        texts=bodies()
        for phrase in ('支出殯葬費','指定受益人','不作為','不是所有項目'):self.assertIn(phrase,texts['TW-25-009'])
        for phrase in ('申領密鑰','iCloud鑰匙圈','不清除資料','現生存自然人','Google'):self.assertIn(phrase,texts['TW-25-010'])
    def test_distinct_deadlines_inventory_and_common_ownership(self):
        texts=bodies()
        for phrase in ('知悉自己得繼承起3個月','住所地法院','清冊不是拋棄繼承','第1162條之2'):self.assertIn(phrase,texts['TW-25-011'])
        for phrase in ('死亡日起6個月','死亡日起3個月','所得稅','公同共有','不代表登記自動展延','第41條之1'):self.assertIn(phrase,texts['TW-25-012'])
    def test_browser_wired_and_temporary_integrator_removed(self):
        code=(ROOT/'tools/tw/assets_and_browser.py').read_text()
        for name in ('check_navigation','check_ch23_browser','check_ch25_browser'):self.assertIn(f'{name}(page,context,url,review)',code)
        for path in ('tools/tw/apply_ch25.py','.github/workflows/ch25-integrate.yml'):self.assertFalse((ROOT/path).exists())
        self.assertFalse(list((ROOT/'tools/tw').glob('ch25-input-*.json')))
if __name__=='__main__':unittest.main()

"""第23章內容、取材與閱讀一致性；不把工程檢查當專業或全文簽證。"""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from body_renderer import body_blocks
from content_validation import load_json
from retroactive_audit import assert_preserved_or_rechecked
from review_contract import ROOT,validate_runtime,validate_entry
from ci_language_policy import audit_drafts
BASE='0c76f150b5979378e04c0fe79bf828f8de460236'
IDS={f'TW-23-{n:03}' for n in range(1,26)}
def read(path):return load_json(ROOT/path)
def old(path):return json.loads(subprocess.check_output(['git','show',BASE+':'+path],cwd=ROOT,text=True))

class SkillsChapterTests(unittest.TestCase):
    def test_all_25_ids_match_bodies_reviews_and_shared_runtime(self):
        runtime={e['id']:e for e in validate_runtime()['items']}
        entries=[e for e in read('localization/manifest.json')['entries'] if e['id'] in IDS]
        self.assertEqual({e['id'] for e in entries},IDS)
        for e in entries:
            with self.subTest(id=e['id']):
                self.assertEqual(e['status'],'verified');self.assertTrue(validate_entry(e))
                body=(ROOT/e['target_path']).read_bytes();review=read(f"localization/reviews/{e['id']}.json")
                self.assertEqual(body.decode(),runtime[e['id']]['body']);self.assertGreater(len(body.decode()),650)
                self.assertEqual(review['target_sha256'],hashlib.sha256(body).hexdigest())
                self.assertIn('AI',review['reviewer']);self.assertIn('獨立',review['reviewer'])
                self.assertEqual(sum(b['tag']=='h3' for b in body_blocks(runtime[e['id']])),5)
                self.assertTrue(all('非逐字引文' in s['supporting_passage'] for s in review['source_checks']))
    def test_original_provenance_and_old_published_items_are_preserved(self):
        before=old('localization/manifest.json')['entries'];after=read('localization/manifest.json')['entries']
        fields=('id','upstream_chapter','upstream_item','upstream_commit','upstream_text_sha256','upstream_path_uri','source_title_zh_tw','display_path')
        self.assertEqual(len(after),765)
        for a,b in zip(before,after,strict=True):
            for f in fields:self.assertEqual(a[f],b[f])
        previous=old('localization/tw-edition/runtime.json');current=validate_runtime()
        items={e['id']:e for e in current['items']};sources={e['id']:e for e in current['sources']}
        for e in previous['items']:assert_preserved_or_rechecked(self,e,items[e['id']])
        for e in previous['sources']:self.assertEqual(sources[e['id']],e)
    def test_sources_have_matching_registry_claims_and_retrieval_limits(self):
        batch=read('localization/ch23-batch.json');runtime={s['id']:s for s in validate_runtime()['sources']}
        registry={s[0]:s for s in read('localization/tw-edition/sources/16-skills.json')['sources']}
        self.assertEqual(len(batch['sources']),22)
        self.assertEqual({s['id'] for s in batch['sources']}.issubset(registry),True)
        for s in batch['sources']:
            self.assertEqual(runtime[s['id']],s);self.assertEqual(registry[s['id']][2],s['url'])
            self.assertGreater(len(s['retrieval_method']),15)
        supplemental={
            'TW-23-002':{'ch23_taiwan_elder_mortality_2011'},
            'TW-23-003':{'ch23_moi_education_2025_pdf'},
            'TW-23-001':{'ch23_mol_student_inspection_114'},
            'TW-23-004':set(),
            'TW-23-006':{'ch23_mol_initial_salary_114'},
            'TW-23-007':{'ch23_returns_wb_wps8402_pdf','ch23_returns_causal_meta_2026','ch23_returns_comment_2026','ch23_returns_tw_schooling_2020'},
            'TW-23-008':{'ch23_certificate_exam_schedule_current','ch23_cpaexam'},
            'TW-23-009':{'ch23_training_q_and_a_115'},
            'TW-23-005':{'ch23_admission_116_portal_20261027','ch23_admission_116_choices_20260803'},
            'TW-23-011':{'ch23_certificate_exam_schedule_current','ch23_skill_cooking_qualification_20260722'},
            'TW-23-012':{'ch23_vacancies_11506_recheck_20261027','ch23_salary_114_recheck_20261027'},
            'TW-23-021':{'ch23_cpa_act_20260805','ch23_cpa_act_amendment_20260805'},
        }
        register={r['id']:r for r in read('localization/retroactive-review-register-20261019.json')['substantive_rechecks']}
        for e in batch['entries']:
            self.assertEqual(set(e['source_ids']),set(e['source_claims']))
            review=read(f"localization/reviews/{e['id']}.json")
            retired={source['id'] for source in register.get(e['id'],{}).get('retired_sources',[])}
            expected_ids=(set(e['source_ids'])|supplemental.get(e['id'],set()))-retired
            self.assertEqual({s['url'] for s in review['source_checks']},{runtime[s]['url'] for s in expected_ids})
            self.assertTrue(all(len(s['claim'])>15 and len(s['retrieval_method'])>15 for s in review['source_checks']))
    def test_only_22_new_topics_counted_and_publication_still_incomplete(self):
        report=audit_drafts()
        self.assertGreaterEqual(report['unique_draft_entries'],410)
        self.assertEqual(report['unique_draft_entries']+report['entries_without_any_draft'],765)
        self.assertGreaterEqual(report['publication_completed_entries'],61)
        self.assertFalse(report['publication_ready'])
        draft=subprocess.check_output(['git','show',BASE+':locales/zh-TW/book/23-學習技能與職涯發展.md'],cwd=ROOT,text=True)
        import re
        existing=set(re.findall(r'TW-23-\d{3}',draft))
        self.assertEqual(existing,{'TW-23-001','TW-23-008','TW-23-009'});self.assertEqual(len(IDS-existing),22)
    def test_education_data_and_tuition_qualifications_not_flattened(self):
        items={e['id']:e['body'] for e in validate_runtime()['items']}
        for phrase in ('51.4%','81.9%','戶籍人口','大專以上'):self.assertIn(phrase,items['TW-23-003'])
        for phrase in ('重讀','獨立招生','中華民國國籍','雜費'):self.assertIn(phrase,items['TW-23-004'])
    def test_training_is_not_cash_and_cost_example_is_not_forecast(self):
        items={e['id']:e['body'] for e in validate_runtime()['items']}
        for phrase in ('三年','10萬元','80%','100%','開訓日','失業'):self.assertIn(phrase,items['TW-23-009'])
        self.assertIn('320,000÷40,000＝8年',items['TW-23-006']);self.assertEqual(320000/40000,8)
        self.assertIn('純假設',items['TW-23-006']);self.assertIn('零或負數',items['TW-23-006'])
    def test_research_boundaries_and_effect_measures_are_explicit(self):
        items={e['id']:e['body'] for e in validate_runtime()['items']}
        requirements={2:['相對風險','百分點','因果'],7:['9%','不是銀行利率'],10:['暴露','不等於裁員率'],14:['標準化效果量','百分比'],17:['單字','區塊'],18:['無障礙','2009-12-01'],19:['遷移','不能'],25:['異質性','臨床診斷']}
        for n,phrases in requirements.items():
            for phrase in phrases:self.assertIn(phrase,items[f'TW-23-{n:03}'])
    def test_legal_paths_and_not_yet_effective_degree_rules_are_separate(self):
        items={e['id']:e['body'] for e in validate_runtime()['items']}
        for phrase in ('15歲','16歲','18歲','20:00','06:00'):self.assertIn(phrase,items['TW-23-001'])
        for phrase in ('甲','乙','丙','單一級'):self.assertIn(phrase,items['TW-23-011'])
        for phrase in ('記帳士','會計師','執業'):self.assertIn(phrase,items['TW-23-021'])
        for n in (22,24,25):
            self.assertIn('第4條',items[f'TW-23-{n:03}']);self.assertIn('第5條第1項',items[f'TW-23-{n:03}'])
    def test_browser_extension_is_wired_without_removing_existing_checks(self):
        code=(ROOT/'tools/tw/assets_and_browser.py').read_text()
        self.assertIn('check_navigation(page,context,url,review)',code)
        self.assertIn('check_ch23_browser(page,context,url,review)',code)
        for path in ['.github/workflows/ch23-integrate.yml','tools/tw/apply_ch23.py']:
            self.assertFalse((ROOT/path).exists())
        self.assertFalse(list((ROOT/'tools/tw').glob('ch23-input-*.json')))
if __name__=='__main__':unittest.main()

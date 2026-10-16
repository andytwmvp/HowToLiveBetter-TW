"""第7章來源及閱讀契約回歸；不是福利核定或法律專業審閱。"""
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
BASE='4dfb5f7b92c7e3c06863d52d1b5f77fb4eee2900'
INTEGRATED=None  # 隔離整合通過提交後，替換成該固定SHA供歷史保全測試。
IDS={f'TW-07-{n:03}' for n in range(1,24)}
def read(path):return load_json(ROOT/path)
def at(ref,path):return json.loads(subprocess.check_output(['git','show',ref+':'+path],cwd=ROOT,text=True))
def snapshot(path):return at(INTEGRATED,path) if INTEGRATED else read(path)
def bodies():return {e['id']:e['body'] for e in validate_runtime()['items']}
class LivingSupportChapterTests(unittest.TestCase):
 def test_23_independent_bodies_reviews_and_runtime_match(self):
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
 def test_original_provenance_and_all_prior_runtime_preserved_at_integration(self):
  previous=at(BASE,'localization/tw-edition/runtime.json');integrated=snapshot('localization/tw-edition/runtime.json')
  items={e['id']:e for e in integrated['items']};sources={s['id']:s for s in integrated['sources']}
  self.assertEqual(len(previous['items']),82)
  for e in previous['items']:self.assertEqual(e,items[e['id']])
  for s in previous['sources']:self.assertEqual(s,sources[s['id']])
  before=at(BASE,'localization/manifest.json')['entries'];current=read('localization/manifest.json')['entries']
  frozen={e['id']:e for e in snapshot('localization/manifest.json')['entries']}
  for a,b in zip(before,current,strict=True):
   for f in ('id','upstream_chapter','upstream_item','upstream_commit','upstream_text_sha256','upstream_path_uri','source_title_zh_tw','display_path'):self.assertEqual(a[f],b[f])
   if a['id'] not in IDS:self.assertEqual(a,frozen[a['id']])
  self.assertEqual(at(BASE,'localization/tw-edition/chapters/07.json'),snapshot('localization/tw-edition/chapters/07.json'))
 def test_36_sources_methods_and_claims_not_just_ids(self):
  batch=read('localization/ch07-batch.json');runtime={s['id']:s for s in validate_runtime()['sources']}
  registry={s[0]:s for s in read('localization/tw-edition/sources/18-living-support.json')['sources']}
  self.assertEqual(len(batch['sources']),36);self.assertEqual(set(registry),{s['id'] for s in batch['sources']})
  for s in batch['sources']:
   self.assertEqual(runtime[s['id']],s);self.assertEqual(registry[s['id']][2],s['url'])
   self.assertGreater(len(s['supports']),25);self.assertGreater(len(s['retrieval_method']),15)
  for e in batch['entries']:
   self.assertEqual(set(e['source_ids']),set(e['source_claims']))
   review=read(f"localization/reviews/{e['id']}.json")
   self.assertEqual({s['url'] for s in review['source_checks']},{runtime[s]['url'] for s in e['source_ids']})
   self.assertTrue(all('非逐字引文' in s['supporting_passage'] for s in review['source_checks']))
 def test_counts_are_real_not_new_draft_duplicates(self):
  data=audit_drafts()
  self.assertGreaterEqual(data['publication_completed_entries'],96)
  self.assertGreaterEqual(data['unique_draft_entries'],410)
  self.assertEqual(data['unique_draft_entries']+data['entries_without_any_draft'],765)
  if data['publication_completed_entries']<765:self.assertFalse(data['publication_ready'])
  previous=at(BASE,'localization/tw-edition/chapters/07.json')
  self.assertEqual({f'TW-07-{e[0]:03}' for e in previous['entries']},IDS)
 def test_unemployment_qualification_and_training_not_conflated(self):
  texts=bodies()
  for phrase in ('3年','滿1年','14日','第25條','2年','60%','第23條','返還'):self.assertIn(phrase,texts['TW-07-001'])
  for phrase in ('100小時','60%','最長6個月','不得與失業給付同時','另有工作'):self.assertIn(phrase,texts['TW-07-013'])
 def test_urgent_aid_and_hotline_scope(self):
  texts=bodies()
  for phrase in ('戶籍地','居住地','2026-06-24','1至3萬元','5000元','核定後','不是每人'):self.assertIn(phrase,texts['TW-07-006'])
  for n in (4,21):
   for phrase in ('08:00至22:00','119','110'):self.assertIn(phrase,texts[f'TW-07-{n:03}'])
 def test_household_income_not_only_self_salary(self):
  text=bodies()['TW-07-007']
  for phrase in ('基本工資','55歲','三次','全日制','其他收入','不同戶籍','假分戶'):self.assertIn(phrase,text)
 def test_health_and_rent_limits_and_approval(self):
  texts=bodies()
  for phrase in ('戶籍地','分期','貸款','償還','不是'):self.assertIn(phrase,texts['TW-07-009'])
  for phrase in ('相關','部分負擔','不代表','自費'):self.assertIn(phrase,texts['TW-07-010'])
  for phrase in ('2026-12-31 17:00','同址','新申請','換址','拒絕連線','正式送出'):self.assertIn(phrase,texts['TW-07-016'])
 def test_labor_and_debt_procedures_preserve_limits(self):
  texts=bodies()
  for phrase in ('從屬性','不受契約名稱','不是勾一項','民事'):self.assertIn(phrase,texts['TW-07-022'])
  for phrase in ('第151條','最大債權金融機構','鄉鎮市區','免責','不脫產'):self.assertIn(phrase,texts['TW-07-023'])
  for phrase in ('刑事更生保護','消費者債務更生','本人意願'):self.assertIn(phrase,texts['TW-07-019'])
 def test_insurance_and_pension_distinct(self):
  texts=bodies()
  for phrase in ('25歲','未滿65歲','退休金','不是'):self.assertIn(phrase,texts['TW-07-018'])
  for phrase in ('第64條','第127條','過二年','不是','等待期'):self.assertIn(phrase,texts['TW-07-020'])
 def test_browser_hook_and_no_ephemeral_writers(self):
  code=(ROOT/'tools/tw/assets_and_browser.py').read_text()
  for name in ('check_navigation','check_ch23_browser','check_ch25_browser','check_ch07_browser'):self.assertIn(f'{name}(page,context,url,review)',code)
  for path in ('tools/tw/apply_ch07.py','.github/workflows/ch07-integrate.yml','.github/workflows/ch07-source-snapshot.yml'):self.assertFalse((ROOT/path).exists())
if __name__=='__main__':unittest.main()

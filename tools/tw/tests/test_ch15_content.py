"""第15章整合與錯誤推論回歸；不代替個案法律、建築或核貸判斷。"""
import hashlib
import json
import subprocess
import sys
from pathlib import Path
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from content_validation import load_json
from review_contract import ROOT,validate_runtime,validate_entry
from body_renderer import body_blocks
from ci_language_policy import audit_drafts
BASE='8607d4dbcaf6bd54a891b227faa0f0b3f711409d'
INTEGRATED='6eb1e418183b46f7174edc3595dcee5f8e0caef0'  # 固定本次初始整合保全，不凍結後續正文修訂。
IDS={f'TW-15-{n:03}' for n in range(1,19)}
def read(path):return load_json(ROOT/path)
def at(ref,path):return json.loads(subprocess.check_output(['git','show',ref+':'+path],cwd=ROOT,text=True))
def snapshot(path):return at(INTEGRATED,path)
def bodies():return {e['id']:e['body'] for e in validate_runtime()['items']}
class HousingChapterTests(unittest.TestCase):
 def test_all_18_bodies_reviews_and_runtime(self):
  runtime={e['id']:e for e in validate_runtime()['items']}
  rows=[e for e in read('localization/manifest.json')['entries'] if e['id'] in IDS]
  self.assertEqual({e['id'] for e in rows},IDS)
  for e in rows:
   with self.subTest(id=e['id']):
    self.assertEqual(e['status'],'verified');self.assertTrue(validate_entry(e))
    raw=(ROOT/e['target_path']).read_bytes();review=read(f"localization/reviews/{e['id']}.json")
    self.assertEqual(raw.decode(),runtime[e['id']]['body']);self.assertGreater(len(raw.decode()),850)
    self.assertEqual(review['target_sha256'],hashlib.sha256(raw).hexdigest())
    self.assertIn('AI',review['reviewer']);self.assertIn('非獨立',review['reviewer'])
    blocks=body_blocks(runtime[e['id']])
    self.assertGreaterEqual(sum(b['tag']=='h3' for b in blocks),5)
    self.assertEqual(sum('url' in b for b in blocks),len(runtime[e['id']]['source_ids']))
 def test_existing_105_items_and_old_registry_preserved(self):
  before=at(BASE,'localization/tw-edition/runtime.json');now=snapshot('localization/tw-edition/runtime.json')
  items={e['id']:e for e in now['items']};sources={s['id']:s for s in now['sources']}
  self.assertEqual(len(before['items']),105)
  for e in before['items']:self.assertEqual(e,items[e['id']])
  for s in before['sources']:self.assertEqual(s,sources[s['id']])
  self.assertEqual(at(BASE,'localization/tw-edition/chapters/15.json'),snapshot('localization/tw-edition/chapters/15.json'))
  old=at(BASE,'localization/manifest.json')['entries'];new=snapshot('localization/manifest.json')['entries']
  for a,b in zip(old,new,strict=True):
   for field in ('id','upstream_text_sha256','upstream_path_uri','upstream_commit','display_path'):self.assertEqual(a[field],b[field])
   if a['id'] not in IDS:self.assertEqual(a,b)
 def test_sources_and_retrieval_scope(self):
  batch=read('localization/ch15-batch.json');all_sources={s['id']:s for s in validate_runtime()['sources']}
  current_items={row['id']:row for row in validate_runtime()['items']}
  register=read('localization/retroactive-review-register-20261019.json')
  records={row['id']:row for row in register['substantive_rechecks']}
  new=read('localization/tw-edition/sources/19-housing.json')['sources']
  self.assertEqual(len(batch['sources']),22);self.assertEqual(len(new),14)
  for s in batch['sources']:
   self.assertEqual(s,all_sources[s['id']]);self.assertGreater(len(s['supports']),20)
   self.assertGreater(len(s['retrieval_method']),20)
  for e in batch['entries']:
   self.assertEqual(set(e['source_ids']),set(e['source_claims']))
   review=read(f"localization/reviews/{e['id']}.json");checks=review['source_checks']
   current_ids=set(current_items[e['id']]['source_ids'])
   retired_ids={row['id'] for row in records.get(e['id'],{}).get('retired_sources',[])}
   historical_ids=set(e['source_ids'])
   # Old source objects stay registered, while citations no longer supporting
   # the current article must have an explicit replacement and retirement record.
   self.assertTrue(historical_ids.issubset(current_ids|retired_ids))
   self.assertTrue(retired_ids.issubset(historical_ids))
   self.assertEqual({all_sources[k]['url'] for k in current_ids},{c['url'] for c in checks})
   self.assertTrue(all('非逐字引文' in c['supporting_passage'] for c in checks))
 def test_counts_without_duplicate_draft_progress(self):
  data=audit_drafts()
  self.assertGreaterEqual(data['publication_completed_entries'],114)
  self.assertEqual(data['unique_draft_entries']+data['entries_without_any_draft'],765)
  self.assertEqual({f'TW-15-{e[0]:03}' for e in at(BASE,'localization/tw-edition/chapters/15.json')['entries']},IDS)
  if data['publication_completed_entries']<765:self.assertFalse(data['publication_ready'])
 def test_tenancy_roles_and_termination_exceptions(self):
  texts=bodies()
  for s in ('二個月','第18點','提前通知','扣款'):self.assertIn(s,texts['TW-15-001'])
  for s in ('代管','包租','授權'):self.assertIn(s,texts['TW-15-003'])
  for s in ('公證','五年','未定期限','抵押'):self.assertIn(s,texts['TW-15-005'])
 def test_mortgage_difference_not_total_price(self):
  text=bodies()['TW-15-011']
  for s in ('第18點','預定貸款','30%','7年','第249條','至少30日'):self.assertIn(s,text)
  self.assertIn('不是房地總價',text)
 def test_area_and_material_exceptions(self):
  text=bodies()['TW-15-012']
  for s in ('不足','全部找補','2%','超過3%','扣除車位','不可歸責','補償價金'):self.assertIn(s,text)
 def test_dates_and_retention_are_distinct(self):
  texts=bodies()
  for s in ('備妥文件','通知','已繳房地價款','萬分之五'):self.assertIn(s,texts['TW-15-013'])
  self.assertTrue('4個月' in texts['TW-15-013'] or '四個月' in texts['TW-15-013'])
  self.assertTrue('6個月' in texts['TW-15-013'] or '六個月' in texts['TW-15-013'])
  for s in ('房地總價5%','自備款','複驗','15年','1年','第365條','6個月','5年','不是所有'):self.assertIn(s,texts['TW-15-018'])
 def test_farm_and_caution_registration_not_guarantees(self):
  texts=bodies()
  for s in ('0.25公頃','2年','不是','原地主'):self.assertIn(s,texts['TW-15-009'])
  for s in ('第79條之1','同意','徵收','強制執行','不會讓買方取得產權'):self.assertIn(s,texts['TW-15-014'])
 def test_loan_cost_and_current_policy(self):
  texts=bodies()
  for s in ('總費用年百分率','3年','24個月','不是市場報價'):self.assertIn(s,texts['TW-15-015'])
  for s in ('3.0','2026-08-01','2029-07-31','未滿50歲','200萬元','40年','3+3','最高'):self.assertIn(s,texts['TW-15-016'])
  self.assertIn('不是整段40年',texts['TW-15-016'])
 def test_hooks_and_no_one_shot_writers(self):
  code=(ROOT/'tools/tw/assets_and_browser.py').read_text()
  for hook in ('check_navigation','check_ch07_browser','check_ch23_browser','check_ch25_browser','check_ch15_browser'):
   self.assertIn(f'{hook}(page,context,url,review)',code)
  for path in ('tools/tw/apply_ch15.py','.github/workflows/ch15-integrate.yml','.github/workflows/ch15-snapshot.yml','.github/workflows/ch15-review-snapshot.yml','.github/workflows/ch15-final-review.yml','tools/tw/apply_ch15_final_review.py'):
   self.assertFalse((ROOT/path).exists())
 def test_case_facts_are_not_rewritten_as_fee_collection(self):
  text=bodies()['TW-15-017']
  for phrase in ('外牆鐵窗','不是欠管理費案件','第21條'):self.assertIn(phrase,text)
  self.assertNotIn('限制欠費住戶門禁的爭議案例',text)
  batch=read('localization/ch15-batch.json')
  entry=next(e for e in batch['entries'] if e['id']=='TW-15-017')
  self.assertIn('不是欠管理費',entry['source_claims']['condopowers'])
  review=read('localization/reviews/TW-15-017.json')
  self.assertTrue(any('不是欠管理費' in s['claim'] for s in review['source_checks']))
 def test_loan_shortfall_choices_retain_contract_scope(self):
  text=bodies()['TW-15-011']
  for phrase in ('買賣雙方得選擇','雙方均不可歸責','不得少於7年'):self.assertIn(phrase,text)
  self.assertNotIn('所有核貸不足均可任意取消',text)
  self.assertNotIn('買方得選依原承諾利率',text)
  review=read('localization/reviews/TW-15-011.json')
  self.assertTrue(any('雙方均不可歸責' in s['claim'] for s in review['source_checks']))
if __name__=='__main__':unittest.main()

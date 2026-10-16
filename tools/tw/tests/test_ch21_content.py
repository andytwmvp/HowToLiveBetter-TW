"""第21章的正文整合與錯誤推論回歸；不代替實際入出境、法律或醫療審認。"""
import hashlib,json,subprocess,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from review_contract import ROOT,validate_runtime,validate_entry
from content_validation import load_json
from ci_language_policy import audit_drafts
from body_renderer import body_blocks
BASE='5b9341aba7d85ab00a9602ebaa34f97cc9a362c1'
INTEGRATED=None  # 合併前固定本次整合SHA，不限制日後其他章節推進。
IDS={f'TW-21-{n:03}' for n in range(1,14)}
def read(p):return load_json(ROOT/p)
def at(ref,p):return json.loads(subprocess.check_output(['git','show',ref+':'+p],cwd=ROOT,text=True))
def integrated(p):return at(INTEGRATED,p) if INTEGRATED else read(p)
def bodies():return {e['id']:e['body'] for e in validate_runtime()['items']}
class TravelChapterTests(unittest.TestCase):
 def test_thirteen_bodies_reviews_and_rendered_sources(self):
  runtime={e['id']:e for e in validate_runtime()['items']}
  rows=[e for e in read('localization/manifest.json')['entries'] if e['id'] in IDS]
  self.assertEqual({e['id'] for e in rows},IDS)
  for e in rows:
   with self.subTest(id=e['id']):
    self.assertTrue(validate_entry(e));self.assertEqual(e['status'],'verified')
    raw=(ROOT/e['target_path']).read_bytes();body=raw.decode();item=runtime[e['id']]
    review=read(f"localization/reviews/{e['id']}.json")
    self.assertEqual(body,item['body']);self.assertGreater(len(body),850)
    self.assertEqual(hashlib.sha256(raw).hexdigest(),review['target_sha256'])
    self.assertIn('AI',review['reviewer']);self.assertIn('非獨立',review['reviewer'])
    blocks=body_blocks(item);self.assertEqual(sum(b['tag']=='h3' for b in blocks),5)
    self.assertEqual(sum('url' in b for b in blocks),len(item['source_ids']))
 def test_previous_content_and_provenance_preserved(self):
  before=at(BASE,'localization/tw-edition/runtime.json');after=integrated('localization/tw-edition/runtime.json')
  self.assertEqual(len(before['items']),123)
  for field in ('items','sources'):
   actual={e['id']:e for e in after[field]}
   for entry in before[field]:self.assertEqual(entry,actual[entry['id']])
  original=at(BASE,'localization/manifest.json')['entries'];current=integrated('localization/manifest.json')['entries']
  for a,b in zip(original,current,strict=True):
   for key in ('id','upstream_commit','upstream_text_sha256','upstream_path_uri','display_path'):self.assertEqual(a[key],b[key])
   if a['id'] not in IDS:self.assertEqual(a,b)
 def test_twenty_sources_and_per_claim_review(self):
  batch=read('localization/ch21-batch.json');runtime={s['id']:s for s in validate_runtime()['sources']}
  registry=read('localization/tw-edition/sources/20-travel-safety.json')['sources']
  self.assertEqual(len(batch['sources']),20);self.assertEqual(len(registry),20)
  for s in batch['sources']:
   self.assertEqual(s,runtime[s['id']]);self.assertGreater(len(s['supports']),30)
   self.assertIn('HTML',s['retrieval_method']);self.assertEqual(s['accessed_at'],'2026-10-17')
  for e in batch['entries']:
   self.assertEqual(set(e['source_ids']),set(e['source_claims']))
   checks=read(f"localization/reviews/{e['id']}.json")['source_checks']
   self.assertEqual({c['url'] for c in checks},{runtime[s]['url'] for s in e['source_ids']})
   self.assertTrue(all('非逐字引文' in c['supporting_passage'] for c in checks))
 def test_new_topics_not_counted_as_navigation(self):
  data=audit_drafts();self.assertGreaterEqual(data['publication_completed_entries'],127)
  self.assertGreaterEqual(data['unique_draft_entries'],423)
  self.assertEqual(data['unique_draft_entries']+data['entries_without_any_draft'],765)
  if data['publication_completed_entries']<765:self.assertFalse(data['publication_ready'])
  prior=at(BASE,'localization/manifest.json')['entries']
  self.assertTrue(all(e['status']!='verified' and not e['target_path'] for e in prior if e['id'] in IDS))
 def test_warnings_not_refund_or_entry_guarantees(self):
  t=bodies()['TW-21-001']
  for value in ('灰色','黃色','橙色','紅色','不直接','未列警示','陸委會','保險'):self.assertIn(value,t)
 def test_phone_costs_and_loan_exceptions(self):
  texts=bodies();t=texts['TW-21-002']
  for value in ('0800-085-095','+886-800-085-095','自付國際電話費','800-0885-0885','eSIM'):self.assertIn(value,t)
  t=texts['TW-21-003']
  for value in ('借款','償還','危及生命','不能','法院'):self.assertIn(value,t)
 def test_medical_reimbursement_and_cash_distinct(self):
  t=bodies()['TW-21-004']
  for value in ('出院日起6個月','不是返臺日起算','上限','後送','不會'):self.assertIn(value,t)
  t=bodies()['TW-21-006']
  for value in ('每人每次','美金1萬元','新臺幣10萬元','人民幣2萬元','超額即使申報','金融卡','預借現金'):self.assertIn(value,t)
 def test_passport_and_driving_exceptions(self):
  t=bodies()['TW-21-007']
  for value in ('不受理','遺失護照說明書','入國證明書','轉機','不保證'):self.assertIn(value,t)
  t=bodies()['TW-21-008']
  for value in ('三年','日文譯本','入境日起一年','較短','再入境','交車'):self.assertIn(value,t)
 def test_agent_invitation_and_jobscam_limits(self):
  t=bodies()['TW-21-009']
  for value in ('非觀光','許可','註冊','退款','不實'):self.assertIn(value,t)
  t=bodies()['TW-21-010']
  for value in ('B類','不是必備','不能','空白','冒用'):self.assertIn(value,t)
  self.assertIn('不把所有海外合法職缺都判為犯罪',bodies()['TW-21-005'])
 def test_contacts_and_medicine_scopes(self):
  t=bodies()['TW-21-011']
  for value in ('可信任','不必一定是家人','不是','24或48','最後位置'):self.assertIn(value,t)
  t=bodies()['TW-21-012']
  for value in ('至少14日前','三個月','兩週','轉機','禁止','不自行停藥'):self.assertIn(value,t)
 def test_quarantine_not_blanket_original_list(self):
  t=bodies()['TW-21-013']
  for value in ('新鮮果實','土壤','非疫區','申報','不會把禁止輸入物變成合法','未取得舊版參考表PDF','免稅不是免檢疫'):self.assertIn(value,t)
  self.assertNotIn('乳製品一律禁止',t)
 def test_browser_hook_and_no_one_shot_writers(self):
  t=(ROOT/'tools/tw/assets_and_browser.py').read_text()
  for name in ('check_navigation','check_ch07_browser','check_ch15_browser','check_ch21_browser'):
   self.assertIn(f'{name}(page,context,url,review)',t)
  for p in ('tools/tw/apply_ch21.py','.github/workflows/ch21-integrate.yml','.github/workflows/ch21-snapshot.yml'):
   self.assertFalse((ROOT/p).exists())
if __name__=='__main__':unittest.main()

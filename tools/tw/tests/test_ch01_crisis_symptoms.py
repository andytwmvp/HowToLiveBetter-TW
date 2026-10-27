"""危機先行、症狀分流、統計定義與原有來源保全。"""
import hashlib,json,subprocess,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from review_contract import ROOT,validate_entry,validate_runtime,publication_report
from body_renderer import body_blocks
from retroactive_audit import assert_preserved_or_rechecked,validate_recheck_history
BASE='ca40db0a8744b2661c07f61931f21515f7a38db8'
NEW={f'TW-01-{n:03}' for n in range(25,29)}
RECHECK={f'TW-13-{n:03}' for n in (3,7,20,24)}
def read(p):return json.loads((ROOT/p).read_text())
class CrisisSymptomsTests(unittest.TestCase):
 def test_formal_sources_hash_and_rendering(self):
  rt=validate_runtime();ii={x['id']:x for x in rt['items']};ss={s['id']:s for s in rt['sources']};mm={e['id']:e for e in read('localization/manifest.json')['entries']}
  for key in NEW|RECHECK:
   with self.subTest(key=key):
    self.assertTrue(validate_entry(mm[key]));i=ii[key];rv=read(f'localization/reviews/{key}.json');raw=(ROOT/i['target_path']).read_bytes()
    self.assertEqual(raw.decode(),i['body']);self.assertEqual(hashlib.sha256(raw).hexdigest(),rv['target_sha256'])
    self.assertEqual({x['url'] for x in rv['source_checks']},{ss[s]['url'] for s in i['source_ids']})
    self.assertEqual(sum(x['tag']=='h3' for x in body_blocks(i)),5)
 def test_emergency_first_and_denominators(self):
  b={x['id']:x['body'] for x in validate_runtime()['items']}
  c=b['TW-01-025'];self.assertLess(c.index('先撥119'),c.index('3,951'));self.assertIn('1925',c);self.assertIn('不是自行停處方藥',c);self.assertNotIn('oai_link_source',c)
  self.assertIn('每半年',b['TW-01-026']);self.assertIn('濃煙',b['TW-01-026']);self.assertIn('沒有家戶',b['TW-01-026'])
  self.assertIn('沒有疼痛',b['TW-01-027']);self.assertIn('先急診',b['TW-01-027']);self.assertIn('不等於',b['TW-01-027'])
  self.assertIn('不可與PDE5抑制劑併用',b['TW-01-028']);self.assertIn('4小時',b['TW-01-028']);self.assertIn('告知救護人員最近使用的藥名與時間',b['TW-01-028']);self.assertIn('不能證明已有冠心病',b['TW-01-028'])
  self.assertIn('不能解讀為超時',b['TW-13-003']);self.assertIn('母數',b['TW-13-007']);self.assertIn('暫時沒有症狀',b['TW-13-020']);self.assertIn('無家戶分母',b['TW-13-024'])
 def test_all_prior_content_and_actual_review_history(self):
  old=json.loads(subprocess.check_output(['git','show',BASE+':localization/tw-edition/runtime.json'],cwd=ROOT));rt=validate_runtime();ii={x['id']:x for x in rt['items']};ss={s['id']:s for s in rt['sources']}
  for row in old['items']:assert_preserved_or_rechecked(self,row,ii[row['id']])
  for row in old['sources']:self.assertEqual(row,ss[row['id']])
  rr={r['id']:r for r in read('localization/retroactive-review-register-20261019.json')['substantive_rechecks']}
  for key in RECHECK:
   self.assertEqual(rr[key]['status'],'ai_source_rechecked_professional_pending');validate_recheck_history(ROOT,rr[key],ii[key])
  self.assertFalse(publication_report()['publication_ready'])
if __name__=='__main__':unittest.main()

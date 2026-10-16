"""第15章合併前兩處轉述修正：逐檔雜湊保護，僅處理指定分支與六份資料。"""
from pathlib import Path
import hashlib
import json
import subprocess
ROOT=Path(__file__).resolve().parents[2]
CHANGES={'loan_old': '超過30%時，買方得選依原承諾利率、年限不低於7年分期，或解除契約。', 'loan_new': '超過30%時，規範另列按原承諾利率、償還年限不得少於7年的分期方式，並規定買賣雙方得選擇分期或解除契約；實際處理應依該款及契約正式主張，不把它改寫成所有核貸不足均可任意取消。', 'loan_claim_old': '第18點規定賣方洽定貸款不足的歸責、30%分母、年限及給付程序。', 'loan_claim_new': '第18點區分賣方洽定貸款不足的歸責及30%分母；雙方均不可歸責且差額超過30%時，另列不少於7年的分期及買賣雙方得選擇分期或解除的方式，不是所有核貸不足一概可取消。', 'case_old': '法務部介紹過限制欠費住戶門禁的爭議案例，但個案判斷不等於每種門禁操作都必定構成同一罪名或固定賠償。', 'case_new': '法務部2012年專欄介紹的是住戶違反外牆鐵窗規約、遭停用感應磁卡的民事爭議，不是欠管理費案件。它只能提示管理權不等於任意剝奪出入權；實際欠費催收仍應依第21條等規定處理，不能把該案例當成每種門禁操作皆構成同一罪名或固定賠償。', 'case_claim_old': '法務部所載門禁催收爭議提示管理權限與侵害住戶權益風險，不能概括保證刑事或民事結果。', 'case_claim_new': '法務部案例的起因是外牆鐵窗規約爭議，不是欠管理費；僅作管理措施不得任意侵害出入權的例子，欠費催收另依條例第21條，不能概括保證個案結果。'}
BEFORE={'localization/ch15-batch.json': '823e791699ad6f71098f3140d4fd0ffd66ca1f9c15f5f7e2be373e544357c07a', 'localization/tw-edition/runtime.json': '199debf39afc0ba8f87adf5cd85344dbfb51ceea9fe84346f00f2db00fe73e3c', 'locales/zh-TW/book/ch15/TW-15-011.md': 'fc0bd4fab278f7de771e17a95fe955d4db6d48852869cd765068aa398c1fe89f', 'localization/reviews/TW-15-011.json': 'd09dbc4fa56715e6f7ba5005af4b54c2811c3472fd393852d0309f8d0196b418', 'locales/zh-TW/book/ch15/TW-15-017.md': '261e066c75fa1a5776d7310638fc4cd75bce7e170a7e1d24b5518bb1fad4601f', 'localization/reviews/TW-15-017.json': '7f837da4efafb228e51657b0d24f4220816052006454fae9075dafca95278f04'}
AFTER={'localization/ch15-batch.json': '0e2f4c1ba411d30bc58423f3bd79dfa3b2a5f5ca1a49c825e5c6c917b71a55a5', 'localization/tw-edition/runtime.json': 'e7bf1e5874dfb9a65134bda846075a02fbc8fa3019d0ca71f1cf4f6af7eff4d6', 'locales/zh-TW/book/ch15/TW-15-011.md': 'eb951e19e92952501df790aef6ac92d1b2d7ed7db7d4fea2b5eedc025012d4c5', 'localization/reviews/TW-15-011.json': '66045795ad84faf80ad57193e7faf5cf107995d6f7a03caf43670f1beefde851', 'locales/zh-TW/book/ch15/TW-15-017.md': '20093ded30e68c1521eb3937f3bac50451138dd9e96379d748f39ef6fee107d2', 'localization/reviews/TW-15-017.json': 'c877cdcb20fc1bc7a387ebf188c3dab4cec217c03ae96681589a7b3ecc9287a4'}

def replace_once(value,before,after):
 if value.count(before)!=1:raise ValueError('待修改段落與已核對版本不同')
 return value.replace(before,after)
def packed(value):return (json.dumps(value,ensure_ascii=False,indent=2)+'\n').encode('utf-8')
def transform(root):
 raw={p:(root/p).read_bytes() for p in BEFORE}
 if any(hashlib.sha256(value).hexdigest()!=BEFORE[p] for p,value in raw.items()):raise ValueError('來源有其他修改，不覆寫')
 batch=json.loads(raw['localization/ch15-batch.json'])
 runtime=json.loads(raw['localization/tw-edition/runtime.json'])
 prepared={}
 for number,prefix,field,source in ((11,'loan','procedure','presalestandard'),(17,'case','limits','condopowers')):
  key=f'TW-15-{number:03}'
  entry=next(e for e in batch['entries'] if e['id']==key)
  entry[field]=replace_once(entry[field],CHANGES[prefix+'_old'],CHANGES[prefix+'_new'])
  entry['source_claims'][source]=CHANGES[prefix+'_claim_new']
  target=f'locales/zh-TW/book/ch15/{key}.md'
  body=replace_once(raw[target].decode(),CHANGES[prefix+'_old'],CHANGES[prefix+'_new'])
  body=replace_once(body,CHANGES[prefix+'_claim_old'],CHANGES[prefix+'_claim_new'])
  prepared[target]=body.encode('utf-8')
  item=next(e for e in runtime['items'] if e['id']==key)
  item['body']=body
  if field=='limits':item['limits']=entry['limits']
  rpath=f'localization/reviews/{key}.json'
  review=json.loads(raw[rpath]);review['target_sha256']=hashlib.sha256(prepared[target]).hexdigest()
  checks=[c for c in review['source_checks'] if c['claim']==CHANGES[prefix+'_claim_old']]
  if len(checks)!=1:raise ValueError('審閱紀錄與指定主張不同')
  checks[0]['claim']=CHANGES[prefix+'_claim_new']
  checks[0]['claim_review_note']='2026-10-17合併前重新對照官方指定段落；修正轉述的角色與案件事實，不是新判決或獨立專業鑑定。'
  prepared[rpath]=packed(review)
 prepared['localization/ch15-batch.json']=packed(batch)
 prepared['localization/tw-edition/runtime.json']=packed(runtime)
 if set(prepared)!=set(AFTER):raise ValueError('修改路徑不符')
 for path,value in prepared.items():
  if hashlib.sha256(value).hexdigest()!=AFTER[path]:raise ValueError('目標雜湊與已測試版本不同：'+path)
 for path,value in prepared.items():(root/path).write_bytes(value)
 return prepared

def main():
 branch=subprocess.check_output(['git','branch','--show-current'],cwd=ROOT,text=True).strip()
 origin=subprocess.check_output(['git','remote','get-url','origin'],cwd=ROOT,text=True).strip().removesuffix('.git')
 if branch!='tw/ch15-housing-20261017' or origin!='https://github.com/andytwmvp/HowToLiveBetter-TW':raise ValueError('拒絕其他儲存庫或分支')
 transform(ROOT)
 for name in ('tools/tw/apply_ch15_final_review.py','.github/workflows/ch15-final-review.yml'):(ROOT/name).unlink()
 print('PASS：六份指定資料與本地已核對雜湊一致；一次性工具已移除。')
if __name__=='__main__':main()

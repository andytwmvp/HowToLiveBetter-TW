"""第7章瀏覽器驗收：資料顯示及來源一致性，不代替補助核定或外站申辦。"""
from review_contract import ROOT,validate_runtime

def check_ch07_browser(page,context,url,review):
 data=validate_runtime();expected={e['id']:e for e in data['items']};ids={f'TW-07-{n:03}' for n in range(1,24)}
 page.set_viewport_size({'width':1440,'height':1000})
 page.goto(url+'index.html',wait_until='domcontentloaded')
 page.wait_for_function('window.TWRuntime && window.TWRuntime.ready')
 assert set(page.locator('[data-id^="TW-07-"]').evaluate_all('(xs)=>xs.map(x=>x.dataset.id)'))==ids
 for key in sorted(ids):
  card=page.locator('#'+key)
  assert card.locator('h3').count()==5 and 'TW-ID:' not in card.inner_text()
  assert card.locator('a[href^="https://"]').count()>=len(expected[key]['source_ids'])
 page.locator('#q').fill('急難紓困')
 card=page.locator('#TW-07-006');assert card.count()==1
 for word in ('戶籍地','居住地','1萬至3萬元','5,000元','核定後'):assert word in card.inner_text()
 card.scroll_into_view_if_needed();page.screenshot(path=str(review/'chapter07-urgent-support.png'),animations='disabled')
 # 書籤是獨立情境；同頁只換hash不會清掉上一個搜尋條件，先驗證重設再切換。
 page.locator('#reset').click()
 assert page.locator('#q').input_value()==''
 assert set(page.locator('[data-id^="TW-07-"]').evaluate_all('(xs)=>xs.map(x=>x.dataset.id)'))==ids
 page.goto(url+'index.html#TW-07-007',wait_until='domcontentloaded')
 page.wait_for_function('window.TWRuntime && window.TWRuntime.ready')
 assert '基本工資' in page.locator('#TW-07-007').inner_text() and '其他收入' in page.locator('#TW-07-007').inner_text()
 page.set_viewport_size({'width':390,'height':844})
 page.goto(url+'selfcheck.html#TW-07-021',wait_until='domcontentloaded')
 page.wait_for_function('window.TWRuntime && window.TWRuntime.ready')
 page.locator('#q').fill('便利商店')
 card=page.locator('#TW-07-021');assert card.count()==1
 card.locator('.seg button.yes').click();assert card.locator('.seg button.yes').get_attribute('aria-pressed')=='true'
 assert '08:00至22:00' in card.inner_text()
 assert page.evaluate('document.documentElement.scrollWidth <= innerWidth+1')
 card.scroll_into_view_if_needed();page.screenshot(path=str(review/'chapter07-housing-mobile.png'),animations='disabled')
 page.goto((ROOT/'dist/HowToLiveBetter-TW.html').as_uri(),wait_until='domcontentloaded')
 page.wait_for_function('window.TWRuntime && window.TWRuntime.ready')
 assert set(page.locator('[data-id^="TW-07-"]').evaluate_all('(xs)=>xs.map(x=>x.dataset.id)'))==ids
 assert '最大債權金融機構' in page.locator('#TW-07-023').inner_text()
 return ['第7章23條ID、五段正文及來源連結一致','急難救助戶籍／居住地搜尋、推計收入書籤、1957時段、手機自查及無水平溢出','離線23條與債務前置程序保留；沒有使用測試代辦給付或宣稱外站申請成功']

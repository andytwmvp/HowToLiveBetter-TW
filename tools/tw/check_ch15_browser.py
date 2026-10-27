"""第15章：驗證正文、來源與操作一致性，不代替個案契約或申貸。"""
from review_contract import ROOT,validate_runtime

def check_ch15_browser(page,context,url,review):
    expected={e['id']:e for e in validate_runtime()['items']}
    ids={f'TW-15-{n:03}' for n in range(1,19)}
    page.set_viewport_size({'width':1440,'height':1000})
    page.goto(url+'index.html',wait_until='domcontentloaded')
    page.wait_for_function('window.TWRuntime && window.TWRuntime.ready')
    assert set(page.locator('[data-id^="TW-15-"]').evaluate_all('(xs)=>xs.map(x=>x.dataset.id)'))==ids
    for key in sorted(ids):
        card=page.locator('#'+key)
        assert card.locator('h3').count()>=5 and 'TW-ID:' not in card.inner_text()
        assert card.locator('a[href^="https://"]').count()>=len(expected[key]['source_ids'])
    page.locator('#q').fill('面積與建材')
    card=page.locator('#TW-15-012');assert card.count()==1
    for word in ('2%','超過3%','全部找補'):assert word in card.inner_text()
    card.scroll_into_view_if_needed()
    page.screenshot(path=str(review/'chapter15-area-desktop.png'),animations='disabled')
    page.locator('#reset').click()
    assert page.locator('#q').input_value()==''
    page.goto(url+'index.html#TW-15-011',wait_until='domcontentloaded')
    page.wait_for_function('window.TWRuntime && window.TWRuntime.ready')
    text=page.locator('#TW-15-011').inner_text()
    assert '預定貸款' in text and '不是房地總價' in text
    page.set_viewport_size({'width':390,'height':844})
    page.goto(url+'selfcheck.html#TW-15-001',wait_until='domcontentloaded')
    page.wait_for_function('window.TWRuntime && window.TWRuntime.ready')
    page.locator('#q').fill('任意沒收')
    card=page.locator('#TW-15-001');assert card.count()==1
    card.locator('.seg button.yes').click()
    assert card.locator('.seg button.yes').get_attribute('aria-pressed')=='true'
    assert '二個月' in card.inner_text()
    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
    card.scroll_into_view_if_needed()
    page.screenshot(path=str(review/'chapter15-deposit-mobile.png'),animations='disabled')
    page.goto((ROOT/'dist/HowToLiveBetter-TW.html').as_uri(),wait_until='domcontentloaded')
    page.wait_for_function('window.TWRuntime && window.TWRuntime.ready')
    assert set(page.locator('[data-id^="TW-15-"]').evaluate_all('(xs)=>xs.map(x=>x.dataset.id)'))==ids
    assert '房地總價5%' in page.locator('#TW-15-018').inner_text()
    return ['第15章18條正文、小標題及來源連結一致','面積2%與3%搜尋、貸款差額書籤、手機押金自查與無水平溢出','離線18條與保留款範圍一致；測試不代辦核貸或推定個案權利']

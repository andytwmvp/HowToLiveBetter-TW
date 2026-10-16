"""第23章實際閱讀與離線回歸；來源網站連通不由本測試保證。"""
from review_contract import ROOT,validate_runtime

def check_ch23_browser(page,context,url,review):
    data=validate_runtime();ids={f'TW-23-{n:03}' for n in range(1,26)}
    page.set_viewport_size({'width':1440,'height':1000})
    page.goto(url+'index.html',wait_until='domcontentloaded')
    page.wait_for_function('window.TWRuntime && window.TWRuntime.ready')
    assert set(page.locator('[data-id^="TW-23-"]').evaluate_all('(xs)=>xs.map(x=>x.dataset.id)'))==ids
    expected={e['id']:e for e in data['items']}
    for key in ('TW-23-003','TW-23-009','TW-23-017','TW-23-024'):
        card=page.locator('#'+key)
        assert card.locator('h3').count()==5
        assert 'TW-ID:' not in card.inner_text() and '## ' not in card.inner_text()
        assert card.locator('a[href^="https://"]').count()>=len(expected[key]['source_ids'])
    card=page.locator('#TW-23-003')
    assert '51.4%' in card.inner_text() and '81.9%' in card.inner_text()
    assert card.locator('a[href="https://www.moi.gov.tw/News_Content.aspx?n=9&s=337608"]').count()>=1
    page.locator('#q').fill('320,000')
    assert page.locator('#TW-23-006').count()==1
    page.locator('#reset').click()
    page.goto(url+'index.html#TW-23-009',wait_until='domcontentloaded')
    page.wait_for_function('window.TWRuntime && window.TWRuntime.ready')
    page.locator('#TW-23-009').scroll_into_view_if_needed()
    page.screenshot(path=str(review/'chapter23-training.png'),animations='disabled')
    page.set_viewport_size({'width':390,'height':844})
    page.goto(url+'selfcheck.html#TW-23-017',wait_until='domcontentloaded')
    page.wait_for_function('window.TWRuntime && window.TWRuntime.ready')
    page.locator('#q').fill('交錯練習')
    card=page.locator('#TW-23-017');assert card.count()==1
    card.locator('.seg button.yes').click()
    assert card.locator('.seg button.yes').get_attribute('aria-pressed')=='true'
    assert '單字' in card.inner_text() and '區塊' in card.inner_text()
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth+1')
    card.scroll_into_view_if_needed();page.screenshot(path=str(review/'chapter23-interleave-mobile.png'),animations='disabled')
    page.goto((ROOT/'dist/HowToLiveBetter-TW.html').as_uri(),wait_until='domcontentloaded')
    page.wait_for_function('window.TWRuntime && window.TWRuntime.ready')
    assert set(page.locator('[data-id^="TW-23-"]').evaluate_all('(xs)=>xs.map(x=>x.dataset.id)'))==ids
    assert '第5條第1項' in page.locator('#TW-23-024').inner_text()
    return ['第23章25條ID、五段標題、來源連結與人口數據一致','職訓書籤、成本搜尋、交錯練習限制、手機自查按鈕與無水平溢出','離線25條及學位待施行界線保留；未在本測試對外查詢來源網頁']

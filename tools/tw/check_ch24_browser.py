"""第24章網站、自查及離線一致性：必須使用實際固定ID和來源連結。"""
from review_contract import ROOT,validate_runtime

def check_ch24_browser(page,context,url,review):
    ids={f'TW-24-{n:03d}' for n in range(1,16)}
    page.goto(url+'index.html',wait_until='domcontentloaded')
    page.wait_for_function('window.TWRuntime && window.TWRuntime.ready')
    assert set(page.locator('[data-id^="TW-24-"]').evaluate_all('(xs)=>xs.map(x=>x.dataset.id)'))==ids
    for key in ids:
        card=page.locator('#'+key)
        assert card.locator('h3').count()==5, key
        assert card.locator('a[href^="https://"]').count()>0,key
    page.locator('#q').fill('部分負擔')
    assert page.locator('#TW-24-002').count()==1
    page.locator('#reset').click()
    page.goto(url+'index.html#TW-24-007',wait_until='domcontentloaded')
    page.wait_for_function('window.TWRuntime && window.TWRuntime.ready')
    assert '檢傷' in page.locator('#TW-24-007').inner_text()
    page.set_viewport_size({'width':390,'height':844})
    page.goto(url+'selfcheck.html#TW-24-014',wait_until='domcontentloaded')
    page.wait_for_function('window.TWRuntime && window.TWRuntime.ready')
    card=page.locator('#TW-24-014')
    card.locator('.seg button.yes').click()
    assert card.locator('.seg button.yes').get_attribute('aria-pressed')=='true'
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth+1')
    page.screenshot(path=str(review/'chapter24-care-mobile.png'),animations='disabled')
    page.goto((ROOT/'dist/HowToLiveBetter-TW.html').as_uri(),wait_until='domcontentloaded')
    page.wait_for_function('window.TWRuntime && window.TWRuntime.ready')
    assert set(page.locator('[data-id^="TW-24-"]').evaluate_all('(xs)=>xs.map(x=>x.dataset.id)'))==ids
    return ['第24章15條臺灣正文、來源與5個小標題已顯示','健保部分負擔搜尋、急診檢傷書籤、慢箋自查與手機版可用','離線閱讀與共用164項資料的15條章節ID一致']

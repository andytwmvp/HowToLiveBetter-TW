"""第21章實際閱讀檢查；不作入境、承保、海關或藥物許可判定。"""
from review_contract import ROOT,validate_runtime

def check_ch21_browser(page,context,url,review):
    expected={e['id']:e for e in validate_runtime()['items']}
    ids={f'TW-21-{n:03}' for n in range(1,14)}
    page.set_viewport_size({'width':1440,'height':1000})
    page.goto(url+'index.html',wait_until='domcontentloaded')
    page.wait_for_function('window.TWRuntime && window.TWRuntime.ready')
    assert set(page.locator('[data-id^="TW-21-"]').evaluate_all('(xs)=>xs.map(x=>x.dataset.id)'))==ids
    for key in sorted(ids):
        card=page.locator('#'+key)
        assert card.locator('h3').count()==5 and 'TW-ID:' not in card.inner_text()
        assert card.locator('a[href^="https://"]').count()>=len(expected[key]['source_ids'])
    page.locator('#q').fill('人民幣2萬元')
    card=page.locator('#TW-21-006');assert card.count()==1
    for word in ('美金1萬元','超額即使申報','每人每次'):assert word in card.inner_text()
    card.scroll_into_view_if_needed()
    page.screenshot(path=str(review/'chapter21-cash-desktop.png'),animations='disabled')
    page.locator('#reset').click();assert page.locator('#q').input_value()==''
    page.goto(url+'index.html#TW-21-002',wait_until='domcontentloaded')
    page.wait_for_function('window.TWRuntime && window.TWRuntime.ready')
    assert '+886-800-085-095' in page.locator('#TW-21-002').inner_text()
    assert '自付國際電話費' in page.locator('#TW-21-002').inner_text()
    page.set_viewport_size({'width':390,'height':844})
    page.goto(url+'selfcheck.html#TW-21-007',wait_until='domcontentloaded')
    page.wait_for_function('window.TWRuntime && window.TWRuntime.ready')
    page.locator('#q').fill('遺失護照說明書')
    card=page.locator('#TW-21-007');assert card.count()==1
    card.locator('.seg button.yes').click()
    assert card.locator('.seg button.yes').get_attribute('aria-pressed')=='true'
    assert '入國證明書' in card.inner_text()
    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
    card.scroll_into_view_if_needed()
    page.screenshot(path=str(review/'chapter21-passport-mobile.png'),animations='disabled')
    page.goto((ROOT/'dist/HowToLiveBetter-TW.html').as_uri(),wait_until='domcontentloaded')
    page.wait_for_function('window.TWRuntime && window.TWRuntime.ready')
    assert set(page.locator('[data-id^="TW-21-"]').evaluate_all('(xs)=>xs.map(x=>x.dataset.id)'))==ids
    assert '不是返臺日起算' in page.locator('#TW-21-004').inner_text()
    return ['第21章13條正文、五個小標題與實際來源一致','現金申報搜尋、國內境外電話費書籤、手機失照自查及無水平溢出','離線13條與健保核退起算一致；沒有測試代辦出境、海關或藥物許可']

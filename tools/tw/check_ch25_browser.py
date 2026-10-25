"""第25章瀏覽器驗收；測試閱讀資料，不在測試時查詢外站或代辦法律程序。"""
from review_contract import ROOT,validate_runtime

def check_ch25_browser(page,context,url,review):
    data=validate_runtime();ids={f'TW-25-{n:03}' for n in range(1,13)}
    page.set_viewport_size({'width':1440,'height':1000})
    page.goto(url+'index.html',wait_until='domcontentloaded')
    page.wait_for_function('window.TWRuntime && window.TWRuntime.ready')
    assert set(page.locator('[data-id^="TW-25-"]').evaluate_all('(xs)=>xs.map(x=>x.dataset.id)'))==ids
    expected={e['id']:e for e in data['items']}
    for key in sorted(ids):
        card=page.locator('#'+key);assert card.locator('h3').count()==5
        assert 'TW-ID:' not in card.inner_text() and '## ' not in card.inner_text()
        assert card.locator('a[href^="https://"]').count()>=len(expected[key]['source_ids'])
    page.locator('#q').fill('中低收入戶')
    card=page.locator('#TW-25-006');assert card.count()==1
    assert '2026-01-01' in card.inner_text() and '私立' in card.inner_text()
    card.scroll_into_view_if_needed();page.screenshot(path=str(review/'chapter25-public-relief.png'),animations='disabled')
    page.locator('#reset').click()
    page.goto(url+'index.html#TW-25-011',wait_until='domcontentloaded')
    page.wait_for_function('window.TWRuntime && window.TWRuntime.ready')
    assert '清冊不是拋棄繼承' in page.locator('#TW-25-011').inner_text()
    page.set_viewport_size({'width':390,'height':844})
    page.goto(url+'selfcheck.html#TW-25-012',wait_until='domcontentloaded')
    page.wait_for_function('window.TWRuntime && window.TWRuntime.ready')
    page.locator('#q').fill('死亡年度所得稅')
    card=page.locator('#TW-25-012');assert card.count()==1
    card.locator('.seg button.yes').click();assert card.locator('.seg button.yes').get_attribute('aria-pressed')=='true'
    for phrase in ('死亡日起3個月','死亡次日起算6個月','2026年9月13日','18期','不代表登記自動展延'):assert phrase in card.inner_text()
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth+1')
    card.scroll_into_view_if_needed();page.screenshot(path=str(review/'chapter25-deadlines-mobile.png'),animations='disabled')
    page.goto((ROOT/'dist/HowToLiveBetter-TW.html').as_uri(),wait_until='domcontentloaded')
    page.wait_for_function('window.TWRuntime && window.TWRuntime.ready')
    assert set(page.locator('[data-id^="TW-25-"]').evaluate_all('(xs)=>xs.map(x=>x.dataset.id)'))==ids
    assert 'iCloud鑰匙圈' in page.locator('#TW-25-010').inner_text()
    return ['第25章12條ID、五段標題與可點擊來源一致','指定公立設施減免搜尋、繼承書籤、手機自查及3個月與6個月不同起算、無水平溢出','離線12條與數位帳號限制保留；未以本測試聲稱外站連通或法律核准']

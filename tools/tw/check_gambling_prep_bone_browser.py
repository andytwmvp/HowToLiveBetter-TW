"""實際核對第1章危機／症狀與本批急救再審的正式閱讀出口。"""
from review_contract import ROOT, validate_runtime


def check_gambling_prep_bone_browser(page, context, url, review):
    runtime = validate_runtime()
    ids = {f'TW-01-{n:03}' for n in range(37, 41)} | {f'TW-13-{n:03}' for n in (16, 17, 18, 19)}
    items = {e['id']: e for e in runtime['items']}
    sources = {s['id']: s for s in runtime['sources']}
    for width, height in ((1440, 1000), (390, 844)):
        page.set_viewport_size({'width': width, 'height': height})
        for target in (url + 'index.html', url + 'selfcheck.html', (ROOT / 'dist/HowToLiveBetter-TW.html').as_uri()):
            page.goto(target, wait_until='domcontentloaded')
            page.wait_for_function('window.TWRuntime && window.TWRuntime.ready')
            for key in sorted(ids):
                article = page.locator('#' + key)
                assert article.count() == 1, (target, key)
                assert items[key]['title'] in article.inner_text()
                assert article.locator('h3').count() == 5, key
                for source_id in items[key]['source_ids']:
                    assert article.locator('a').evaluate_all('(xs, u) => xs.some(a => a.href === u)', sources[source_id]['url']), (key, source_id)
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1'), target
        page.goto(url + 'selfcheck.html#TW-01-038', wait_until='domcontentloaded')
        page.wait_for_function('window.TWRuntime && window.TWRuntime.ready')
        button = page.locator('#TW-01-038 .seg button.yes')
        button.click()
        assert button.get_attribute('aria-pressed') == 'true'
        page.locator('#q').fill('PrEP')
        assert page.locator('#TW-01-038').count() == 1
        page.locator('#reset').click()
        page.locator('#q').fill('葡萄糖錠')
        assert page.locator('#TW-13-017').count() == 1
        page.screenshot(path=str(review / f'gambling-prep-bone-{width}.png'), animations='disabled')
    page.set_viewport_size({'width': 1440, 'height': 1000})
    return ['四篇戒賭／PrEP／骨鬆與四篇急救再審在桌機、手機、自查及離線的ID、五段正文及來源連結一致；PrEP與吞嚥限制搜尋、自查按鈕與無水平溢出通過；未以瀏覽器檢查宣稱醫療或消防專業認證。']

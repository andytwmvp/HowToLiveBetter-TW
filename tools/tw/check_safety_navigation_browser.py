"""實際核對三則中風、心臟急症及防災導航再審的逐段閱讀出口。"""
from review_contract import ROOT, validate_runtime
from body_renderer import body_blocks


def check_safety_navigation_browser(page, context, url, review):
    runtime = validate_runtime()
    ids = {'TW-NAV-001','TW-NAV-002','TW-NAV-010'}
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
                assert article.locator('h3').count() == (6 if key=='TW-NAV-010' else 0), key
                rendered = article.text_content()
                for block in body_blocks(items[key]):
                    assert block['text'] in rendered, (target, key, block['text'][:50])
                for source_id in items[key]['source_ids']:
                    assert article.locator('a').evaluate_all('(xs, u) => xs.some(a => a.href === u)', sources[source_id]['url']), (key, source_id)
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1'), target
        page.goto(url + 'selfcheck.html#TW-NAV-001', wait_until='domcontentloaded')
        page.wait_for_function('window.TWRuntime && window.TWRuntime.ready')
        button = page.locator('#TW-NAV-001 .seg button.yes')
        button.click()
        assert button.get_attribute('aria-pressed') == 'true'
        page.locator('#q').fill('最後正常')
        assert page.locator('#TW-NAV-001').count() == 1
        page.locator('#reset').click()
        page.locator('#q').fill('不要等待警報')
        assert page.locator('#TW-NAV-010').count() == 1
        page.screenshot(path=str(review / f'safety-navigation-{width}.png'), animations='disabled')
    page.set_viewport_size({'width': 1440, 'height': 1000})
    return ['三則高風險導航於1440／390、閱讀／自查／離線逐段全文與來源一致；最後正常及海嘯避難搜尋、自查按鈕、無水平溢出通過。非醫療或災防專業驗收。']

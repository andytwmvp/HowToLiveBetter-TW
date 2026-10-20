"""實際核對三篇暴力現場及施救權益再審的逐段閱讀出口。"""
from review_contract import ROOT, validate_runtime
from body_renderer import body_blocks


def check_conflict_rescue_rights_browser(page, context, url, review):
    runtime = validate_runtime()
    ids = {f'TW-13-{n:03}' for n in (36, 37, 39)}
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
                rendered = article.text_content()
                for block in body_blocks(items[key]):
                    assert block['text'] in rendered, (target, key, block['text'][:50])
                for source_id in items[key]['source_ids']:
                    assert article.locator('a').evaluate_all('(xs, u) => xs.some(a => a.href === u)', sources[source_id]['url']), (key, source_id)
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1'), target
        page.goto(url + 'selfcheck.html#TW-13-036', wait_until='domcontentloaded')
        page.wait_for_function('window.TWRuntime && window.TWRuntime.ready')
        button = page.locator('#TW-13-036 .seg button.yes')
        button.click()
        assert button.get_attribute('aria-pressed') == 'true'
        page.locator('#q').fill('2024年9月')
        assert page.locator('#TW-13-036').count() == 1
        page.locator('#reset').click()
        page.locator('#q').fill('第176條')
        assert page.locator('#TW-13-039').count() == 1
        page.screenshot(path=str(review / f'conflict-rescue-rights-{width}.png'), animations='disabled')
    page.set_viewport_size({'width': 1440, 'height': 1000})
    return ['三篇威脅索財／鬥毆／施救權益再審，桌機1440及手機390、閱讀／自查／離線逐段全文、五標題及來源一致；統計斷點與民事請求搜尋、自查與無水平溢出通過。不是警察、消防、心理或法律專業認證。']

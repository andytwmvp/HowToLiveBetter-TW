"""實際核對五篇感染、照護與斷肢再審的逐段閱讀出口。"""
from review_contract import ROOT, validate_runtime
from body_renderer import body_blocks


def check_bites_ticks_water_assault_amputation_browser(page, context, url, review):
    runtime = validate_runtime()
    ids = {f'TW-13-{n:03}' for n in (13, 34, 35, 42, 47)}
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
        page.goto(url + 'selfcheck.html#TW-13-013', wait_until='domcontentloaded')
        page.wait_for_function('window.TWRuntime && window.TWRuntime.ready')
        button = page.locator('#TW-13-013 .seg button.yes')
        button.click()
        assert button.get_attribute('aria-pressed') == 'true'
        page.locator('#q').fill('1,146')
        assert page.locator('#TW-13-013').count() == 1
        page.locator('#reset').click()
        page.locator('#q').fill('3,643')
        assert page.locator('#TW-13-042').count() == 1
        page.screenshot(path=str(review / f'bites-ticks-water-assault-amputation-{width}.png'), animations='disabled')
    page.set_viewport_size({'width': 1440, 'height': 1000})
    return ['五篇動物咬抓／蜱蟲／飲水／性侵後照護／斷肢再審，桌機1440及手機390、閱讀／自查／離線逐段全文、五標題及來源一致；動物監測與醫療服務數搜尋、自查按鈕與無水平溢出通過。非專業認證。']

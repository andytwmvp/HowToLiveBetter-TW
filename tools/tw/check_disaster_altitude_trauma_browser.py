"""實際核對四篇災害、山域及穿刺異物再審的閱讀出口。"""
from review_contract import ROOT, validate_runtime


def check_disaster_altitude_trauma_browser(page, context, url, review):
    runtime = validate_runtime()
    ids = {f'TW-13-{n:03}' for n in (30, 32, 33, 40)}
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
        page.goto(url + 'selfcheck.html#TW-13-040', wait_until='domcontentloaded')
        page.wait_for_function('window.TWRuntime && window.TWRuntime.ready')
        button = page.locator('#TW-13-040 .seg button.yes')
        button.click()
        assert button.get_attribute('aria-pressed') == 'true'
        page.locator('#q').fill('1066')
        assert page.locator('#TW-13-033').count() == 1
        page.locator('#reset').click()
        page.locator('#q').fill('不等待警報')
        assert page.locator('#TW-13-030').count() == 1
        page.screenshot(path=str(review / f'disaster-altitude-trauma-{width}.png'), animations='disabled')
    page.set_viewport_size({'width': 1440, 'height': 1000})
    return ['四篇地震／雷擊／高山症／穿刺異物再審，在桌機、手機、正式閱讀、自查與離線之ID、五段正文及來源一致；1066問卷與不等待警報搜尋、自查按鈕及無水平溢出通過。工程驗證不代表醫療、消防或建築安全認證。']

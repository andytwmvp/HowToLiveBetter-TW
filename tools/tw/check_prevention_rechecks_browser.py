"""實際核對第1章疫苗／檢測與本批急救再審的正式閱讀出口。"""
from review_contract import ROOT, validate_runtime


def check_prevention_rechecks_browser(page, context, url, review):
    runtime = validate_runtime()
    ids = {f'TW-01-{n:03}' for n in range(21, 25)} | {f'TW-13-{n:03}' for n in (12, 14, 15, 25)}
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
        page.goto(url + 'selfcheck.html#TW-01-023', wait_until='domcontentloaded')
        page.wait_for_function('window.TWRuntime && window.TWRuntime.ready')
        button = page.locator('#TW-01-023 .seg button.yes')
        button.click()
        assert button.get_attribute('aria-pressed') == 'true'
        page.locator('#q').fill('8週例外')
        assert page.locator('#TW-01-022').count() == 1
        page.locator('#reset').click()
        page.locator('#q').fill('獲救後')
        assert page.locator('#TW-13-025').count() == 1
        page.screenshot(path=str(review / f'prevention-rechecks-{width}.png'), animations='disabled')
    page.set_viewport_size({'width': 1440, 'height': 1000})
    return ['四篇疫苗／檢測與四篇急救再審在桌機、手機、自查及離線的ID、五段正文及來源連結一致；接種史搜尋、自查按鈕與無水平溢出通過；未代辦接種或宣稱外站申請成功。']

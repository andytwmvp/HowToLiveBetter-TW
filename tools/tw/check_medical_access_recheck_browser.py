"""急救費用、自費告知、認定與病歷全文及互動。"""
from review_contract import ROOT, validate_runtime
from body_renderer import body_blocks


def check_medical_access_recheck_browser(page, context, url, review):
    runtime = validate_runtime()
    ids = {'TW-24-006', 'TW-24-010', 'TW-24-012', 'TW-24-002'}
    items = {i['id']: i for i in runtime['items']}
    sources = {s['id']: s for s in runtime['sources']}
    for width, height in ((1440, 1000), (390, 844)):
        page.set_viewport_size({'width': width, 'height': height})
        for target in (url+'index.html', url+'selfcheck.html', (ROOT/'dist/HowToLiveBetter-TW.html').as_uri()):
            page.goto(target, wait_until='domcontentloaded')
            page.wait_for_function('window.TWRuntime && window.TWRuntime.ready')
            for key in sorted(ids):
                article = page.locator('#'+key)
                assert article.count() == 1, (target, key)
                assert items[key]['title'] in article.inner_text()
                assert article.locator('h3').count() == 5, (target, key)
                rendered = article.text_content()
                for block in body_blocks(items[key]):
                    assert block['text'] in rendered, (target, key, block['text'][:50])
                for source_id in items[key]['source_ids']:
                    assert article.locator('a').evaluate_all('(xs,u)=>xs.some(a=>a.href===u)', sources[source_id]['url']), (key, source_id)
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1'), target
        page.goto(url+'selfcheck.html#TW-24-006', wait_until='domcontentloaded')
        page.wait_for_function('window.TWRuntime && window.TWRuntime.ready')
        button = page.locator('#TW-24-006 .seg button.yes')
        button.click()
        assert button.get_attribute('aria-pressed') == 'true'
        for key, text in (('TW-24-006','調解程序不收費'), ('TW-24-010','到宅鑑定'), ('TW-24-012','書面全案報價'), ('TW-24-002','不是總帳單')):
            page.locator('#q').fill(text)
            article = page.locator('#'+key)
            assert article.count() == 1, (key, text)
            article.evaluate('(e)=>e.scrollIntoView({block:"start"})')
            page.screenshot(path=str(review/f'access-{key}-{width}.png'), animations='disabled')
        page.locator('#reset').click()
    page.set_viewport_size({'width':1440, 'height':1000})
    return ['醫爭、身障、植牙、門診費用四篇於1440／390、閱讀／自查／離線逐段正文及來源一致；搜尋、自查與無水平溢出通過，非醫療法律專業驗收。']

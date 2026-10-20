"""四篇肝炎、領藥與照護契約再審正文、來源及搜尋互動。"""
from review_contract import ROOT, validate_runtime
from body_renderer import body_blocks


def check_hepatitis_prescriptions_contract_browser(page, context, url, review):
    runtime = validate_runtime()
    ids = {'TW-16-011', 'TW-16-005', 'TW-24-014', 'TW-17-011'}
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
        page.goto(url+'selfcheck.html#TW-16-011', wait_until='domcontentloaded')
        page.wait_for_function('window.TWRuntime && window.TWRuntime.ready')
        button = page.locator('#TW-16-011 .seg button.yes')
        button.click()
        assert button.get_attribute('aria-pressed') == 'true'
        for key, text in (('TW-16-011','1.88%'), ('TW-16-005','前10日內'), ('TW-24-014','三者條件不同'), ('TW-17-011','機構名義專戶')):
            page.locator('#q').fill(text)
            article = page.locator('#'+key)
            assert article.count() == 1, (key, text)
            article.evaluate('(e)=>e.scrollIntoView({block:"start"})')
            page.screenshot(path=str(review/f'contract-{key}-{width}.png'), animations='disabled')
        page.locator('#reset').click()
    page.set_viewport_size({'width':1440, 'height':1000})
    return ['四篇肝炎慢箋與照護契約於1440／390、閱讀／自查／離線逐段全文與來源一致；孕婦比例、領藥效期、代領遠距與保證金搜尋、自查按鈕及無水平溢出通過；非醫療法律專業驗收。']

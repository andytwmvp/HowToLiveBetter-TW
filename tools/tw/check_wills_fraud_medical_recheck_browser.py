"""遺囑、防詐、家庭醫師與基層急症四篇閱讀器檢查。"""
from review_contract import ROOT, validate_runtime
from body_renderer import body_blocks


def check_wills_fraud_medical_recheck_browser(page, context, url, review):
    runtime = validate_runtime()
    ids = {'TW-17-002', 'TW-17-004', 'TW-16-006', 'TW-24-001'}
    items = {item['id']: item for item in runtime['items']}
    sources = {source['id']: source for source in runtime['sources']}
    for width, height in ((1440, 1000), (390, 844)):
        page.set_viewport_size({'width': width, 'height': height})
        for target in (url + 'index.html', url + 'selfcheck.html', (ROOT / 'dist/HowToLiveBetter-TW.html').as_uri()):
            page.goto(target, wait_until='domcontentloaded')
            page.wait_for_function('window.TWRuntime && window.TWRuntime.ready')
            for key in sorted(ids):
                article = page.locator('#' + key)
                assert article.count() == 1, (target, key)
                assert items[key]['title'] in article.inner_text()
                assert article.locator('h3').count() == 5, (target, key)
                rendered = article.text_content()
                for block in body_blocks(items[key]):
                    assert block['text'] in rendered, (target, key, block['text'][:60])
                for source_id in items[key]['source_ids']:
                    assert article.locator('a').evaluate_all('(xs,u)=>xs.some(a=>a.href===u)', sources[source_id]['url']), (key, source_id)
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1'), target
        page.goto(url + 'selfcheck.html#TW-24-001', wait_until='domcontentloaded')
        page.wait_for_function('window.TWRuntime && window.TWRuntime.ready')
        button = page.locator('#TW-24-001 .seg button.yes')
        button.click()
        assert button.get_attribute('aria-pressed') == 'true'
        for key, needle in (
            ('TW-17-002', '2027-02-17起施行'),
            ('TW-17-004', '先掛斷並用獨立管道查證'),
            ('TW-16-006', '2026-07-01'),
            ('TW-24-001', '立即撥119'),
        ):
            page.locator('#q').fill(needle)
            article = page.locator('#' + key)
            assert article.count() == 1, (key, needle)
            article.evaluate('(e)=>e.scrollIntoView({block:"start"})')
            page.screenshot(path=str(review / f'wills-fraud-medical-{key}-{width}.png'), animations='disabled')
        page.locator('#reset').click()
    page.set_viewport_size({'width': 1440, 'height': 1000})
    return ['遺囑、防詐、家庭醫師與基層就醫四篇於1440／390、閱讀／自查／離線逐段全文與來源一致；搜尋、自查及無水平溢出通過；非法律、警政、醫療或健保專業驗收。']

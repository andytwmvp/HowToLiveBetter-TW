"""四篇醫療照護再審正文、來源與實際搜尋互動。"""
from review_contract import ROOT, validate_runtime
from body_renderer import body_blocks


def check_medical_care_browser(page, context, url, review):
    runtime = validate_runtime()
    ids = {'TW-16-012', 'TW-17-008', 'TW-17-013', 'TW-24-007'}
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
        page.goto(url+'selfcheck.html#TW-16-012', wait_until='domcontentloaded')
        page.wait_for_function('window.TWRuntime && window.TWRuntime.ready')
        button = page.locator('#TW-16-012 .seg button.yes')
        button.click()
        assert button.get_attribute('aria-pressed') == 'true'
        for key, text in (('TW-16-012','停電與故障備援'), ('TW-24-007','要求重新評估'), ('TW-17-013','7.99%'), ('TW-17-008','不為減壓拔除')):
            page.locator('#q').fill(text)
            article = page.locator('#'+key)
            assert article.count() == 1, (key, text)
            article.evaluate('(e)=>e.scrollIntoView({block:"start"})')
            page.screenshot(path=str(review/f'medical-care-{key}-{width}.png'), animations='disabled')
        page.locator('#reset').click()
    page.set_viewport_size({'width':1440, 'height':1000})
    return ['四篇醫療照護於1440／390、閱讀／自查／離線逐段全文與來源一致；氧氣備援、惡化重評、7.99%及醫材壓迫搜尋、自查按鈕與無水平溢出通過；非專業醫療驗收。']

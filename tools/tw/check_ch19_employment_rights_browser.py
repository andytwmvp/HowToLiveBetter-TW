"""第19章離職文件、契約、競業及派遣四篇於閱讀出口的全文與互動回歸。"""
from review_contract import ROOT, validate_runtime
from body_renderer import body_blocks


def check_ch19_employment_rights_browser(page, context, url, review):
    runtime = validate_runtime()
    ids = {'TW-19-017', 'TW-19-020', 'TW-19-022', 'TW-19-024'}
    items = {item['id']: item for item in runtime['items']}
    sources = {source['id']: source for source in runtime['sources']}
    assert ids.issubset(items)

    for width, height in ((1440, 1000), (390, 844)):
        page.set_viewport_size({'width': width, 'height': height})
        for target in (url+'index.html', url+'selfcheck.html', (ROOT/'dist/HowToLiveBetter-TW.html').as_uri()):
            page.goto(target, wait_until='domcontentloaded')
            page.wait_for_function('window.TWRuntime && window.TWRuntime.ready')
            for key in sorted(ids):
                article = page.locator('#'+key)
                assert article.count() == 1, (target, key)
                assert items[key]['title'] in article.inner_text(), (target, key)
                assert article.locator('h3').count() == 5, (target, key)
                rendered = article.text_content()
                for block in body_blocks(items[key]):
                    assert block['text'] in rendered, (target, key, block['text'][:50])
                for source_id in items[key]['source_ids']:
                    assert article.locator('a').evaluate_all(
                        '(xs,u)=>xs.some(a=>a.href===u)', sources[source_id]['url']
                    ), (key, source_id)
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1'), target

        page.goto(url+'selfcheck.html#TW-19-017', wait_until='domcontentloaded')
        page.wait_for_function('window.TWRuntime && window.TWRuntime.ready')
        button = page.locator('#TW-19-017 .seg button.yes')
        button.click()
        assert button.get_attribute('aria-pressed') == 'true'
        searches = (
            ('TW-19-017', '7日內補正'),
            ('TW-19-020', '從屬性程度'),
            ('TW-19-022', '離職時一個月平均工資的50%'),
            ('TW-19-024', '90日內'),
        )
        for key, phrase in searches:
            page.locator('#q').fill(phrase)
            page.wait_for_function("document.getElementById('status').textContent.startsWith('顯示 1／')")
            article = page.locator('#'+key)
            assert article.count() == 1 and article.is_visible(), (key, phrase)
            article.evaluate('(element)=>element.scrollIntoView({block:"start"})')
            page.screenshot(path=str(review/f'employment-rights-{key}-{width}.png'), animations='disabled')
        page.locator('#reset').click()

    page.set_viewport_size({'width': 1440, 'height': 1000})
    return ['四篇第19章勞動權益於1440／390、正式閱讀／自查／離線逐段全文及來源一致；離職補件、從屬性、競業補償與派遣期限可搜尋，自查互動及無水平溢出通過；非法律或勞動專業簽證。']

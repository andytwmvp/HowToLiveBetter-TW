"""職安、職災、工作急症、霸凌與健檢歷史再審全文及互動。"""
from review_contract import ROOT, validate_runtime
from body_renderer import body_blocks


def check_workplace_safety_recheck_browser(page, context, url, review):
    runtime = validate_runtime()
    ids = {'TW-19-009', 'TW-19-010', 'TW-19-011', 'TW-19-012', 'TW-19-016'}
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

        page.goto(url+'selfcheck.html#TW-19-009', wait_until='domcontentloaded')
        page.wait_for_function('window.TWRuntime && window.TWRuntime.ready')
        button = page.locator('#TW-19-009 .seg button.yes')
        button.click()
        assert button.get_attribute('aria-pressed') == 'true'
        searches = (
            ('TW-19-009', '2028-01-01才施行'),
            ('TW-19-010', '未經主管機關或現場應變負責人確認危害已排除'),
            ('TW-19-011', '平均月投保薪資發給'),
            ('TW-19-012', '不自行餵食或給藥'),
            ('TW-19-016', '30至99人雇主應自收到申訴翌日起4個月內作成決定'),
        )
        for key, phrase in searches:
            page.locator('#q').fill(phrase)
            article = page.locator('#'+key)
            assert article.count() == 1, (key, phrase)
            page.wait_for_function("document.getElementById('status').textContent.startsWith('顯示 1／')")
            assert article.is_visible(), (key, phrase)
            for other in sorted(ids - {key}):
                assert not page.locator('#'+other).is_visible(), (key, phrase, other)
            article.evaluate('(element)=>element.scrollIntoView({block:"start"})')
            page.screenshot(path=str(review/f'workplace-{key}-{width}.png'), animations='disabled')
        page.locator('#reset').click()
    page.set_viewport_size({'width': 1440, 'height': 1000})
    return ['第19章五篇職安、職災、工作急症、霸凌及健檢正文於1440／390、正式閱讀／自查／離線逐段全文與來源一致；數據範圍、法定給付、119、自查與無水平溢出通過；非職安、醫療、法律或保險專業簽證。']

"""驗證文章互相參照時，搜尋結果不會藏住連結目標。"""
from review_contract import ROOT


def check_internal_link_navigation_browser(page, url):
    targets = (
        ('網站', url+'index.html'),
        ('自我檢視', url+'selfcheck.html'),
        ('離線HTML', (ROOT/'dist/HowToLiveBetter-TW.html').as_uri()),
    )
    for width, height in ((1440, 1000), (390, 844)):
        page.set_viewport_size({'width': width, 'height': height})
        for name, target in targets:
            page.goto(target, wait_until='domcontentloaded')
            page.wait_for_function('window.TWRuntime && window.TWRuntime.ready')
            page.locator('#q').fill('初診規定')
            assert page.locator('#TW-24-004').count() == 1, (name, width, '來源文章沒有出現在搜尋結果')
            assert page.locator('#TW-16-002').count() == 0, (name, width, '測試前目標文章應被搜尋條件隱藏')
            page.locator('#TW-24-004 a[href="#TW-16-002"]').click()
            page.wait_for_function('document.getElementById("TW-16-002") !== null', timeout=5000)
            assert '慢箋領藥' in page.locator('#TW-16-002').inner_text(), (name, width, '站內連結沒有顯示目標文章')
            assert page.evaluate('location.hash') == '#TW-16-002', (name, width, '站內連結沒有更新網址錨點')
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1'), (name, width, '手機或桌機版出現水平溢位')
    return ['網站、自我檢視及離線HTML在1440／390寬度下，搜尋篩選後點選跨篇連結會顯示並定位至原先隱藏的目標文章。']

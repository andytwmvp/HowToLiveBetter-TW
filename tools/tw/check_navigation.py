"""實際瀏覽器驗證臺灣預設來源、自查年齡邊界與離線資料一致性。"""
import copy
import json
from edition import build_html
from review_contract import ROOT, validate_runtime

def mock_json_response(body):
    """回呼只收一個route參數，避免第二個Request蓋掉測試回應文字。"""
    if not isinstance(body, str):
        raise TypeError('測試HTTP回應必須為原始JSON文字')
    def handler(route):
        route.fulfill(status=200, content_type='application/json', body=body)
    return handler


def check_navigation(page, context, url, review):
    data=validate_runtime();expected={e['id'] for e in data['items']};requests=[]
    def capture(request):requests.append(request.url)
    page.on('request',capture)
    page.goto(url,wait_until='domcontentloaded')
    page.wait_for_function('window.TWRuntime && window.TWRuntime.ready')
    assert set(page.locator('.q').evaluate_all('(xs)=>xs.map(x=>x.dataset.id)'))==expected
    assert not any('/book/' in request or '/chapters/' in request for request in requests),'臺灣預設頁讀取了原作或草稿'
    assert page.locator('[data-id^="TW-14-"]').count()==12
    assert page.locator('[data-id^="TW-19-"]').count()==sum(e['id'].startswith('TW-19-') for e in data['items'])
    labor=page.locator('#TW-19-004')
    assert labor.locator('h3').count()==5 and '50,000' in labor.inner_text()
    assert labor.locator('a[href="https://law.moj.gov.tw/LawClass/LawAll.aspx?pcode=N0030020"]').count()>=1
    page.locator('#q').fill('最低服務年限')
    assert page.locator('#TW-19-022').count()==1
    page.locator('#reset').click()
    chapter=page.locator('#TW-14-003')
    assert chapter.locator('h3').count()==5
    assert 'TW-ID:' not in chapter.inner_text() and '## ' not in chapter.inner_text()
    assert chapter.locator('a[href="https://support.apple.com/zh-tw/118228"]').count()>=1
    page.locator('#q').fill('SIM PIN')
    assert page.locator('#TW-14-003').count()==1
    page.locator('#reset').click()
    page.screenshot(path=str(review/'taiwan-reader.png'),animations='disabled')
    page.goto(url+'index.html#TW-14-003',wait_until='domcontentloaded')
    page.wait_for_function('window.TWRuntime && window.TWRuntime.ready')
    page.locator('#TW-14-003').scroll_into_view_if_needed()
    page.screenshot(path=str(review/'chapter14-sim-pin.png'),animations='disabled')
    page.goto(url+'index.html#TW-19-022',wait_until='domcontentloaded')
    page.wait_for_function('window.TWRuntime && window.TWRuntime.ready')
    page.locator('#TW-19-022').scroll_into_view_if_needed()
    page.screenshot(path=str(review/'chapter19-employment-terms.png'),animations='disabled')
    page.goto(url+'index.html#TW-19-009',wait_until='domcontentloaded')
    page.wait_for_function('window.TWRuntime && window.TWRuntime.ready')
    health=page.locator('#TW-19-009')
    assert health.locator('h3').count()==5 and '2028-01-01' in health.inner_text()
    assert health.locator('a[href*="LawOldVer.aspx"]').count()>=1
    page.locator('#q').fill('191,000')
    assert page.locator('#TW-19-018').count()==1
    assert '不是稅額' in page.locator('#TW-19-018').inner_text()
    page.locator('#reset').click()
    page.set_viewport_size({'width':390,'height':844})
    page.goto(url+'index.html#TW-19-016',wait_until='domcontentloaded')
    page.wait_for_function('window.TWRuntime && window.TWRuntime.ready')
    bullying=page.locator('#TW-19-016')
    assert '最高負責人' in bullying.inner_text() and '2026-07-01' in bullying.inner_text()
    bullying.scroll_into_view_if_needed()
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1')
    page.screenshot(path=str(review/'chapter19-occupational-rights.png'),animations='disabled')
    page.set_viewport_size({'width':1440,'height':1000})

    # 損壞百分比編碼只忽略錨點，不清空可用的安全導航。
    page.goto(url+'index.html#%EF',wait_until='domcontentloaded')
    page.wait_for_function('window.TWRuntime && window.TWRuntime.ready')
    assert page.locator('.q').count()==len(expected)
    page.locator('#q').fill('乳癌')
    # 新增合法正文後可能有多個命中；逐項核對真正應命中的 ID，不凍結為一筆。
    expected_search = {e['id'] for e in data['items']
                       if '乳癌' in ' '.join(e[k] for k in ('title', 'body', 'limits'))}
    actual_search = set(page.locator('.q').evaluate_all('(xs)=>xs.map(x=>x.dataset.id)'))
    assert actual_search == expected_search
    assert page.locator('.q').count() == len(expected_search)
    assert 'TW-NAV-004' in actual_search
    page.goto(url+'selfcheck.html',wait_until='domcontentloaded')
    page.wait_for_function('window.TWRuntime && window.TWRuntime.ready')
    page.locator('#sex').select_option('f')
    for age,ids in [(24,set()),(25,{'TW-NAV-005'}),(29,{'TW-NAV-005'}),(30,{'TW-NAV-006'}),(39,{'TW-NAV-006'}),(40,{'TW-NAV-004','TW-NAV-006'}),(74,{'TW-NAV-004','TW-NAV-006'}),(75,{'TW-NAV-006'})]:
        page.locator('#age').fill(str(age))
        visible=set(page.locator('.q').evaluate_all('(xs)=>xs.map(x=>x.dataset.id)'))
        assert visible & {'TW-NAV-004','TW-NAV-005','TW-NAV-006'}==ids,(age,visible)
    page.locator('#age').fill('44');page.locator('#family').select_option('n');assert not page.locator('#TW-NAV-009').count()
    page.locator('#family').select_option('y');assert page.locator('#TW-NAV-009').count()==1
    page.locator('#age').fill('45');assert not page.locator('#TW-NAV-009').count()
    page.locator('#reset').click();page.locator('.seg button.yes').first.click()
    assert page.locator('.seg button.yes').first.get_attribute('aria-pressed')=='true'
    assert page.evaluate('localStorage.getItem("selfcheck-v1")') is None
    page.set_viewport_size({'width':390,'height':844})
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1')
    page.screenshot(path=str(review/'taiwan-selfcheck-mobile.png'),animations='disabled')
    def fail(route):route.fulfill(status=503,body='unavailable')
    context.route('**/localization/tw-edition/runtime.json',fail)
    try:
        requests.clear();page.goto(url,wait_until='domcontentloaded')
        page.wait_for_function('window.TWRuntime && window.TWRuntime.failed')
        assert page.locator('.q').count()==0
        assert not any('/book/' in request or '/chapters/' in request for request in requests)
    finally:context.unroute('**/localization/tw-edition/runtime.json',fail)
    # 伺服器成功回傳HTTP200，也必須驗證內容與日期，不能只檢查HTTP狀態。
    invalid=[]
    bad=copy.deepcopy(data);bad['items'][8]['eligibility']['family_history']='false';invalid.append(bad)
    bad=copy.deepcopy(data);bad['sources'][0]['url']='https:///missing-host';invalid.append(bad)
    bad=copy.deepcopy(data);bad['review_due_at']='2000-01-01';invalid.append(bad)
    raw_invalid=[json.dumps(payload) for payload in invalid]
    # 不先轉成物件：必須驗證伺服器實際回傳的重複欄位及數值溢位。
    original=json.dumps(data)
    raw_invalid.append(original.replace('"review_status": "source_checked"', '"review_status": "draft", "review_status": "source_checked"', 1))
    raw_invalid.append(original.replace('"schema_version": 1', '"schema_version": 1, "overflow": 1e309', 1))
    for body in raw_invalid:
        serve_bad=mock_json_response(body)
        context.route('**/localization/tw-edition/runtime.json',serve_bad)
        try:
            requests.clear();page.goto(url,wait_until='domcontentloaded')
            page.wait_for_function('window.TWRuntime && window.TWRuntime.failed && !window.TWRuntime.ready')
            assert page.locator('.q').count()==0
            assert not any('/book/' in request or '/chapters/' in request for request in requests)
        finally:context.unroute('**/localization/tw-edition/runtime.json',serve_bad)
    out=ROOT/'dist/tw-navigation.html';build_html(out,data)
    page.goto(out.as_uri(),wait_until='domcontentloaded')
    page.wait_for_function('window.TWRuntime && window.TWRuntime.ready')
    assert set(page.locator('.q').evaluate_all('(xs)=>xs.map(x=>x.dataset.id)'))==expected
    page.goto(url+'index.html#e-14-1',wait_until='domcontentloaded')
    page.wait_for_url('**/source.html#e-14-1')
    page.wait_for_function("document.querySelectorAll('.card').length === 765",timeout=120000)
    assert page.url == url+'source.html#e-14-1'
    page.remove_listener('request',capture)
    return [f'臺灣預設閱讀與自查共用{len(expected)}項；含第14章及第19章正文，未讀取原作或草稿','乳癌40／74、子宮頸抹片25／29／30歲與大腸癌家族史邊界通過','手機版、自查、離線資料一致、HTTP503及HTTP200錯誤資料（含重複JSON欄位／非有限數值）均不回退；損壞錨點不阻斷閱讀']

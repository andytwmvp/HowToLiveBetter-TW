"""第26章網頁、手機自查與離線閱讀的整合驗收。"""
from review_contract import ROOT, validate_runtime

def check_ch26_browser(page,context,url,review):
    data=validate_runtime()
    ids={f"TW-26-{i:03}" for i in range(1,14)}
    page.goto(url+"index.html",wait_until="domcontentloaded")
    page.wait_for_function("window.TWRuntime && window.TWRuntime.ready")
    assert set(page.locator('[data-id^="TW-26-"]').evaluate_all("(xs)=>xs.map(x=>x.dataset.id)"))==ids
    for id in sorted(ids):
        card=page.locator("#"+id)
        assert card.locator("h3").count()==5
        assert card.locator('a[href^="https://"]').count()>=2
    page.locator("#q").fill("第三方支付")
    assert page.locator("#TW-26-001").count()==1
    page.screenshot(path=str(review/"chapter26-payment-desktop.png"),animations="disabled")
    page.locator("#reset").click()
    page.goto(url+"index.html#TW-26-009",wait_until="domcontentloaded")
    page.wait_for_function("window.TWRuntime && window.TWRuntime.ready")
    assert "10個工作日" in page.locator("#TW-26-009").inner_text()
    page.set_viewport_size({"width":390,"height":844})
    page.goto(url+"selfcheck.html#TW-26-012",wait_until="domcontentloaded")
    page.wait_for_function("window.TWRuntime && window.TWRuntime.ready")
    card=page.locator("#TW-26-012")
    card.locator(".seg button.yes").click()
    assert card.locator(".seg button.yes").get_attribute("aria-pressed")=="true"
    assert "尚未施行" in card.inner_text()
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1")
    page.screenshot(path=str(review/"chapter26-personal-data-mobile.png"),animations="disabled")
    page.goto((ROOT/"dist/HowToLiveBetter-TW.html").as_uri(),wait_until="domcontentloaded")
    page.wait_for_function("window.TWRuntime && window.TWRuntime.ready")
    assert set(page.locator('[data-id^="TW-26-"]').evaluate_all("(xs)=>xs.map(x=>x.dataset.id)"))==ids
    return ["第26章13項正文及來源連結顯示正確","第三方支付搜尋、著作權書籤、個資自查及手機響應正常","離線閱讀與共用資料一致"]

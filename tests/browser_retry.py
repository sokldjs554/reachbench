"""Exercise the public recorded comparison on desktop and mobile viewports."""
import argparse
import json
from pathlib import Path

from playwright.sync_api import sync_playwright, expect


def check(browser, url, out, mobile):
    size = {"width": 390, "height": 844} if mobile else {"width": 1440, "height": 1000}
    context = browser.new_context(viewport=size, has_touch=mobile, ignore_https_errors=True,
                                  user_agent="Mozilla/5.0")
    page = context.new_page()
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.goto(url, wait_until="domcontentloaded")
    link = page.locator("a.mobile-case" if mobile else ".play-controls .case-link")
    expect(link).to_be_visible()
    link.click()
    expect(page.locator("#workbench")).to_be_visible(timeout=60000)
    expect(page.locator("#clock")).to_have_text("6.31 s / 17.56 s")
    off, on = page.locator(".panel.off"), page.locator(".panel.on")
    expect(off.locator(".readout b")).to_contain_text("종료")
    expect(on.locator(".readout b")).to_contain_text("재시도")
    expect(off.locator(".picture span")).to_contain_text("자세 기록")
    expect(on.locator(".picture span")).to_contain_text("자세 기록")
    expect(page.locator("#evaluation")).to_contain_text("실제 재시도 0건")
    page.screenshot(path=out / ("mobile.png" if mobile else "desktop.png"), full_page=True)
    page.locator("#play").click()
    page.wait_for_timeout(400)
    page.locator("#play").click()
    paused = page.locator("#clock").inner_text()
    page.wait_for_timeout(120)
    assert paused == page.locator("#clock").inner_text() and not paused.startswith("6.31")
    expect(off.locator("time")).to_have_text("6.31 s")
    page.get_by_role("button", name="12.51초 · 두 번째 집기").click()
    expect(on.locator(".readout small")).to_contain_text("43.869 mm")
    page.get_by_role("button", name="17.56초 · 배치 결과").click()
    expect(on.locator(".readout b")).to_have_text("배치 성공")
    expect(on.locator(".picture span")).to_have_text("자세 기록 17.56 s")
    expect(on.locator(".readout small")).to_contain_text("2.29 mm")
    page.locator("#reset").click()
    expect(page.locator("#clock")).to_contain_text("0.00 s")
    page.locator("#timeline").focus()
    page.keyboard.press("End")
    expect(page.locator("#clock")).to_have_text("17.56 s / 17.56 s")
    page.locator("#photos button").nth(2).click()
    expect(page.locator("#clock")).to_contain_text("6.61 s")
    expect(page.locator("#alignment")).to_contain_text("30 ms")
    expect(page.locator("#alignment")).to_contain_text("6.62 s")
    page.locator("#inspector summary").click()
    expect(page.locator("#joints table")).to_be_visible()
    page.select_option("#mode","off")
    expect(page.locator("#photos button")).to_have_count(2)
    page.locator("#photos button").last.click()
    expect(page.locator("#clock")).to_contain_text("1.96 s")
    expect(page.locator("#alignment")).to_contain_text("20 ms")
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
    assert page.locator("#photos img").evaluate_all("(imgs)=>imgs.every(i=>i.complete && i.naturalWidth>0)")
    with page.expect_download() as download:
        page.get_by_role("link",name="관측·행동 데이터 받기 (JSONL)").click()
    samples = Path(download.value.path()).read_text().splitlines()
    assert len({json.loads(line)["sample_id"] for line in samples}) == 86
    assert not errors,errors
    context.close()


if __name__ == "__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("url")
    ap.add_argument("--out",type=Path,default=Path("work/retry-browser"))
    args=ap.parse_args()
    args.out.mkdir(exist_ok=True,parents=True)
    with sync_playwright() as pw:
        browser=pw.chromium.launch(executable_path="/usr/bin/chromium",headless=True,
                                   args=["--no-sandbox","--enable-unsafe-swiftshader","--use-angle=swiftshader"])
        for mobile in (False, True):
            check(browser,args.url,args.out,mobile)
            print("mobile" if mobile else "desktop","comparison passed",flush=True)
        browser.close()

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
    compare = page.locator(".entry-actions").get_by_role("link", name="재시도 켬·끔 비교", exact=True)
    expect(compare).to_be_visible()
    bounds = compare.bounding_box()
    assert bounds["y"] + bounds["height"] <= size["height"]
    preview = page.locator("#occlusion-preview")
    expect(preview).to_be_visible()
    expect(preview.locator("figcaption")).to_have_text(["정면 · 미검출", "후면 · 큐브 검출"])
    expect(page.locator(".retry-eval")).to_contain_text("0건")
    if mobile:
        run = page.locator("#hero-run")
        expect(run).to_be_enabled(timeout=90000)
        page.locator('[data-condition="normal"]').click()
        expect(preview).to_be_hidden()
        page.locator('[data-condition="occluded"]').click()
        expect(preview).to_be_visible()
        run.click()
        expect(preview).to_be_hidden()
        expect(page.locator("#sensor-history canvas").first).to_be_visible(timeout=30000)
        page.locator("#pause").click()
        page.locator("#reset").click()
        expect(preview).to_be_visible()
        page.evaluate("window.scrollTo({top:0, behavior:'instant'})")
        page.screenshot(path=out / "mobile-home.png")
    else:
        page.screenshot(path=out / "desktop-home.png")
    compare.click()
    expect(page.locator("#workbench")).to_be_visible(timeout=60000)
    expect(page.locator("#clock")).to_have_text("12.51 s / 17.56 s")
    page.get_by_role("button", name="6.31초 · 첫 집기 실패").click()
    off, on = page.locator(".panel.off"), page.locator(".panel.on")
    expect(off.locator(".readout b")).to_contain_text("종료")
    expect(on.locator(".readout b")).to_contain_text("재시도")
    expect(off.locator(".picture span")).to_contain_text("자세 기록")
    expect(on.locator(".picture span")).to_contain_text("자세 기록")
    expect(off.locator(".event-still")).to_have_attribute("data-event","empty-off")
    expect(on.locator(".event-still")).to_have_attribute("data-event","empty")
    expect(off.locator(".readout b")).to_contain_text("재시도를 꺼서 실행 종료")
    expect(page.locator("#evaluation")).to_contain_text("실제 재시도 0건")
    page.screenshot(path=out / ("mobile.png" if mobile else "desktop.png"), full_page=True)
    page.locator("#play").click()
    page.wait_for_timeout(400)
    page.locator("#play").click()
    paused = page.locator("#clock").inner_text()
    page.wait_for_timeout(120)
    assert paused == page.locator("#clock").inner_text() and not paused.startswith("6.31")
    expect(off.locator("time")).to_have_text("6.31 s")
    expect(off.locator(".terminal")).to_have_text("6.31초 종료 · 마지막 자세")
    expect(on.locator(".terminal")).to_be_hidden()
    marker = page.get_by_role("button", name="시간축에서 두 번째 집기 보기")
    marker.click()
    expect(marker).to_have_attribute("aria-current","time")
    expect(on.locator(".event-still")).to_have_attribute("data-event","grasp")
    expect(off.locator(".event-still")).to_have_attribute("data-event","empty-off")
    expect(on.locator(".readout small")).to_contain_text("12.50 s 닫기 명령 0")
    expect(page.locator("#clock")).to_have_text("12.51 s / 17.56 s")
    expect(on.locator(".readout small")).to_contain_text("43.869 mm")
    page.get_by_role("button", name="17.56초 · 배치 결과").click()
    expect(on.locator(".event-still")).to_have_attribute("data-event","placed")
    expect(on.locator(".readout b")).to_have_text("배치 성공")
    expect(on.locator(".picture span")).to_have_text("자세 기록 17.56 s")
    expect(on.locator(".readout small")).to_contain_text("2.29 mm")
    page.locator("#reset").click()
    expect(page.locator("#clock")).to_contain_text("0.00 s")
    expect(off.locator(".terminal")).to_be_hidden()
    expect(on.locator(".terminal")).to_be_hidden()
    page.locator("#timeline").focus()
    page.keyboard.press("End")
    expect(page.locator("#clock")).to_have_text("17.56 s / 17.56 s")
    page.locator("#photos button").nth(2).click()
    expect(page.locator("#clock")).to_contain_text("6.61 s")
    expect(page.locator("#selected-observation")).to_have_text("재시도 켬 · 후면 카메라 · 6.61초")
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
    page.wait_for_function("""() => {
        const images = [...document.querySelectorAll('#photos img')];
        return images.length === 2 && images.every(image => image.complete && image.naturalWidth > 0);
    }""")
    with page.expect_download() as download:
        page.get_by_role("link",name="관측·행동 데이터 받기 (JSONL)").click()
    samples = Path(download.value.path()).read_text().splitlines()
    assert len({json.loads(line)["sample_id"] for line in samples}) == 86
    assert not errors,errors
    context.close()


def check_without_webgl(browser, url, mobile):
    width, height = (390, 844) if mobile else (1440, 1000)
    context = browser.new_context(viewport={"width": width, "height": height},
                                  ignore_https_errors=True, user_agent="Mozilla/5.0")
    page = context.new_page()
    page.goto(url, wait_until="domcontentloaded")
    expect(page.locator("#phase")).to_have_text("이 브라우저에서는 실시간 3D를 열 수 없습니다")
    expect(page.get_by_text("조건과 방법을 고르고 실행하세요.", exact=True)).not_to_be_visible()
    expect(page.locator("#hero-run")).to_be_disabled()
    page.get_by_role("link", name="기록으로 두 실행 비교하기").click()
    expect(page.locator("#clock")).to_have_text("6.31 s / 17.56 s")
    page.get_by_role("button", name="12.51초 · 두 번째 집기").click()
    expect(page.locator(".panel.off time")).to_have_text("6.31 s")
    expect(page.locator(".panel.on .event-still")).to_have_attribute("data-event", "grasp")
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
        blocked = pw.chromium.launch(executable_path="/usr/bin/chromium", headless=True,
                                     args=["--no-sandbox", "--disable-webgl"])
        for mobile in (False, True):
            check_without_webgl(blocked, args.url, mobile)
            print("mobile" if mobile else "desktop", "no-WebGL fallback passed", flush=True)
        blocked.close()

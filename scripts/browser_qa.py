"""Browser QA of exact static files via Playwright routing; no preview server needed.
Optionally --url https://... validates the actual public deployment with real HTTP.
Screenshots are real Chromium captures. Browser dependencies are development-only.
"""
import argparse,json,mimetypes,time,shutil
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]

def run(base=None,output='docs/v2/browser-validation.json',screenshots='dist/screenshots'):
    shots=ROOT/screenshots;shots.mkdir(parents=True,exist_ok=True)
    reports=[]
    with sync_playwright() as pw:
        browser=pw.chromium.launch(executable_path=shutil.which('chromium'),headless=True,args=['--no-sandbox'])
        for name,width,height in [('desktop',1440,1000),('mobile',390,844)]:
            errors=[];missing=[]
            ctx=browser.new_context(viewport={'width':width,'height':height},device_scale_factor=1,ignore_https_errors=True,user_agent='Mozilla/5.0',is_mobile=name=='mobile',has_touch=name=='mobile')
            page=ctx.new_page();page.on('pageerror',lambda error:errors.append(str(error)))
            if not base:
                def route(request):
                    from urllib.parse import urlparse,unquote
                    path=unquote(urlparse(request.request.url).path)
                    f=(ROOT/'dist'/('index.html' if path=='/' else path.lstrip('/'))).resolve()
                    if not f.is_relative_to((ROOT/'dist').resolve()) or not f.is_file():
                        if not path.startswith('/api/') and path!='/favicon.ico':missing.append(path)
                        request.fulfill(status=404,body='not found');return
                    request.fulfill(status=200,body=f.read_bytes(),content_type=mimetypes.guess_type(str(f))[0] or 'application/octet-stream')
                page.route('https://reachbench.test/**',route)
            url=base or 'https://reachbench.test/'
            page.goto(url,wait_until='networkidle')
            page.wait_for_function("document.querySelector('#left-sprite').naturalWidth > 0 && !document.querySelector('#compare').disabled")
            assert page.locator('#baseline-rate').inner_text()=='2.0%'
            assert page.locator('#improved-rate').inner_text()=='59.0%'
            assert page.locator('#left-frame').get_attribute('data-trace-index')=='0'
            assert not page.evaluate('document.documentElement.scrollWidth > innerWidth')
            page.screenshot(path=str(shots/f'{name}-comparison.png'),full_page=True)
            page.locator('#compare').click();page.wait_for_timeout(500)
            page.locator('#compare').click();paused=page.locator('#time-label').inner_text();page.wait_for_timeout(200);assert page.locator('#time-label').inner_text()==paused
            assert paused!='0.00 s'
            page.locator('#time').fill('1000');page.locator('#time').dispatch_event('input')
            assert page.locator('#left-frame').get_attribute('data-trace-index')==page.locator('#scene').get_attribute('data-left-index')
            assert page.locator('#right-frame').get_attribute('data-trace-index')==page.locator('#scene').get_attribute('data-right-index')
            page.locator('#reset').click();assert page.locator('#time-label').inner_text()=='0.00 s'
            page.locator('#condition').select_option('occluded')
            page.wait_for_function("document.querySelector('#condition-note').textContent.includes('회색') && document.querySelector('#time').disabled")
            assert '이동 없음' in page.locator('#right-result').inner_text()
            assert '인식 정확도' in page.locator('#causal-chain').inner_text()
            assert page.locator('#compare').is_disabled()
            page.locator('#condition').select_option('calibration')
            page.wait_for_function("document.querySelector('#scenario-title').textContent.includes('65') && !document.querySelector('#collision-jump').hidden")
            page.locator('#collision-jump').click()
            assert '접촉' in page.locator('#contact-detail').inner_text()
            assert page.locator('#scene').get_attribute('data-right-index')==page.locator('#right-frame').get_attribute('data-trace-index')
            page.screenshot(path=str(shots/f'{name}-collision.png'),full_page=True)
            page.locator('#to-calibration').click()
            page.wait_for_function("document.querySelector('#right-method').textContent.includes('기준점') && !document.querySelector('#compare').disabled")
            assert page.locator('#baseline-rate').inner_text()=='40.0%' and page.locator('#improved-rate').inner_text()=='100.0%'
            assert '목표 도달' in page.locator('#right-result').inner_text()
            page.locator('#time').fill('1000');page.locator('#time').dispatch_event('input')
            page.screenshot(path=str(shots/f'{name}-calibration.png'),full_page=True)
            page.locator('#condition').select_option('markers_missing')
            page.wait_for_function("document.querySelector('#right-result').textContent.includes('보정 근거 부족')")
            assert '이동 보류' in page.locator('#causal-chain').inner_text()
            page.locator('#condition').select_option('board_shift')
            page.wait_for_function("document.querySelector('#scenario-title').textContent.includes('배치 오류') && document.querySelector('#right-result').textContent.includes('오차 초과')")
            page.locator('[data-tab=results]').click();assert page.locator('#study-table tr').count()==5
            assert not page.evaluate('document.documentElement.scrollWidth > innerWidth')
            # Failure drill-down opens its real scene, seed and condition.
            page.locator('#legacy-failures button[data-run^="occluded"]').click()
            page.wait_for_function("document.querySelector('#condition').value==='occluded' && document.querySelector('#time').disabled")
            assert page.locator('#experiment').is_visible()
            page.locator('#condition').select_option('nominal')
            page.wait_for_function("document.querySelector('#scenario-title').textContent==='기본 조명' && !document.querySelector('#compare').disabled")
            page.locator('#seed').select_option('1019')
            page.wait_for_function("document.querySelector('#run-id').textContent.includes('1019')")
            page.locator('#show-overlay').uncheck();assert not page.locator('#overlay').is_visible()
            page.locator('[data-tab=method]').click();assert page.locator('#method').is_visible()
            overflow=page.evaluate('document.documentElement.scrollWidth > innerWidth')
            assert not overflow, f'{name}: horizontal overflow'
            assert not errors,errors
            assert not missing,missing
            reports.append({'viewport':name,'width':width,'height':height,'passed':True,'horizontal_overflow':overflow,'page_errors':errors,'missing_assets':missing,'checks':['recorded frames loaded','play/pause/reset','seek and frame/2D exact-index sync','occlusion no-motion explanation','recorded collision jump','legacy/calibration suite switch','missing references stop','shifted references failure','failure drill-down','seed switch','overlay toggle','evaluation tables','tabs']})
            ctx.close()
        browser.close()
    report={'mode':'public-deployment' if base else 'static-files-routed-in-Chromium','base_url':base,'browser':'installed Chromium via Playwright','tls_note':'Browser proxy certificate verification disabled in test context; not a TLS audit. Public HTTP response checks use system TLS separately.','screenshots':screenshots,'reports':reports}
    Path(output).parent.mkdir(parents=True,exist_ok=True);Path(output).write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--url');ap.add_argument('--output',default='docs/v2/browser-validation.json');ap.add_argument('--screenshots',default='dist/screenshots');a=ap.parse_args();run(a.url,a.output,a.screenshots)

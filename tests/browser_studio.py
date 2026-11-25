"""Real Chromium/WebGL flow checks. Start an HTTP server; pass --url and --out."""
import argparse,asyncio,json
from pathlib import Path
from playwright.async_api import async_playwright
ap=argparse.ArgumentParser();ap.add_argument('--url',default='http://127.0.0.1:4173');ap.add_argument('--out',default='work/v3/browser');ap.add_argument('--ignore-https-errors',action='store_true',help='Only for a test environment with an untrusted TLS inspection proxy');args=ap.parse_args()
out=Path(args.out);out.mkdir(parents=True,exist_ok=True)
async def main():
 errors=[];results=[];checks=[]
 async with async_playwright() as p:
  b=await p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox','--enable-unsafe-swiftshader','--use-angle=swiftshader'])
  page=await b.new_page(viewport={'width':1440,'height':1000},ignore_https_errors=args.ignore_https_errors,user_agent='Mozilla/5.0')
  page.on('pageerror',lambda e:errors.append(str(e)))
  await page.goto(args.url,wait_until='networkidle',timeout=90000)
  await page.wait_for_function('window.reachbench?.engine.ready',timeout=90000)
  assert await page.locator('#rate-base').inner_text()=='25%'
  assert await page.locator('#rate-feedback').inner_text()=='75%'
  await page.screenshot(path=str(out/'desktop.png'),full_page=True)
  await page.locator('#run').click();await page.wait_for_timeout(700);await page.locator('#pause').click()
  t=await page.evaluate('reachbench.engine.elapsed');await page.wait_for_timeout(250)
  assert await page.evaluate('reachbench.engine.elapsed')==t and t>0
  await page.locator('#reset').click();assert await page.evaluate('reachbench.engine.elapsed')==0
  assert await page.locator('.sensor-card').count()==0
  checks.append('live play, pause, reset clears time and sensor cards')
  for condition in ['occluded','normal','shifted','unreachable']:
   for method in ['one_shot','feedback']:
    await page.locator(f'[data-condition="{condition}"]').click();await page.locator(f'[data-method="{method}"]').click();await page.locator('#run').click()
    r=await page.evaluate('''()=>{const e=reachbench.engine;for(let i=0;i<18000&&e.running;i++)e.step();e.sync();return e.result;}''')
    assert r is not None and r['method']==method and r['condition']==condition
    if condition=='normal' or (condition in ['occluded','shifted'] and method=='feedback'):assert r['success'],r
    else:assert not r['success'],r
    assert r['retries']<=1
    results.append(r);print('live',condition,method,r['reason'],flush=True)
  checks.append('all 8 live seed 100 condition/method combinations')
  await page.locator('[data-record="occluded-100-one_shot"]').click()
  await page.wait_for_function('reachbench.state.replay && reachbench.state.method==="one_shot"')
  assert '목표를 찾지 못함' in await page.locator('#result').inner_text()
  assert await page.locator('#run').is_disabled()
  assert await page.locator('#phase').inner_text()=='작업 중단'
  checks.append('zero-duration failed record opens with sensor and terminal failure')
  await page.locator('[data-record="occluded-100-feedback"]').click()
  await page.wait_for_function('reachbench.state.replay && reachbench.state.method==="feedback"')
  await page.locator('#run').click();await page.wait_for_timeout(300);await page.locator('#pause').click()
  await page.locator('#scrub').fill('500');assert await page.evaluate('reachbench.engine.elapsed')>4
  await page.locator('#reset').click();assert await page.evaluate('reachbench.engine.elapsed')==0
  await page.locator('#scrub').fill('1000');assert await page.locator('#phase').inner_text()=='작업 완료'
  assert await page.locator('#pause').is_disabled()
  checks.append('record play, pause, scrub middle/end, reset, terminal result')
  await page.screenshot(path=str(out/'recorded.png'),full_page=True)
  await page.locator('#return-live').click();assert not await page.evaluate('reachbench.state.replay')
  await page.locator('#new-scene').click();assert await page.evaluate('reachbench.state.seed')==101
  checks.append('return to live and new seeded layout')
  await page.set_viewport_size({'width':390,'height':844});await page.evaluate('scrollTo(0,0)')
  assert await page.evaluate('document.documentElement.scrollWidth<=innerWidth')
  await page.screenshot(path=str(out/'mobile.png'),full_page=True)
  await page.locator('[data-condition="occluded"]').click();await page.locator('[data-method="feedback"]').click();await page.locator('#run').click()
  r=await page.evaluate('''()=>{const e=reachbench.engine;for(let i=0;i<18000&&e.running;i++)e.step();e.sync();return e.result;}''');assert r['success'],r
  await page.locator('#compare-other').click()
  await page.wait_for_function('reachbench.engine.result!==null')
  assert await page.evaluate('reachbench.engine.result.reason')=='target_missing'
  checks.append('390px viewport no horizontal overflow; live run and same-scene compare')
  # Resource failure must preserve engine-independent recorded evidence.
  fallback=await b.new_page(viewport={'width':1200,'height':900},ignore_https_errors=args.ignore_https_errors,user_agent='Mozilla/5.0')
  await fallback.route('**/assets/workcell.mjb.gz',lambda route:route.abort())
  await fallback.goto(args.url,wait_until='networkidle',timeout=90000)
  await fallback.locator('#error').wait_for(state='visible')
  assert await fallback.locator('#phase').inner_text() == '이 브라우저에서는 실시간 3D를 열 수 없습니다'
  assert not (await fallback.locator('#phase-note').inner_text()).strip()
  assert await fallback.get_by_role('link',name='기록으로 두 실행 비교하기').is_visible()
  await fallback.locator('[data-record="occluded-100-feedback"]').click()
  await fallback.wait_for_selector('.sensor-card img')
  assert '트레이 배치 성공' in await fallback.locator('#result').inner_text()
  assert await fallback.locator('#events li').count()>5
  checks.append('blocked model: original sensor images/events/result remain accessible')
  await b.close()
 assert not errors,errors
 report={'url':args.url,'browser':'Chromium / software WebGL (SwiftShader), desktop 1440x1000 and mobile viewport 390x844','passed':True,'checks':checks,'live_results':results,'errors':errors,'note':'Physics assertions advance actual WASM steps in batches; not a wall-clock performance benchmark or physical mobile-device test.'}
 (out/'validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
 print(json.dumps({'passed':True,'checks':checks},ensure_ascii=False),flush=True)
asyncio.run(main())

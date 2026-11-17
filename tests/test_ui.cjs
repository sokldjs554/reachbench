// DOM/data integration; browser_qa.py tests actual rendering and playback.
const {JSDOM}=require('jsdom');
const fs=require('fs'),path=require('path'),assert=require('assert');
const root=path.resolve('dist'),dom=new JSDOM(fs.readFileSync(root+'/index.html','utf8'),{runScripts:'outside-only',url:'https://example.test/'}),w=dom.window;
w.requestAnimationFrame=()=>{};w.scrollTo=()=>{};
w.Image=class {set src(v){assert(fs.existsSync(path.join(root,v.split('?')[0])));queueMicrotask(()=>this.onload());}};
w.fetch=async url=>url.startsWith('/api')?{ok:false,json:async()=>({})}:{ok:true,json:async()=>JSON.parse(fs.readFileSync(path.join(root,url.split('?')[0]),'utf8'))};
w.eval(fs.readFileSync(root+'/app.js','utf8').replace('export {frameAt,fmt,pct};',''));
const $=x=>w.document.querySelector(x),pause=()=>new Promise(r=>setTimeout(r,40));
function change(id,value){$(id).value=value;$(id).dispatchEvent(new w.Event('change'));}
async function verify(ids,dir){await pause();assert($('#error').hidden,$('#error').textContent);for(let i=0;i<2;i++){const r=JSON.parse(fs.readFileSync(`${root}/${dir}/${ids[i]}.json`));assert($('#'+['left','right'][i]+'-result').textContent.includes(r.endpoint_error_mm.toFixed(1)));}$('#time').value=1000;$('#time').dispatchEvent(new w.Event('input'));for(const side of ['left','right'])assert.equal($('#'+side+'-frame').dataset.traceIndex,$('#scene').dataset[side+'Index']);}
(async()=>{
 await pause();assert.equal($('#baseline-rate').textContent,'2.0%');assert.equal($('#improved-rate').textContent,'59.0%');assert.equal(w.document.querySelectorAll('#metrics-table tr').length,4);
 for(const condition of ['nominal','dim','clutter','occluded','calibration']){change('#condition',condition);await verify(['baseline','improved'].map(m=>`${condition}-1000-${m}`),'data');if(condition==='occluded'){assert($('#time').disabled);assert($('#right-result').textContent.includes('이동 없음'));}}
 $('#suite-calibration').click();await pause();assert.equal($('#baseline-rate').textContent,'40.0%');assert.equal($('#improved-rate').textContent,'100.0%');
 for(const bias of [0,20,40,65,100]){change('#bias',String(bias));await verify(['uncorrected','reference'].map(m=>`standard-${bias}-3000-${m}`),'data-v2');}
 for(const profile of ['markers_missing','board_shift']){change('#condition',profile);await verify(['uncorrected','reference'].map(m=>`${profile}-65-3000-${m}`),'data-v2');}
 assert.equal(w.document.querySelectorAll('#study-table tr').length,5);assert($('#local-form').hidden);
 $('#reset').click();assert.equal($('#time-label').textContent,'0.00 s');
 const report={passed:true,mode:'jsdom 26: DOM/data only',checks:['five legacy conditions and outcome values','five calibration biases and outcome values','both reference stress profiles','frame/2D sample index consistency','headline denominators','evaluation table row counts','local-only gate','reset']};
 fs.mkdirSync('docs/v2',{recursive:true});fs.writeFileSync('docs/v2/dom-validation.json',JSON.stringify(report,null,2));console.log(JSON.stringify(report));
})().catch(e=>{console.error(e);process.exitCode=1;});

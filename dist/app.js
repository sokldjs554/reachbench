const $=s=>document.querySelector(s);
const CONDITIONS={nominal:['기본 조명','고정 카메라와 정상 조명. 목표·장애물 위치가 seed에 따라 달라집니다.'],dim:['어두운 조명','밝기 38% + 픽셀 잡음 σ=5. 고정 RGB 임계값과 HSV 분할을 비교합니다.'],clutter:['추가 장애물','장애물을 하나 더 추가합니다. 목표에 닿을 수 있어도 링크 전체의 경로가 막힐 수 있습니다.'],occluded:['목표 가림','초기 이미지에서 목표를 완전히 가립니다. 검출하지 못하면 이동을 시작하지 않습니다.'],calibration:['보정 오차','카메라→작업 공간 변환에 X축 +65 mm 오차를 주입합니다.']};
const REASONS={reached:['목표 도달','충돌 없이 목표의 35 mm 이내에 도착했습니다.'],collision:['충돌로 정지','기록된 자세에서 링크와 장애물의 접촉을 검출했습니다.'],target_missing:['목표 검출 실패','목표 픽셀이 검출되지 않아 이동을 시작하지 않았습니다.'],no_path:['경로 탐색 실패','보수적 여유 거리와 관절 격자 내에서 경로를 찾지 못했습니다.'],goal_blocked:['목표 자세 차단','추정 장애물과 충돌하지 않는 목표 관절 자세가 없습니다.'],start_blocked:['시작 자세 차단','추정 장애물의 안전 여유 때문에 초기 경로를 연결하지 못했습니다.'],unreachable:['도달 범위 밖','추정 목표의 역기구학 해가 관절 한계 내에 없습니다.'],position_error:['위치 오차 초과','충돌 없이 움직였지만 실제 목표와 35 mm 이상 떨어져 있습니다.']};
const METHOD_NAMES={baseline:'RGB + 직접 접근',perception:'HSV + 직접 접근',planning:'RGB + A*',improved:'HSV + A*'};
let summary,condition='nominal',seed=1000,runs=[],playing=false,elapsed=0,previous=0,requestId=0;
const color={baseline:'#d28b63',improved:'#60c3a4'};
const fmt=(n,d=1)=>n==null?'—':Number(n).toFixed(d);
const pct=n=>(n*100).toFixed(1)+'%';
function tag(name,attrs={},content=''){return `<${name} ${Object.entries(attrs).map(([k,v])=>`${k}="${v}"`).join(' ')}>${content}</${name}>`;}
function xy(p){return [400+p[0]*380,295-p[1]*380];}
function circle(p,r,attrs){const [cx,cy]=xy(p);return tag('circle',{cx,cy,r:r*380,...attrs});}
function polyline(points,attrs){return tag('polyline',{points:points.map(p=>xy(p).join(',')).join(' '),fill:'none',...attrs});}
function textAt(p,t,attrs={}){const [x,y]=xy(p);return tag('text',{x,y,fill:'#b8ccc6','font-size':11,'font-family':'monospace',...attrs},t);}
function currentFrame(r,t){return r.trace[Math.min(r.trace.length-1,Math.floor(t/.05+1e-7))];}
function draw(){
 if(!runs.length)return;
 const scene=runs[0].scene;let svg='';
 for(let x=-1;x<=1;x+=.2)svg+=polyline([[x,-.7],[x,.7]],{stroke:'#263d42','stroke-width':1});
 for(let y=-.6;y<=.6;y+=.2)svg+=polyline([[-1,y],[1,y]],{stroke:'#263d42','stroke-width':1});
 svg+=circle([-.5,0],1,{stroke:'#3d5557','stroke-width':1,'stroke-dasharray':'4 5',fill:'none'});
 svg+=polyline([[-.92,-.64],[-.72,-.64]],{stroke:'#93aaa5','stroke-width':2});svg+=textAt([-.92,-.60],'200 mm',{'font-size':10});
 svg+=polyline([[.72,-.6],[.87,-.6]],{stroke:'#71908d','stroke-width':1.5});svg+=polyline([[.72,-.6],[.72,-.45]],{stroke:'#71908d','stroke-width':1.5});svg+=textAt([.9,-.61],'X');svg+=textAt([.71,-.42],'Y');
 for(const [i,o] of scene.obstacles.entries()){
  svg+=circle(o,o[2]+.037,{fill:'none',stroke:'#4d7190','stroke-dasharray':'4 4','stroke-width':1});
  svg+=circle(o,o[2],{fill:'#3b6283',stroke:'#6e99bf','stroke-width':1.5});
  svg+=textAt([o[0]+o[2]+.025,o[1]+.01],`OBS ${i+1}`,{'font-size':9,fill:'#89a7bd'});
 }
 svg+=circle(scene.target,.035,{fill:'#d07557',stroke:'#efb294','stroke-width':2});svg+=circle(scene.target,.065,{fill:'none',stroke:'#d79d7e','stroke-dasharray':'3 4','stroke-width':1});
 svg+=textAt([scene.target[0]+.08,scene.target[1]+.035],'TARGET',{'font-size':10,fill:'#e1b294'});
 const improved=runs.find(r=>r.method==='improved');if(improved?.detected.target){const p=improved.detected.target.xy;svg+=circle(p,.018,{fill:'none',stroke:color.improved,'stroke-width':1.4});}
 for(const r of runs){const pts=r.trace.map(f=>f.joints[2]);svg+=polyline(pts,{stroke:color[r.method],'stroke-width':1.5,opacity:.35,'stroke-dasharray':'3 4'});const f=currentFrame(r,elapsed);const idx=r.trace.indexOf(f);svg+=polyline(pts.slice(0,idx+1),{stroke:color[r.method],'stroke-width':2.3,opacity:.85});}
 for(const r of runs){const f=currentFrame(r,elapsed);const c=color[r.method];svg+=polyline(f.joints,{stroke:'#0c1b20','stroke-width':24,'stroke-linecap':'round','stroke-linejoin':'round'});svg+=polyline(f.joints,{stroke:c,'stroke-width':16,'stroke-linecap':'round','stroke-linejoin':'round',opacity:r.method==='baseline'?.65:.95});for(const p of f.joints)svg+=circle(p,.017,{fill:'#15292b',stroke:c,'stroke-width':2});if(f.collision)svg+=circle(f.joints[2],.06,{fill:'none',stroke:'#f3a47a','stroke-width':2});}
 svg+=circle([-.5,0],.065,{fill:'#283e40',stroke:'#839e98','stroke-width':2});svg+=circle([-.5,0],.022,{fill:'#8da39b'});svg+=textAt([-.7,.105],'BASE / 2-DOF',{'font-size':10});
 $('#scene').innerHTML=svg;$('#time-label').textContent=fmt(elapsed,2)+' s';const max=Math.max(...runs.map(r=>r.duration_s));$('#time').disabled=max===0;$('#time').value=String(max>0?Math.round(elapsed/max*1000):0);
 $('#play').textContent=playing?'Ⅱ':'▶';
}
function cards(){for(const r of runs){const [label,why]=REASONS[r.reason]||[r.reason,''];$('#'+r.method+'-result').innerHTML=`<div class="result-title"><span>${r.method==='baseline'?'기준 방법':'개선 방법'} · 최종 결과</span><span class="outcome ${r.success?'ok':'fail'}">${label}</span></div><div><strong>${fmt(r.endpoint_error_mm)}</strong><small>mm · 최종 위치 오차</small></div><p>${why}</p>`;}}
function sensors(){const r=runs.find(r=>r.method==='improved');$('#camera').src=r.id.startsWith('local')?`data/frames/${r.id}/camera.png?v=${requestId}`:`data/cameras/${r.condition}-${r.seed}.png`;let s='';if(r.detected.target){const t=r.detected.target;s+=tag('circle',{cx:t.pixel[0],cy:t.pixel[1],r:Math.sqrt(t.area/Math.PI)+4,fill:'none',stroke:'#6affcb','stroke-width':1.5});s+=tag('text',{x:t.pixel[0]+10,y:t.pixel[1]-10,fill:'#174f3e','font-size':9},'TARGET');}for(const o of r.detected.obstacles)s+=tag('circle',{cx:o.pixel[0],cy:o.pixel[1],r:Math.sqrt(o.area/Math.PI)+3,fill:'none',stroke:'#8fc6ff','stroke-width':1.2});$('#overlay').innerHTML=s;
 $('#perception').innerHTML=[['목표 위치 X / Y',r.detected.target?r.detected.target.xy.map(x=>fmt(x,3)).join(' / ')+' m':'검출 없음'],['목표 인식 오차',fmt(r.perception_error_mm)+' mm'],['인식한 장애물',r.detected.obstacles.length+' 개'],['인식 처리 시간',fmt(r.perception_ms,2)+' ms'],['계획 처리 시간',fmt(r.planning_ms,2)+' ms']].map(([k,v])=>`<div><dt>${k}</dt><dd>${v}</dd></div>`).join('');
 $('#action').textContent=r.frames>1?`A* 경로의 관절각을 ${r.frames}개 자세로 실행했습니다. ${REASONS[r.reason][1]}`:`이동 보류. ${REASONS[r.reason][1]}`;
 $('#snapshots').innerHTML=['start','middle','end'].map((n,i)=>`<img src="${n==='start'?$('#camera').getAttribute('src'):`data/frames/${r.id}/${n}.png?v=${requestId}`}" alt="개선 방법 ${['시작','중간','종료'][i]} 렌더링">`).join('');
 $('#download-run').href='data/'+r.id+'.json';$('#download-run').hidden=r.id.startsWith('local');
}
async function loadScene(){const id=++requestId;playing=false;elapsed=0;$('#compare').disabled=true;$('#error').hidden=true;try{const data=await Promise.all(['baseline','improved'].map(async method=>{const res=await fetch(`data/${condition}-${seed}-${method}.json`);if(!res.ok)throw Error('실험 기록을 불러오지 못했습니다.');return res.json();}));if(id!==requestId)return;runs=data;$('.record-label').textContent='● 실제 실행 기록 · 사전 계산된 시뮬레이션';$('#run-id').textContent=`${condition.toUpperCase()} / ${seed}`;$('#condition-note').textContent=CONDITIONS[condition][1];cards();sensors();draw();}catch(e){$('#error').textContent=e.message;$('#error').hidden=false;}finally{if(id===requestId)$('#compare').disabled=false;}}
function results(){const m=summary.metrics;$('#baseline-rate').textContent=pct(m.baseline.all.success_rate);$('#improved-rate').textContent=pct(m.improved.all.success_rate);$('#sample-count').textContent=`${m.baseline.all.n}개 장면 × 4개 방법 · 실물 검증 없음`;
 $('#metrics-table').innerHTML=Object.keys(METHOD_NAMES).map(k=>{const r=m[k].all;return `<tr><td>${METHOD_NAMES[k]}</td><td>${r.successes} / ${r.n}</td><td>${pct(r.success_rate)} (${r.wilson95.map(pct).join('–')})</td><td>${r.detected_n}</td><td>${fmt(r.perception_error_mean_mm)} mm</td><td>${fmt(r.perception_median_ms,2)} ms</td><td>${fmt(r.planning_median_ms,2)} ms</td></tr>`;}).join('');
 $('#condition-bars').innerHTML=Object.keys(CONDITIONS).map(c=>`<div class="bar-row"><span>${CONDITIONS[c][0]}</span><div class="bar-group">${['baseline','improved'].map(k=>`<div class="bar-track" aria-label="${METHOD_NAMES[k]} ${CONDITIONS[c][0]} ${pct(m[k][c].success_rate)}"><i class="${k}" style="width:${m[k][c].success_rate*100}%"></i><span>${m[k][c].successes}/${m[k][c].n}</span></div>`).join('')}</div></div>`).join('');
 $('#failures').innerHTML=Object.entries(m.improved.all.reasons).filter(([k])=>k!=='reached').map(([k,n])=>`<div class="failure-row"><b>${REASONS[k]?.[0]||k}</b><span>${n} episodes</span><p>${REASONS[k]?.[1]||''}</p></div>`).join('');
 $('#protocol').innerHTML=`<p>Seed ${summary.config.seeds[0]}–${summary.config.seeds.at(-1)}, ${summary.config.conditions.length}개 조건 × ${summary.config.seeds.length}개 장면 × 4개 방법 = ${summary.episodes.length}회 실행. 성공: 최종 XY 오차 ≤35 mm이며 실행 중 장애물 충돌 없음. 시작하지 못한 경우도 실패로 포함합니다.</p>`;
}
function tab(name){document.querySelectorAll('.tabpage').forEach(p=>p.classList.toggle('active',p.id===name));document.querySelectorAll('.tabs button').forEach(b=>b.classList.toggle('active',b.dataset.tab===name));history.replaceState(null,'','#'+name);}
document.querySelectorAll('[data-tab]').forEach(b=>b.onclick=()=>tab(b.dataset.tab));
window.addEventListener('hashchange',()=>{if(['experiment','results','method'].includes(location.hash.slice(1)))tab(location.hash.slice(1));});
document.querySelector('a[href="#method"]').onclick=()=>tab('method');
document.querySelectorAll('[data-condition]').forEach(b=>b.onclick=()=>{condition=b.dataset.condition;document.querySelectorAll('[data-condition]').forEach(x=>x.classList.toggle('selected',x===b));loadScene();});
$('#seed').onchange=e=>{seed=Number(e.target.value);loadScene();};
function play(){if(!runs.length)return;const max=Math.max(...runs.map(r=>r.duration_s));if(elapsed>=max)elapsed=0;playing=!playing;draw();}
$('#compare').onclick=()=>{elapsed=0;playing=false;play();};$('#play').onclick=play;$('#reset').onclick=()=>{playing=false;elapsed=0;draw();};$('#time').oninput=e=>{playing=false;elapsed=Number(e.target.value)/1000*Math.max(...runs.map(r=>r.duration_s));draw();};$('#show-overlay').onchange=e=>$('#overlay').style.display=e.target.checked?'':'none';
function animate(timestamp){const delta=previous?Math.min((timestamp-previous)/1000,.1):0;previous=timestamp;if(playing&&runs.length){const max=Math.max(...runs.map(r=>r.duration_s));elapsed=Math.min(elapsed+delta,max);if(elapsed>=max)playing=false;draw();}requestAnimationFrame(animate);}requestAnimationFrame(animate);
$('#run-local').onclick=async()=>{const btn=$('#run-local');btn.disabled=true;playing=false;$('#local-status').textContent='Python 시뮬레이션 실행 중…';try{const res=await fetch('/api/run',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({condition,seed,target:[Number($('#target-x').value),Number($('#target-y').value)]})});const data=await res.json();if(!res.ok)throw Error(data.error);requestId++;runs=data.episodes;elapsed=0;$('.record-label').textContent='● 방금 실행한 Python 시뮬레이션 · 로컬';$('#run-id').textContent='FRESH LOCAL / '+seed;cards();sensors();draw();$('#local-status').textContent='새 Python 실행 완료 · 아래 결과는 저장된 평가 집계에 포함하지 않습니다.';}catch(e){$('#local-status').textContent=e.message;}finally{btn.disabled=false;}};
async function init(){try{const r=await fetch('data/summary.json');if(!r.ok)throw Error('평가 데이터를 불러오지 못했습니다. 페이지를 새로고침해 주세요.');summary=await r.json();seed=summary.config.seeds[0];$('#seed').innerHTML=summary.config.seeds.map(s=>`<option value="${s}">SCENE ${s}</option>`).join('');results();await loadScene();if(['results','method'].includes(location.hash.slice(1)))tab(location.hash.slice(1));}catch(e){$('#error').textContent=e.message;$('#error').hidden=false;$('#compare').disabled=true;}try{const r=await fetch('/api/health');const d=await r.json();if(d.mode==='fresh-local'){$('#local-form').hidden=false;$('#local-status').textContent='Python 로컬 엔진 연결됨';}else throw Error();}catch{$('#local-status').textContent='배포판: 저장된 실행 탐색 · 새 계산은 로컬에서 지원';}}
init();
export {currentFrame,fmt,pct};

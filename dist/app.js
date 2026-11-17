const $=selector=>document.querySelector(selector);
const CONDITIONS={nominal:['기본 조명','같은 입력에서 직접 접근과 장애물 회피 경로를 비교합니다.'],dim:['어두운 조명','밝기 38% + 픽셀 잡음. 인식 누락이 이동 보류로 이어지는지 확인하세요.'],clutter:['추가 장애물','장애물이 하나 더 있습니다. 손끝뿐 아니라 링크 전체의 충돌을 검사합니다.'],occluded:['목표 가림','초기 입력에 회색 패치를 덮었습니다. 사선 관찰 화면은 인식 입력이 아닙니다.'],calibration:['보정 오차 +65 mm','픽셀→좌표 변환의 X 편향. 평가용 실제 목표와 계획에 사용한 추정 위치를 비교하세요.']};
const PROFILES={standard:['정상 기준점','녹색 기준점의 등록 위치와 관측을 비교해 공통 XY 편향을 추정합니다.'],markers_missing:['기준점 2개만 보임','최소 3개가 필요합니다. 보정 근거가 부족하면 이동을 시작하지 않습니다.'],board_shift:['기준점 배치 오류 +50 mm','등록 위치와 달리 모든 기준점을 X로 50 mm 옮겼습니다. 잔차가 작아도 보정이 틀릴 수 있습니다.']};
const NAMES={baseline:'RGB + 직접 접근',perception:'HSV + 직접 접근',planning:'RGB + A*',improved:'HSV + A*',uncorrected:'HSV + A* · 보정 전',reference:'기준점 보정 + HSV + A*'};
const REASONS={reached:['목표 도달','충돌 없이 목표의 35 mm 이내에 도착'],collision:['충돌로 정지','링크와 장애물의 실제 접촉 검출'],target_missing:['목표 검출 실패','목표를 찾지 못해 이동 보류'],no_path:['경로 탐색 실패','추정 장애물과 관절 격자에서 경로를 찾지 못함'],goal_blocked:['목표 자세 차단','충돌 여유를 만족하는 목표 자세가 없음'],start_blocked:['시작 자세 차단','추정 장애물 때문에 초기 경로 연결 불가'],unreachable:['도달 범위 밖','관절 한계 내 역기구학 해 없음'],position_error:['목표 오차 초과','실제 목표와 35 mm 이상 떨어져 도착'],calibration_unavailable:['보정 근거 부족','기준점 검증 실패로 이동 보류']};
const COLORS=['#ad8be8','#58d5b1'];
const state={suite:'legacy',condition:'nominal',bias:65,seed:1000,runs:[],media:[],roots:[],elapsed:0,playing:false,requestId:0,local:false};
let legacy,study,previous=0;
const fmt=(n,d=1)=>n==null?'—':Number(n).toFixed(d);
const pct=n=>(n*100).toFixed(1)+'%';
async function json(url){const r=await fetch(url);if(!r.ok)throw Error(`기록을 불러오지 못했습니다: ${url}`);return r.json();}
function setTab(name){document.querySelectorAll('.tabpage').forEach(x=>x.classList.toggle('active',x.id===name));document.querySelectorAll('[data-tab]').forEach(x=>x.classList.toggle('active',x.dataset.tab===name));history.replaceState(null,'','#'+name);}
function configure(){
 const choices=state.suite==='legacy'?CONDITIONS:PROFILES;$('#condition').innerHTML=Object.entries(choices).map(([v,[label]])=>`<option value="${v}">${label}</option>`).join('');$('#condition').value=state.condition;
 const seeds=state.suite==='legacy'?legacy.config.seeds:study.config.seeds;$('#seed').innerHTML=seeds.map(s=>`<option value="${s}">${s}</option>`).join('');$('#seed').value=String(state.seed);
 $('#bias-label').hidden=state.suite==='legacy';$('#bias').value=String(state.bias);$('#bias').disabled=state.condition!=='standard';
 document.querySelectorAll('[data-suite]').forEach(x=>x.classList.toggle('selected',x.dataset.suite===state.suite));
 const rates=state.suite==='legacy'?[legacy.metrics.baseline.all,legacy.metrics.improved.all]:[study.metrics.standard.all.uncorrected,study.metrics.standard.all.reference];
 $('#baseline-rate').textContent=pct(rates[0].success_rate);$('#improved-rate').textContent=pct(rates[1].success_rate);
 $('#headline-left').textContent=state.suite==='legacy'?'RGB + 직접 접근':'HSV + A* · 보정 전';$('#headline-right').textContent=state.suite==='legacy'?'HSV + A*':'기준점 보정 + HSV + A*';
 $('#headline-scope').textContent=state.suite==='legacy'?'기존 실험 · 동일한 100개 장면':'새 실험 · 정상 기준점 100개 장면';
 $('#sample-count').textContent=state.suite==='legacy'?'5조건 × 20 seed · 성공 기준: 무충돌 + 35 mm 이내':'5편향 × 20 seed · 스트레스 40개 장면 별도 집계';
 $('#to-calibration').hidden=state.suite!=='legacy'||state.condition!=='calibration';
}
async function loadScene(){
 const req=++state.requestId;state.playing=false;state.elapsed=0;state.local=false;$('#compare').disabled=true;$('#error').hidden=true;
 const suite=state.suite,cond=state.condition,bias=state.bias,seed=state.seed;
 try{
  const methods=suite==='legacy'?['baseline','improved']:['uncorrected','reference'];
  const ids=methods.map(m=>suite==='legacy'?`${cond}-${seed}-${m}`:`${cond}-${bias}-${seed}-${m}`);
  const roots=ids.map(id=>suite==='legacy'?`media/legacy/${id}`:`data-v2/recordings/${id}`);
  const [runs,media]=await Promise.all([Promise.all(ids.map(id=>json(`${suite==='legacy'?'data':'data-v2'}/${id}.json`))),Promise.all(roots.map(r=>json(r+'/recording.json')))]);
  if(req!==state.requestId)return;
  state.runs=runs;state.media=media;state.roots=roots;
  for(let i=0;i<2;i++){if(media[i].run_id!==runs[i].id)throw Error('영상과 실행 기록 ID가 다릅니다.');for(const f of media[i].frames){if(f.t!==runs[i].trace[f.trace_index].t)throw Error('프레임 시간과 관절 기록이 다릅니다.');}}
  // Preload sprite pages so a scrub never shows a different frame while fetching.
  await Promise.all(media.flatMap((m,i)=>m.pages.map(p=>new Promise((resolve,reject)=>{const image=new Image();image.onload=resolve;image.onerror=()=>reject(Error('PyBullet 프레임을 불러오지 못했습니다.'));image.src=roots[i]+'/'+p.file;}))));
  if(req!==state.requestId)return;
  $('.record-label').textContent='● 사전 계산된 PyBullet 기록 재생';$('#run-id').textContent=`${suite==='legacy'?'기존':'보정'} / seed ${seed}`;
  const choice=(suite==='legacy'?CONDITIONS:PROFILES)[cond];$('#scenario-title').textContent=choice[0];$('#condition-note').textContent=choice[1];
  renderStatic();render();
 }catch(e){if(req===state.requestId){state.runs=[];$('#error').textContent=e.message;$('#error').hidden=false;}}
 finally{if(req===state.requestId)$('#compare').disabled=!state.runs.length||maxTime()===0;}
}
function maxTime(){return Math.max(0,...state.runs.map(r=>r.duration_s));}
function frameAt(media,time){let chosen=media.frames[0];for(const f of media.frames){if(f.t>time+1e-9)break;chosen=f;}return chosen;}
function activeFrame(i){const r=state.runs[i];return state.media[i]?frameAt(state.media[i],state.elapsed):{trace_index:Math.min(r.trace.length-1,Math.floor(state.elapsed/.05)),t:Math.min(r.duration_s,Math.floor(state.elapsed/.05)*.05)};}
function showSprite(i){const side=i===0?'left':'right',r=state.runs[i],meta=state.media[i],frame=activeFrame(i);$('#'+side+'-clock').textContent=`t = ${fmt(frame.t,2)} s`;const badge=$('#'+side+'-state');badge.className='frame-state';
 if(r.trace[frame.trace_index].collision){badge.textContent='▲ 충돌 · 정지';badge.classList.add('collision');}
 else if(state.elapsed>=r.duration_s){badge.textContent=r.success?'✓ 도달 · 종료':r.frames===1?'Ⅱ 이동 보류':'실행 종료';if(r.success)badge.classList.add('done');}
 else badge.textContent=state.playing?'▶ 기록 재생':'Ⅱ 기록 정지';
 const img=$('#'+side+'-sprite');if(!meta){img.hidden=true;return;}img.hidden=false;
 const page=meta.pages[frame.page],col=frame.tile%page.columns,row=Math.floor(frame.tile/page.columns),src=state.roots[i]+'/'+page.file+(state.local?'?v='+state.requestId:'');
 if(img.getAttribute('src')!==src)img.src=src;img.style.width=page.columns*100+'%';img.style.left=-col*100+'%';img.style.top='50%';img.style.transform=`translateY(-${(row+.5)/page.rows*100}%)`;
 $('#'+side+'-frame').dataset.traceIndex=String(frame.trace_index);$('#'+side+'-frame').dataset.time=String(frame.t);
}
function render(){
 if(!state.runs.length)return;
 state.elapsed=Math.min(state.elapsed,maxTime());for(let i=0;i<2;i++)showSprite(i);
 $('#time-label').textContent=fmt(state.elapsed,2)+' s';$('#time').disabled=maxTime()===0;$('#time').value=String(maxTime()?Math.round(state.elapsed/maxTime()*1000):0);$('#compare').textContent=state.playing?'Ⅱ 일시정지':'▶ 두 실행 재생';
 drawMap();renderContacts();
}
function tag(n,a={},c=''){return `<${n} ${Object.entries(a).map(([k,v])=>`${k}="${v}"`).join(' ')}>${c}</${n}>`;}
function point(p){return [405+p[0]*270,250-p[1]*270];}
function line(ps,a={}){return tag('polyline',{points:ps.map(p=>point(p).join(',')).join(' '),fill:'none',...a});}
function circle(p,r,a={}){const [cx,cy]=point(p);return tag('circle',{cx,cy,r:r*270,...a});}
function label(p,text,a={}){const [x,y]=point(p);return tag('text',{x,y,fill:'#e0ecf1','font-size':12,'font-family':'sans-serif',...a},text);}
function diamond(p,color){const [x,y]=point(p);return tag('polygon',{points:`${x},${y-8} ${x+8},${y} ${x},${y+8} ${x-8},${y}`,fill:'none',stroke:color,'stroke-width':2});}
function drawMap(){
 const s=state.runs[0].scene;let out='';for(let x=-1.4;x<=1.3;x+=.2)out+=line([[x,-.7],[x,.8]],{stroke:'#294353','stroke-width':1});for(let y=-.6;y<=.8;y+=.2)out+=line([[-1.4,y],[1.3,y]],{stroke:'#294353','stroke-width':1});
 for(const o of s.obstacles)out+=circle(o,o[2],{fill:'#3c79ac',stroke:'#aad1f2','stroke-width':2});
 for(let i=0;i<2;i++){
  const r=state.runs[i],f=activeFrame(i),pts=r.trace.map(t=>t.joints[2]);out+=line(pts,{stroke:COLORS[i],'stroke-width':1.5,opacity:.4,'stroke-dasharray':i===0?'7 5':'2 4'});out+=line(pts.slice(0,f.trace_index+1),{stroke:COLORS[i],'stroke-width':3,'stroke-dasharray':i===0?'7 5':''});
  const q=r.trace[f.trace_index].joints;out+=line(q,{stroke:'#102330','stroke-width':18,'stroke-linejoin':'round','stroke-linecap':'round'});out+=line(q,{stroke:COLORS[i],'stroke-width':10,opacity:.9,'stroke-linejoin':'round','stroke-linecap':'round'});for(const p of q)out+=circle(p,.018,{fill:'#122838',stroke:COLORS[i],'stroke-width':2});
  if(r.detected.target){out+=diamond(r.detected.target.xy,i===0?'#d4bfff':'#f6c45d');out+=line([s.target,r.detected.target.xy],{stroke:i===0?'#d4bfff':'#f6c45d','stroke-width':1.5,'stroke-dasharray':'3 4'});}
  for(const e of state.media[i]?.contacts||[])if(f.t>=e.t)for(const contact of e.contacts){const [x,y]=point(contact.point_on_robot);out+=tag('polygon',{points:`${x},${y-10} ${x+9},${y+7} ${x-9},${y+7}`,fill:'#ff6b60',stroke:'#fff','stroke-width':1.2});out+=label([contact.point_on_robot[0]+.055,contact.point_on_robot[1]-.06],`접촉 ${fmt(e.t,2)} s`,{fill:'#ffafa7','font-size':11});}
 }
 out+=circle(s.target,.035,{fill:'#bf5243',stroke:'#fff','stroke-width':2});const [tx,ty]=point(s.target);out+=tag('path',{d:`M ${tx-11} ${ty} h 22 M ${tx} ${ty-11} v 22`,stroke:'#fff','stroke-width':1.2});out+=label([s.target[0]-.04,s.target[1]+.095],'⊕ 실제 목표 · 평가 전용',{'font-size':12});
 out+=circle([-.5,0],.058,{fill:'#1b394b',stroke:'#c1d1d9','stroke-width':2});out+=label([-.75,.12],'로봇 베이스',{'font-size':11});
 out+=line([[-1.24,-.61],[-1.04,-.61]],{stroke:'#c3d6df','stroke-width':2});out+=label([-1.24,-.56],'200 mm',{'font-size':10});
 const rf=activeFrame(1);out+=tag('text',{x:18,y:25,fill:'#c4dbe5','font-size':12},`기준 ${fmt(activeFrame(0).t,2)} s / 개선 ${fmt(rf.t,2)} s · 프레임과 같은 샘플`);
 $('#scene').innerHTML=out;$('#scene').dataset.leftIndex=String(activeFrame(0).trace_index);$('#scene').dataset.rightIndex=String(rf.trace_index);
}
function renderStatic(){
 state.runs.forEach((r,i)=>{const side=i===0?'left':'right';$('#'+side+'-method').textContent=(i===0?'기준 · ':'개선 · ')+NAMES[r.method];const [name,reason]=REASONS[r.reason];const stopped=r.frames===1;
 $('#'+side+'-result').innerHTML=`<span class="result-status ${r.success?'ok':'fail'}">${r.success?'✓':'!'} ${name}</span><div class="result-error"><b>${fmt(r.endpoint_error_mm)}</b><small>mm</small></div><p>${reason}</p><span class="result-note">${stopped?'이동 없음 · 시작 손끝 → 실제 목표까지 남은 거리':'최종 손끝 → 평가용 실제 목표의 XY 거리'}</span>`;});
 const r=state.runs[1],before=r.detected_before||r.detected,det=r.detected;
 const camera=state.local?`data/frames/${r.id}/camera.png?v=${state.requestId}`:state.suite==='legacy'?`data/cameras/${r.condition}-${r.seed}.png`:`data-v2/cameras/${r.profile}-${r.bias_mm}-${r.seed}.png`;
 $('#camera').src=camera;let overlay='';if(det.target){const t=det.target;overlay+=tag('circle',{cx:t.pixel[0],cy:t.pixel[1],r:Math.sqrt(t.area/Math.PI)+5,fill:'none',stroke:'#fff','stroke-width':2});overlay+=tag('circle',{cx:t.pixel[0],cy:t.pixel[1],r:Math.sqrt(t.area/Math.PI)+7,fill:'none',stroke:'#00694e','stroke-width':1});}
 for(const m of r.reference_observations||[]){overlay+=tag('rect',{x:m.pixel[0]-7,y:m.pixel[1]-7,width:14,height:14,fill:'none',stroke:'#114c35','stroke-width':2});overlay+=tag('text',{x:m.pixel[0]+9,y:m.pixel[1],fill:'#173b29','font-size':12},'C'+(m.id+1));}$('#overlay').innerHTML=overlay;
 const inputText=r.scene.occlude?'25×25 회색 패치가 붉은 목표를 가립니다. 관찰용 사선 카메라는 인식에 사용하지 않습니다.':r.profile==='markers_missing'?'같은 RGB에 기준점이 2개만 보입니다.':r.profile==='board_shift'?'기준점을 실제로 50 mm 옮겼지만 등록 좌표는 그대로입니다.':'초기 상부 RGB 한 장에서 목표와 장애물을 찾습니다. 실행 중 새로 관측하지 않습니다.';
 const perceptionText=det.target?`목표 검출 ${det.target_pixels} px · 추정 X ${fmt(det.target.xy[0],3)}, Y ${fmt(det.target.xy[1],3)} m`:'목표 0 px · 위치 추정값 없음. 아래 거리는 인식 오차가 아닙니다.';
 const actionText=r.reason==='calibration_unavailable'?`이동 보류: 기준점 ${r.calibration.count}개 / 최소 3개. 보정 검증 실패로 정지합니다.`:r.frames===1?`이동 보류: ${REASONS[r.reason][1]}.`:`A*가 선택한 관절 경로를 ${r.frames}개 자세로 실행합니다.`;
 $('#causal-chain').innerHTML=[['01 입력',inputText],['02 인식',perceptionText],['03 선택한 행동',actionText],['04 최종 판정',r.frames===1?`미이동 상태의 손끝과 실제 목표 사이 거리 ${fmt(r.endpoint_error_mm)} mm. 인식 정확도 또는 주행 오차가 아닙니다.`:`${REASONS[r.reason][1]}. 최종 XY 거리 ${fmt(r.endpoint_error_mm)} mm.`]].map(([h,t])=>`<li><strong>${h}</strong><p>${t}</p></li>`).join('');
 const gt=r.scene.target;let detail=`<p>⊕ 실제 목표(평가용): <b>(${gt.map(x=>fmt(x,3)).join(', ')}) m</b></p>`;
 if(det.target){detail+=`<p>◇ ${r.reason==='calibration_unavailable'?'인식된 추정 (계획에 사용 안 함)':'계획 입력의 추정'}: <b>(${det.target.xy.map(x=>fmt(x,3)).join(', ')}) m</b> · 목표 인식 오차 <b>${fmt(r.perception_error_mm)} mm</b></p>`;
 if(r.calibration){detail+=`<p>보정 전 추정 X ${fmt(before.target.xy[0],3)} m → 보정 후 ${fmt(det.target.xy[0],3)} m</p><p>기준점 ${r.calibration.count}개 · 추정 편향 ${r.calibration.offset_xy?r.calibration.offset_xy.map(x=>fmt(x*1000)).join(' / ')+' mm':'산출 안 함'} · 최대 잔차 ${fmt(r.calibration.residual_max_mm)} mm</p>`;}}
 else detail+='<p>추정 위치 없음. 평가용 실제 목표는 계획기에 전달되지 않습니다.</p>';
 detail+='<p>정답 좌표는 거리 계산과 이 설명에만 사용합니다. 보정기의 알려진 입력은 작업 목표가 아닌 기준점의 등록 좌표입니다.</p>';$('#geometry-detail').innerHTML=detail;
 $('#perception').innerHTML=state.runs.map((x,i)=>`<div><dt>${i===0?'기준':'개선'} · 인식 / 보정 / 계획</dt><dd>${fmt(x.perception_ms,2)} / ${fmt(x.calibration_ms||0,2)} / ${fmt(x.planning_ms,2)} ms</dd></div>`).join('');
 ['left','right'].forEach((side,i)=>{const a=$('#download-'+side);a.hidden=state.local;a.href=`${state.suite==='legacy'?'data':'data-v2'}/${state.runs[i].id}.json`;});$('#download-media').href=state.roots[1]+'/recording.json';$('#download-media').hidden=state.local||!state.media[1];
 const events=state.media.flatMap(m=>m?.contacts||[]);$('#collision-jump').hidden=!events.length;$('#collision-jump').onclick=()=>{state.playing=false;state.elapsed=Math.min(...events.map(e=>e.t));render();};
}
function renderContacts(){const info=[];state.media.forEach((m,i)=>{for(const e of m?.contacts||[]){const c=e.contacts[0];info.push(`${i===0?'기준':'개선'}: t=${fmt(e.t,2)} s, 링크 ${c.link_index+1} ↔ 장애물 ${c.obstacle_index+1}, 접촉 XY (${fmt(c.point_on_robot[0],3)}, ${fmt(c.point_on_robot[1],3)}) m`);}});$('#contact-detail').textContent=info.length?'▲ 기록된 최초 접촉 · '+info.join(' / '):'접촉 기록 없음. 충돌이 없는 실행에 접촉 위치를 추측해 표시하지 않습니다.';}
function openCase(suite,row){state.suite=suite;state.condition=suite==='legacy'?row.condition:row.profile;state.seed=row.seed;if(suite==='calibration')state.bias=row.bias_mm;configure();setTab('experiment');loadScene();window.scrollTo({top:0,behavior:'smooth'});}
function failureButtons(container,rows,suite){const reasons=[...new Set(rows.filter(r=>!r.success).map(r=>r.reason))];$(container).innerHTML=reasons.map(reason=>{const rs=rows.filter(r=>r.reason===reason);const first=rs[0];return `<button class="failure-card" data-run="${first.id}"><b>${REASONS[reason][0]}</b><span>${rs.length}회 · ${suite==='legacy'?'기존 개선 방법':'보정 후 방법'}</span><em>seed ${first.seed} 사례 열기 →</em></button>`;}).join('');$(container).querySelectorAll('button').forEach(b=>b.onclick=()=>openCase(suite,rows.find(r=>r.id===b.dataset.run)));}
function results(){
 $('#metrics-table').innerHTML=['baseline','perception','planning','improved'].map(k=>{const r=legacy.metrics[k].all;return `<tr><td>${NAMES[k]}</td><td>${r.successes} / ${r.n}</td><td>${pct(r.success_rate)}</td><td>${r.detected_n}</td><td>${fmt(r.perception_error_mean_mm)} mm</td></tr>`;}).join('');
 failureButtons('#legacy-failures',legacy.episodes.filter(r=>r.method==='improved'),'legacy');
 $('#study-scope').textContent=`개발 seed 2000–2002와 분리한 최종 seed ${study.config.seeds[0]}–${study.config.seeds.at(-1)}. 정상 기준점 100개 장면 + 스트레스 40개 장면, 총 ${study.episodes.length}회.`;
 $('#study-table').innerHTML=study.config.offsets_mm.map(bias=>{const m=study.metrics.standard[String(bias)],a=m.uncorrected,b=m.reference;return `<tr><td>+${bias} mm</td><td>${a.successes}/${a.n}</td><td>${b.successes}/${b.n}</td><td>${a.collisions} → ${b.collisions}</td><td>${fmt(a.perception_error_mean_mm)} → ${fmt(b.perception_error_mean_mm)} mm</td><td>${fmt(a.pipeline_median_ms)} → ${fmt(b.pipeline_median_ms)} ms</td></tr>`;}).join('');
 $('#stress-results').innerHTML=['markers_missing','board_shift'].map(p=>{const m=study.metrics[p].all,a=m.uncorrected,b=m.reference;return `<article><h4>${PROFILES[p][0]}</h4><p>성공 <strong>${a.successes}/${a.n} → ${b.successes}/${b.n}</strong> · 충돌 <strong>${a.collisions} → ${b.collisions}</strong></p><p>${PROFILES[p][1]}</p><button class="text-button" data-profile="${p}">이 조건 직접 보기 →</button></article>`;}).join('');$('#stress-results').querySelectorAll('button').forEach(b=>b.onclick=()=>openCase('calibration',study.episodes.find(r=>r.profile===b.dataset.profile)));
 failureButtons('#study-failures',study.episodes.filter(r=>r.method==='reference'),'calibration');
 $('#protocol').innerHTML=`<p>기존: 400회. 새 실험: 20 seed × (정상 기준점의 편향 0/20/40/65/100 mm + 기준점 결손 65 mm + 기준점 배치 오류 65 mm) × 2방법 = ${study.episodes.length}회. 성공: 최종 XY 거리 ≤35 mm, 이동 경로 존재, 실행 중 충돌 없음. 이동 보류도 과제 실패로 포함합니다.</p>`;
}
function togglePlay(){if(!state.runs.length||maxTime()===0)return;if(state.elapsed>=maxTime())state.elapsed=0;state.playing=!state.playing;render();}
$('#compare').onclick=togglePlay;$('#reset').onclick=()=>{state.playing=false;state.elapsed=0;render();};$('#time').oninput=e=>{state.playing=false;state.elapsed=Number(e.target.value)/1000*maxTime();render();};$('#show-overlay').onchange=e=>$('#overlay').style.display=e.target.checked?'':'none';
$('#condition').onchange=e=>{state.condition=e.target.value;if(state.suite==='calibration'&&state.condition!=='standard')state.bias=65;configure();loadScene();};$('#seed').onchange=e=>{state.seed=Number(e.target.value);loadScene();};$('#bias').onchange=e=>{state.bias=Number(e.target.value);loadScene();};
document.querySelectorAll('[data-suite]').forEach(b=>b.onclick=()=>{if(b.dataset.suite===state.suite)return;state.suite=b.dataset.suite;state.condition=state.suite==='legacy'?'nominal':'standard';state.seed=state.suite==='legacy'?legacy.config.seeds[0]:study.config.seeds[0];state.bias=65;configure();loadScene();});$('#to-calibration').onclick=()=>$('#suite-calibration').click();
document.querySelectorAll('[data-tab]').forEach(b=>b.onclick=()=>setTab(b.dataset.tab));window.addEventListener('hashchange',()=>{if(['experiment','results','method'].includes(location.hash.slice(1)))setTab(location.hash.slice(1));});
function animate(t){const dt=previous?Math.min((t-previous)/1000,.1):0;previous=t;if(state.playing){state.elapsed=Math.min(state.elapsed+dt,maxTime());if(state.elapsed>=maxTime())state.playing=false;render();}requestAnimationFrame(animate);}requestAnimationFrame(animate);
$('#run-local').onclick=async()=>{const b=$('#run-local');b.disabled=true;state.playing=false;const req=++state.requestId;$('#local-status').textContent='Python에서 새 장면과 프레임을 계산 중…';try{const res=await fetch('/api/run',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({seed:state.seed,condition:state.suite==='legacy'?state.condition:'nominal',target:[Number($('#target-x').value),Number($('#target-y').value)]})});const data=await res.json();if(!res.ok)throw Error(data.error);if(req!==state.requestId)return;state.local=true;state.runs=data.episodes;state.roots=data.episodes.map(r=>r.media_root||'');state.media=await Promise.all(state.roots.map(root=>root?json(root+'/recording.json?v='+req):null));await Promise.all(state.media.flatMap((m,i)=>m.pages.map(p=>new Promise((resolve,reject)=>{const image=new Image();image.onload=resolve;image.onerror=()=>reject(Error('로컬 프레임 로드 실패'));image.src=state.roots[i]+'/'+p.file+'?v='+req;}))));if(req!==state.requestId)return;state.elapsed=0;$('#scenario-title').textContent='새 로컬 실행';$('#condition-note').textContent=CONDITIONS[data.episodes[0].condition][0]+' · 목표 좌표를 직접 바꾼 실행. 상단 성공률은 저장된 실험 집계입니다.';$('.record-label').textContent='● 방금 계산한 로컬 Python 실행';$('#run-id').textContent='LOCAL / '+state.seed;renderStatic();render();$('#compare').disabled=maxTime()===0;$('#local-status').textContent='새 계산 완료. 기존·보정 실험 집계에 추가되지 않습니다.';}catch(e){$('#local-status').textContent=e.message;}finally{b.disabled=false;}};
async function init(){try{[legacy,study]=await Promise.all([json('data/summary.json'),json('data-v2/summary.json')]);configure();results();await loadScene();if(['results','method'].includes(location.hash.slice(1)))setTab(location.hash.slice(1));}catch(e){$('#error').textContent=e.message;$('#error').hidden=false;$('#compare').disabled=true;}try{const r=await fetch('/api/health');const d=await r.json();if(d.mode==='fresh-local'){$('#local-form').hidden=false;$('#local-status').textContent='로컬 Python 엔진 연결됨';}else throw Error();}catch{$('#local-status').textContent='공개 웹: 저장된 실행 탐색 전용 · 새 계산은 로컬에서 지원';}}
init();
export {frameAt,fmt,pct};

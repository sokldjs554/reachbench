import {Workbench} from './studio-engine.mjs';
const $=s=>document.querySelector(s),$$=s=>[...document.querySelectorAll(s)];
const conditions={normal:['기본 집기','시야가 확보된 작업대에서 물체를 집어 트레이에 놓습니다.'],occluded:['목표 가림','정면에서 목표가 보이지 않으면 후면 카메라로 다시 확인합니다.'],shifted:['관찰 후 위치 변화','첫 관측 뒤 2 N의 외력을 60 ms 가합니다. 개선 방법은 내려가기 전에 다시 관찰합니다.'],unreachable:['작업 범위 밖','카메라에서 찾았더라도 작업 범위 밖이면 이동을 보류합니다.']};
const phases={ready:['시작을 기다립니다','조건과 방법을 고르고 실행하세요.'],starting:['카메라 관측 준비','RGB-D 입력으로 목표를 찾습니다.'],observe:['목표 관찰','센서 영상에서 위치를 추정합니다.'],change_view:['다른 카메라로 재관측','정면 검출 실패 → 후면 카메라'],approach:['목표 위로 접근','관절 모터가 IK 목표를 추종합니다.'],replan:['새 위치로 접근 수정','추가 관측을 제어 목표에 반영합니다.'],disturbance:['물체에 외력 발생','2 N · 60 ms, 물리적으로 물체를 밀었습니다.'],descend:['그리퍼 내려가기','추정한 물체 중심으로 접근합니다.'],close:['그리퍼 닫기','부착 제약 없이 손가락 접촉으로 집습니다.'],lift:['물체 들어올리기','닫힌 그리퍼를 유지하며 상승합니다.'],verify_grasp:['집기 확인','손가락 간격으로 빈 집기 여부를 확인합니다.'],retry:['집기 실패 → 재시도','손을 열고 다시 관찰합니다.'],transport:['트레이로 운반','그립을 유지하며 이동합니다.'],place:['물체 내려놓기','트레이 위로 내려갑니다.'],release:['그리퍼 열기','물체를 놓습니다.'],retreat:['그리퍼 후퇴','물체가 트레이 안에 남았는지 평가합니다.'],settle:['물체 안정화 대기','물리 시뮬레이션 진행 중'],success:['작업 완료','트레이 안에 물체를 놓았습니다.'],failure:['작업 중단','실패 이유를 오른쪽에서 확인하세요.']};
const reasons={placed:'트레이 배치 성공',target_missing:'목표를 찾지 못함',outside_workspace:'작업 범위 밖',empty_grasp:'빈 그리퍼 · 집기 실패',obstacle_contact:'가림판과 접촉',placement_failed:'트레이 배치 실패',timeout:'실행 시간 초과'};
const state={seed:100,condition:'occluded',method:'feedback',replay:false,request:0};let engine,summary;
function selections(){
 $$('[data-condition]').forEach(b=>{const yes=b.dataset.condition===state.condition;b.classList.toggle('selected',yes);b.setAttribute('aria-pressed',String(yes));});
 $$('[data-method]').forEach(b=>{const yes=b.dataset.method===state.method;b.classList.toggle('selected',yes);b.setAttribute('aria-pressed',String(yes));});
 $('#seed-label').textContent='SEED '+state.seed;$('#scenario-help').textContent=conditions[state.condition][1];
}
function clear(){
 $('#sensor-history').replaceChildren();$('#sensor-empty').hidden=false;$('#events').replaceChildren();$('#compare-other').hidden=true;$('#result').className='run-result';$('#result').innerHTML='<span>THIS RUN</span><b>아직 실행하지 않았습니다</b><p>물체를 집어 트레이에 놓아야 성공입니다.</p>';
}
function reset(){
 state.request++;state.replay=false;clear();engine?.reset(state.seed,state.condition);$('#replay-controls').hidden=true;$('#mode-badge').innerHTML='<i></i> LIVE PHYSICS';$('#engine-label').textContent='MuJoCo 4.0.1 · 브라우저 실행';$('#run').innerHTML='<span>▶</span> 실험 실행';$('#pause').textContent='일시정지';$('#pause').disabled=true;$('#run').disabled=!engine?.ready;selections();
}
function event(e){
 if(e.replay&&e.terminal){$('#pause').disabled=true;$('#pause').textContent='일시정지';}
 const [title,note]=phases[e.phase]||[e.phase,''];$('#phase').textContent=title;$('#phase-note').textContent=e.phase==='observe'?(e.detected?'목표 검출 → 위치 추정':'목표 검출 실패'):note;
 if(e.phase!=='ready'&&!e.replay){const li=document.createElement('li');li.innerHTML=`<time>${e.t.toFixed(2)} s</time><span>${title}${e.phase==='observe'?` · ${e.camera==='front'?'정면':'후면'} / ${e.detected?'검출':'미검출'}`:''}</span>`;$('#events').append(li);}
 if(e.result)showResult(e.result);
}
function showResult(r,recorded=false){
 const box=$('#result');box.className='run-result '+(r.success?'success':'failure');box.innerHTML=`<span>${recorded?'PYTHON RECORDED RUN':'LIVE RESULT · 이번 실행'}</span><b>${r.success?'✓':'×'} ${reasons[r.reason]||r.reason}</b><p>놓기 오차 <strong>${r.placement_error_mm.toFixed(1)} mm</strong> · ${r.duration_s.toFixed(2)} s</p><p>관측 ${r.observations}회 · 재시도 ${r.retries}회</p>`;
 $('#pause').disabled=true;$('#run').innerHTML='<span>▶</span> '+(recorded?'기록 재생':'다시 실행');$('#compare-other').hidden=recorded;$('#compare-other').textContent=`같은 배치에서 ${state.method==='feedback'?'기준':'개선'} 방법 실행 →`;
}
function sensor(o){
 $('#sensor-empty').hidden=true;const card=document.createElement('article');card.className='sensor-card';const canvas=document.createElement('canvas');canvas.width=canvas.height=o.n;const ctx=canvas.getContext('2d');ctx.putImageData(new ImageData(new Uint8ClampedArray(o.rgb),o.n,o.n),0,0);
 if(o.estimate){const [x,y,x1,y1]=o.estimate.bbox;ctx.strokeStyle='#5ce9d7';ctx.lineWidth=2;ctx.strokeRect(x-2,y-2,x1-x+4,y1-y+4);}
 card.append(canvas);const label=document.createElement('b');label.className=o.estimate?'found':'missing';label.textContent=`${o.camera==='front'?'정면':'후면'} · ${o.estimate?'목표 검출':'검출 실패'}`;card.append(label);const text=document.createElement('p');text.textContent=`t=${o.t.toFixed(2)}s · ${o.estimate?o.estimate.pixels:0} px`;card.append(text);$('#sensor-history').append(card);$('#sensor-history').scrollLeft=$('#sensor-history').scrollWidth;
}
function start(){if(!engine?.ready)return;if(state.replay){engine.seek(0);engine.running=true;$('#pause').disabled=false;return;}reset();engine.start(state.method);$('#pause').disabled=false;$('#result').innerHTML='<span>LIVE RESULT</span><b>실행 중</b><p>센서와 모터의 실제 계산 결과를 기다립니다.</p>';}
const runButton = $('#run');
const narrowWorkbench = matchMedia('(max-width:760px)');
function positionRunButton() {
 const toolbar = narrowWorkbench.matches ? $('#mobile-runbar') : $('.play-controls');
 if (narrowWorkbench.matches) toolbar.append(runButton);
 else toolbar.prepend(runButton);
}
positionRunButton();
narrowWorkbench.addEventListener('change',positionRunButton);
runButton.onclick=start;
$('#pause').onclick=()=>{engine.running=!engine.running;$('#pause').textContent=engine.running?'일시정지':'계속 실행';};
$('#reset').onclick=()=>{if(state.replay){engine.running=false;engine.seek(0);$('#pause').disabled=true;$('#pause').textContent='일시정지';}else reset();};
$('#new-scene').onclick=()=>{state.seed=state.seed>=119?100:state.seed+1;reset();};
$('#compare-other').onclick=()=>{state.method=state.method==='feedback'?'one_shot':'feedback';start();};
$$('[data-condition]').forEach(b=>b.onclick=()=>{state.condition=b.dataset.condition;reset();});
$$('[data-method]').forEach(b=>b.onclick=()=>{state.method=b.dataset.method;reset();});
$('#speed').onchange=e=>{if(engine)engine.speed=+e.target.value;};$('#return-live').onclick=reset;
$('#scrub').oninput=e=>{engine.running=false;engine.seek(+e.target.value/1000*engine.replay.duration_s);$('#pause').disabled=engine.elapsed>=engine.replay.duration_s;$('#pause').textContent='계속 실행';};
async function json(url){const r=await fetch(url);if(!r.ok)throw Error('자료를 불러오지 못했습니다: '+url);return r.json();}
async function replay(id){
 const request=++state.request;if(engine)engine.running=false;try{
 const r=await json(`bench/runs/${id}/run.json`);if(request!==state.request)return;
 clear();state.seed=r.seed;state.condition=r.condition;state.method=r.method;state.replay=true;selections();if(engine?.ready)engine.loadReplay(r);$('#mode-badge').textContent='PYTHON / RECORDED';$('#engine-label').textContent='실제 실행의 관절 기록 재구성 · 라이브 계산 아님';$('#replay-controls').hidden=!engine?.ready||r.duration_s===0;$('#run').disabled=!engine?.ready||r.duration_s===0;$('#run').innerHTML='<span>▶</span> 기록 재생';showResult(r,true);if(r.duration_s===0)$('#run').textContent='이동 없음';$('#result').insertAdjacentHTML('beforeend',`<p><a href="bench/runs/${id}/run.json" target="_blank">이 실행의 원본 기록 ↗</a></p>`);
 for(const o of r.sensors){const card=document.createElement('article');card.className='sensor-card';const im=new Image();im.src=`bench/runs/${id}/${o.image}`;im.alt=`실제 Python ${o.camera} 카메라 입력`;card.append(im);const b=document.createElement('b');b.textContent=`${o.camera==='front'?'정면':'후면'} · ${o.estimate?'목표 검출':'검출 실패'}`;b.className=o.estimate?'found':'missing';card.append(b);const p=document.createElement('p');p.textContent=`t=${o.t.toFixed(2)}s${o.error_mm==null?'':` · 추정 오차 ${o.error_mm.toFixed(1)}mm`}`;card.append(p);if(o.estimate){const q=document.createElement('p');q.textContent=`추정 XY ${(o.estimate.position[0]*1000).toFixed(0)}, ${(o.estimate.position[1]*1000).toFixed(0)} mm / 평가 정답 ${(o.truth[0]*1000).toFixed(0)}, ${(o.truth[1]*1000).toFixed(0)} mm`;card.append(q);}$('#sensor-history').append(card);}
 $('#sensor-empty').hidden=true;for(const e of r.events)event(e);if(engine?.ready)engine.seek(0);else{$('#phase').textContent='기록의 최종 결과';$('#phase-note').textContent='3D 없이 센서 영상·판단 기록을 확인할 수 있습니다.';}$('#viewport').scrollIntoView({behavior:'smooth',block:'start'});
 }catch(e){$('#result').textContent=e.message;}
}
function rateCell(r,base=false){return `<strong>${(100*r.success_rate).toFixed(0)}%</strong><small>${r.successes}/${r.n}</small><div class="bar ${base?'base':''}"><i style="width:${100*r.success_rate}%"></i></div>`;}
async function benchmark(){
 try{summary=await json('bench/summary.json');const find=(c,m)=>summary.find(r=>r.condition===c&&r.method===m);
 $('#rate-base').textContent=(find('all','one_shot').success_rate*100).toFixed(0)+'%';$('#rate-feedback').textContent=(find('all','feedback').success_rate*100).toFixed(0)+'%';
 $('#benchmark-rows').innerHTML=Object.entries(conditions).map(([c,[name]])=>{const a=find(c,'one_shot'),b=find(c,'feedback');const failures=[...new Set([...Object.keys(a.failures),...Object.keys(b.failures)])].map(x=>reasons[x]||x).join(' · ')||'해당 평가에서 실패 없음';return `<tr><td>${name}</td><td>${rateCell(a,true)}</td><td>${rateCell(b)}</td><td style="white-space:normal;font-size:12px;max-width:220px">${failures}</td><td><button class="replay-link" data-record="${c}-100-one_shot">기준 ↗</button><button class="replay-link" data-record="${c}-100-feedback">개선 ↗</button>${c==='shifted'?'<button class="replay-link" data-record="shifted-107-feedback">재시도 사례 ↗</button> <a href="retry/">재시도 켬·끔 비교</a>':''}</td></tr>`;}).join('');
 $$('[data-record]').forEach(b=>b.onclick=()=>{replay(b.dataset.record);});
 $('#metric-details').innerHTML='<table><thead><tr><th>조건 / 방법</th><th>평균 인식 XY 오차</th><th>평균 최종 놓기 오차</th><th>가림판 접촉</th><th>평균 처리 시간</th><th>관측 / 재시도</th></tr></thead><tbody>'+summary.filter(r=>r.condition!=='all').map(r=>`<tr><td>${conditions[r.condition][0]} / ${r.method==='one_shot'?'기준':'개선'}</td><td>${r.perception_error_mm==null?'—':r.perception_error_mm.toFixed(1)+' mm'}</td><td>${r.placement_error_mm.toFixed(1)} mm</td><td>${r.collisions}/${r.n}</td><td>${(r.wall_ms/1000).toFixed(2)} s</td><td>${r.observations.toFixed(1)}회 / 총 ${r.retries}회</td></tr>`).join('')+'</tbody></table>';
 }catch(e){$('#benchmark-rows').innerHTML=`<tr><td colspan="5">${e.message}</td></tr>`;}
}
selections();benchmark();
try{
 engine=new Workbench($('#viewport'),event,sensor);window.reachbench={engine,state};
 await engine.load(text=>$('#loading-text').textContent=text);$('#loading').hidden=true;$('#run').disabled=false;$('#reset').disabled=false;$('#new-scene').disabled=false;
}catch(e){console.error(e);$('#loading').hidden=true;$('#error').hidden=false;$('#error').textContent='실시간 3D 실행을 시작할 수 없습니다. '+e.message+' 아래 평가 기록과 GitHub의 로컬 실행 방법을 확인해 주세요.';}
setInterval(()=>{if(!engine?.ready)return;$('#clock').textContent=engine.elapsed.toFixed(2)+' s';if(engine.replay)$('#scrub').value=Math.round((engine.replay.duration_s ? engine.elapsed/engine.replay.duration_s*1000 : 0));},100);

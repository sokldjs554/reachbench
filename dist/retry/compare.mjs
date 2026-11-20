const $ = (s) => document.querySelector(s);
const modes = ["off", "on"];
const phases = {
  observe:"카메라 관측", disturbance:"물체에 외력 적용", approach:"목표로 접근",
  descend:"그리퍼 하강", close:"그리퍼 닫기", lift:"물체 들어 올리기",
  verify_grasp:"집기 판정", retry:"손을 열고 재시도", transport:"트레이로 운반",
  place:"물체 내려놓기", release:"그리퍼 열기", retreat:"후퇴", success:"배치 성공", failure:"빈 집기 · 종료"
};
const sTime = (n) => n.toFixed(2) + " s";
const lastAt = (items, t, time) => items.findLastIndex(item => time(item) <= t + 1e-7);
function element(tag, text, parent) {
  const el = document.createElement(tag);
  if (text != null) el.textContent = text;
  if (parent) parent.append(el);
  return el;
}
async function loadJSON(path) {
  const response = await fetch(path);
  if (!response.ok) throw new Error(path);
  return response.json();
}

function makePanel(mode, frames, run) {
  const panel = element("article", null, $("#panels"));
  panel.className = "panel " + mode;
  const head = element("div", null, panel);
  head.className = "panel-title";
  element("h3", mode === "off" ? "재시도 끔" : "재시도 켬", head);
  const time = element("time", null, head);
  const picture = element("div", null, panel);
  picture.className = "picture";
  const canvas = element("canvas", null, picture);
  canvas.width = frames.width;
  canvas.height = frames.height;
  canvas.setAttribute("aria-label", (mode === "off" ? "재시도 끔" : "재시도 켬") + " 관절 기록 재구성");
  const stamp = element("span", null, picture);
  const terminal = element("b", run.duration_s.toFixed(2) + "초 종료 · 마지막 자세", picture);
  terminal.className = "terminal";
  terminal.hidden = true;
  const box = element("div", null, panel);
  box.className = "readout";
  const status = element("b", null, box);
  const detail = element("small", null, box);
  const stream = frames[mode];
  let lastIndex = -1, lastStatus = "", activeSheet = null;
  function paint(i) {
    if (i !== lastIndex) return;
    const ctx = canvas.getContext("2d");
    const cell = i % (frames.columns * frames.rows);
    ctx.drawImage(activeSheet.image, (cell % frames.columns)*frames.width,
      Math.floor(cell / frames.columns)*frames.height, frames.width, frames.height,
      0, 0, frames.width, frames.height);
    stamp.textContent = "자세 기록 " + sTime(stream.times[i]);
  }
  function showFrame(i) {
    if (i === lastIndex) return;
    lastIndex = i;
    const index = Math.floor(i / (frames.columns * frames.rows));
    if (activeSheet?.index === index && activeSheet.image.naturalWidth) return paint(i);
    if (activeSheet?.index === index) return;
    const image = new Image();
    activeSheet = {index, image};
    canvas.getContext("2d").clearRect(0,0,canvas.width,canvas.height);
    stamp.textContent = "자세 불러오는 중";
    image.onload = () => { if (activeSheet.image === image) paint(lastIndex); };
    image.onerror = () => { if (activeSheet.image === image) stamp.textContent = "기록 이미지 로드 실패"; };
    image.src = stream.sheets[index];
  }
  return (t) => {
    const stop = stream.times.at(-1);
    const shown = Math.min(t, stop);
    const i = lastAt(stream.times, shown, n => n);
    showFrame(i);
    terminal.hidden = t + 1e-7 < stop;
    time.textContent = sTime(shown);
    const e = run.events[lastAt(run.events, shown, e => e.t)];
    if (lastStatus === e) return;
    lastStatus = e;
    status.textContent = phases[e.phase] || e.phase;
    const grasp = run.events.findLast(x => x.phase === "verify_grasp" && x.t <= shown);
    const info = [];
    if (grasp) {
      const command = grasp.prior_grip_command;
      const name = command === 0 ? "닫기" : command === 255 ? "열기" : "그리퍼";
      info.push(sTime(grasp.command_t) + " " + name + " 명령 " + command);
      info.push(sTime(grasp.t) + " 집기 판정 " + (grasp.gripper_width_m*1000).toFixed(3) + " mm");
    }
    if (e.phase === "success" || e.phase === "failure") info.push("물체–트레이 " + run.placement_error_mm.toFixed(2) + " mm");
    if (!info.length) info.push("단계 시작 " + sTime(e.t));
    detail.textContent = info.join(" · ");
  };
}

async function main() {
  const [study,frames] = await Promise.all([loadJSON("study.json"),loadJSON("frames.json")]);
  const runs = study.runs;
  const duration = Math.max(...modes.map(m => frames[m].times.at(-1)));
  const checks = runs.on.events.filter(e => e.phase === "verify_grasp");
  let time = checks[0].t, playing = false, frameID = 0, origin = 0;
  let selected = "", lastObservation = null;
  const updatePanels = modes.map(m => makePanel(m, frames, runs[m]));
  const slider = $("#timeline"), play = $("#play");
  slider.max = duration;
  const eventControls = [];
  const evals = study.evaluation;
  $("#evaluation").textContent = "별도 평가 seed 200–219  ·  재시도 끔 " + evals.off_successes + "/" + evals.n_pairs +
    " 성공  ·  켬 " + evals.on_successes + "/" + evals.n_pairs + " 성공  ·  실제 재시도 " + evals.on_retry_runs + "건";
  function inspect(o) {
    if (lastObservation === o) return;
    lastObservation = o;
    [...$("#photos").children].forEach(b => b.setAttribute("aria-pressed",String(Number(b.dataset.t) === o.t)));
    const method = selected === "on" ? "재시도 켬" : "재시도 끔";
    const camera = o.camera === "front" ? "정면 카메라" : "후면 카메라";
    $("#selected-observation").textContent = method + " · " + camera + " · " + o.t.toFixed(2) + "초";
    const section = $("#alignment");
    section.replaceChildren();
    function metric(label,value,note) {
      const cell = element("div", null, section);
      element("span",label,cell); element("b",value,cell); element("small",note,cell);
    }
    const xy = o.estimate_xy_m?.map(x => (x*1000).toFixed(1)).join(", ");
    metric("카메라 위치 추정",xy ? "("+xy+") mm" : "미검출","작업대 기준 XY");
    metric("관측 직전 또는 같은 시각의 상태","손가락 간격 " + o.gap_mm.toFixed(2) + " mm",
      sTime(o.state_t) + " · 관측과 " + o.state_lag_ms + " ms 차이");
    const grip = o.next_ctrl?.[7];
    metric("관측 후 첫 기록 명령",grip == null ? "후속 명령 없음" : (grip === 255 ? "그리퍼 열기" : grip === 0 ? "그리퍼 닫기" : "그리퍼 명령") + " (" + grip + ")",
      o.next_t == null ? "" : sTime(o.next_t) + " · " + (phases[o.next_phase] || o.next_phase));
    const rows = $("#joints");
    rows.replaceChildren();
    const table = element("table",null,rows);
    const hdr = table.insertRow();
    for (const label of ["각도 (rad)","1축","2축","3축","4축","5축","6축","7축"]) element("th",label,hdr);
    for (const [name,vector] of [["관측 직전 상태",o.arm_rad],["다음 기록 명령",o.next_ctrl]]) {
      const row = table.insertRow(); element("th",name,row);
      for(let i=0;i<7;i++) element("td",vector ? vector[i].toFixed(3) : "—",row);
    }
  }
  function setMode(mode) {
    selected = mode;
    $("#photos").replaceChildren();
    runs[mode].observations.forEach((o,index) => {
      const btn = element("button",null,$("#photos")); btn.dataset.t = o.t;
      const im = element("img",null,btn);
      im.alt = (o.camera === "front" ? "정면" : "후면") + " 관측 " + (index+1);
      im.src = o.image;
      element("span",sTime(o.t),btn);
      btn.onclick = () => seek(o.t);
    });
    paint();
  }
  function paint() {
    for(const p of updatePanels) p(time);
    slider.value = time;
    for (const {t, buttons} of eventControls) {
      const current = Math.abs(time - t) < 0.005;
      for (const button of buttons) button.setAttribute("aria-current", current ? "time" : "false");
    }
    slider.setAttribute("aria-valuetext",sTime(time));
    $("#clock").textContent = sTime(time) + " / " + sTime(duration);
    const obs = runs[selected].observations;
    inspect(obs[lastAt(obs,time,o=>o.t)]);
  }
  function pause() {
    playing = false; cancelAnimationFrame(frameID); play.textContent = time >= duration ? "다시 재생" : "재생";
  }
  function seek(t) { time = Math.min(duration,Math.max(0,t)); pause(); paint(); }
  function tick(now) {
    if(!playing) return;
    time = Math.min(duration,(now-origin)/1000);
    paint();
    if(time >= duration) pause(); else frameID=requestAnimationFrame(tick);
  }
  play.onclick = () => {
    if(playing) return pause();
    if(time >= duration) seek(0);
    origin = performance.now()-time*1000;
    playing=true; play.textContent="일시정지"; frameID=requestAnimationFrame(tick);
  };
  $("#reset").onclick=()=>seek(0);
  slider.oninput=()=>seek(Number(slider.value));
  $("#mode").onchange=e=>setMode(e.target.value);
  document.addEventListener("visibilitychange",()=>{if(document.hidden) pause();});
  for(const [label,t] of [["첫 집기 실패",checks[0].t],["두 번째 집기",checks[1].t],["배치 결과",duration]]) {
    const btn=element("button",t.toFixed(2)+"초 · "+label,$("#jumps"));
    btn.onclick=()=>seek(t);
    const marker = element("button", null, $("#markers"));
    marker.style.left = (100 * t / duration) + "%";
    marker.title = t.toFixed(2) + "초 · " + label;
    marker.setAttribute("aria-label", "시간축에서 " + label + " 보기");
    marker.onclick = () => seek(t);
    eventControls.push({t, buttons:[btn, marker]});
  }
  setMode("on");
  const moments = new Map([["empty", checks[0].t], ["grasp", checks[1].t], ["placed", duration]]);
  seek(moments.get(new URLSearchParams(location.search).get("event")) ?? checks[0].t);
  $("#loading").hidden=true;$("#workbench").hidden=false;$("#inspector").hidden=false;
}
main().catch(() => { $("#loading").textContent="기록을 불러오지 못했습니다. 페이지를 새로고침하거나 상단의 실험 원본을 확인해 주세요."; });

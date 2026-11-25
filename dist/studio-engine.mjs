import * as THREE from 'three';
import {OrbitControls} from './vendor/OrbitControls.js';
import loadMujoco from './vendor/mujoco.js';
import {HOME,TRAY,sceneFromSeed,solve,estimateRGBD,judgePlacement} from './studio-core.mjs';

export class Workbench {
 constructor(container,onEvent,onSensor){
  this.container=container;this.onEvent=onEvent;this.onSensor=onSensor;this.running=false;this.ready=false;this.speed=1;
  this.scene=new THREE.Scene();this.scene.background=new THREE.Color('#1b2630');
  this.renderer=new THREE.WebGLRenderer({antialias:true,preserveDrawingBuffer:true});this.renderer.setPixelRatio(Math.min(devicePixelRatio,1.7));
  this.renderer.shadowMap.enabled=true;this.renderer.shadowMap.type=THREE.PCFSoftShadowMap;
  this.renderer.outputColorSpace=THREE.SRGBColorSpace;container.append(this.renderer.domElement);
  this.camera=new THREE.PerspectiveCamera(40,1,.01,10);this.camera.up.set(0,0,1);this.camera.position.set(1.55,1.45,1.55);this.camera.layers.enable(1);
  this.controls=new OrbitControls(this.camera,this.renderer.domElement);this.controls.target.set(.30,.04,.61);this.controls.maxDistance=4;this.controls.minDistance=.75;this.controls.maxPolarAngle=Math.PI*.49;this.controls.update();
  this.scene.add(new THREE.HemisphereLight(0xd6e7ff,0x5e6669,2.2));
  const light=new THREE.DirectionalLight(0xfff5df,3.0);light.position.set(.5,-1,3);light.castShadow=true;light.shadow.mapSize.set(1024,1024);light.shadow.camera.left=-1.4;light.shadow.camera.right=1.4;light.shadow.camera.top=1.4;light.shadow.camera.bottom=-1.4;light.shadow.normalBias=.003;this.scene.add(light);
  this.marker=new THREE.Mesh(new THREE.RingGeometry(.028,.032,40),new THREE.MeshBasicMaterial({color:0x54d8eb,side:THREE.DoubleSide}));this.marker.layers.set(1);this.marker.visible=false;this.scene.add(this.marker);
  this.sensorCamera=new THREE.PerspectiveCamera(45,1,.01,4);this.sensorCamera.up.set(0,0,1);
  this.target=new THREE.WebGLRenderTarget(224,224,{minFilter:THREE.NearestFilter,magFilter:THREE.NearestFilter});
  this.depthMaterial=new THREE.MeshDepthMaterial({depthPacking:THREE.RGBADepthPacking,blending:THREE.NoBlending});
  this.resize=new ResizeObserver(()=>this.fit());this.resize.observe(container);this.fit();
  this.last=performance.now();this.animate=this.animate.bind(this);
 }
 fit(){const {width,height}=this.container.getBoundingClientRect();this.renderer.setSize(width,height);this.camera.aspect=width/Math.max(1,height);this.camera.updateProjectionMatrix();}
 async load(progress){
  progress('물리 엔진 준비 중');this.mj=await loadMujoco({locateFile:p=>new URL('./vendor/'+p,import.meta.url).href});
  progress('Panda 모델 불러오는 중 · 최초 약 15 MB');const r=await fetch('./assets/workcell.mjb.gz');if(!r.ok)throw Error('로봇 모델을 불러올 수 없습니다');
  if(!globalThis.DecompressionStream)throw Error('이 브라우저는 모델 압축 해제를 지원하지 않습니다. 최신 Chrome 또는 Safari로 열어 주세요.');
  const bytes=new Uint8Array(await new Response(r.body.pipeThrough(new DecompressionStream('gzip'))).arrayBuffer());
  this.mj.FS.writeFile('/workcell.mjb',bytes);this.vfs=new this.mj.MjVFS();this.model=this.mj.MjModel.from_binary_path('/workcell.mjb',this.vfs);this.data=new this.mj.MjData(this.model);this.ikdata=new this.mj.MjData(this.model);
  this.jp=new this.mj.DoubleBuffer(3*this.model.nv);this.jr=new this.mj.DoubleBuffer(3*this.model.nv);
  this.tcp=this.id('SITE','tcp');this.cube=this.id('BODY','cube');this.cubeAdr=this.model.jnt_qposadr[this.id('JOINT','cube_joint')];this.occluder=this.id('BODY','occluder');this.occluderGeom=this.id('GEOM','occluder_geom');
  progress('장면 구성 중');this.buildGeometry();this.ready=true;this.reset(100,'occluded');requestAnimationFrame(this.animate);return this;
 }
 id(type,name){return this.mj.mj_name2id(this.model,this.mj.mjtObj['mjOBJ_'+type].value,name);}
 buildGeometry(){
  const m=this.model;this.meshes=[];const cache=new Map();
  for(let g=0;g<m.ngeom;g++){
   if(m.geom_group[g]===3)continue;let geometry;const type=m.geom_type[g],sz=Array.from(m.geom_size.slice(3*g,3*g+3));
   if(type===7){const id=m.geom_dataid[g];if(cache.has(id))geometry=cache.get(id);else{
    geometry=new THREE.BufferGeometry();const adr=m.mesh_vertadr[id],n=m.mesh_vertnum[id],fa=m.mesh_faceadr[id],fn=m.mesh_facenum[id];
    geometry.setAttribute('position',new THREE.BufferAttribute(new Float32Array(m.mesh_vert.slice(3*adr,3*(adr+n))),3));geometry.setIndex(new THREE.BufferAttribute(new Uint32Array(m.mesh_face.slice(3*fa,3*(fa+fn))),1));geometry.computeVertexNormals();cache.set(id,geometry);
   }}else if(type===6)geometry=new THREE.BoxGeometry(...sz.map(x=>2*x));
   else if(type===0)geometry=new THREE.PlaneGeometry(6,6);
   else if(type===2)geometry=new THREE.SphereGeometry(sz[0],16,12);
   else if(type===5){geometry=new THREE.CylinderGeometry(sz[0],sz[0],sz[1]*2,24);geometry.rotateX(Math.PI/2);}else continue;
   const mat=m.geom_matid[g],rgba=mat>=0?m.mat_rgba.slice(4*mat,4*mat+4):m.geom_rgba.slice(4*g,4*g+4);
   const color=type===0?new THREE.Color('#263440'):new THREE.Color().setRGB(rgba[0],rgba[1],rgba[2],THREE.SRGBColorSpace);
   const mesh=new THREE.Mesh(geometry,new THREE.MeshStandardMaterial({color,roughness:.47,metalness:type===7?.14:0,side:THREE.DoubleSide}));mesh.castShadow=type!==0;mesh.receiveShadow=true;mesh.userData.geom=g;this.scene.add(mesh);this.meshes.push(mesh);
  }
 }
 sync(){if(!this.ready)return;const mat=new THREE.Matrix4();for(const mesh of this.meshes){const g=mesh.userData.geom,x=this.data.geom_xpos,R=this.data.geom_xmat,o=9*g;mesh.position.set(x[3*g],x[3*g+1],x[3*g+2]);mat.set(R[o],R[o+1],R[o+2],0,R[o+3],R[o+4],R[o+5],0,R[o+6],R[o+7],R[o+8],0,0,0,0,1);mesh.quaternion.setFromRotationMatrix(mat);}}
 reset(seed=100,condition='occluded',override=null){
  if(!this.ready)return;this.running=false;this.replay=null;this.result=null;this.phase='ready';this.seed=seed;this.condition=condition;this.queue=[];this.op=null;this.events=[];this.observations=0;this.retries=0;this.collision=false;this.elapsed=0;this.marker.visible=false;
  const m=this.model,d=this.data;this.mj.mj_resetData(m,d);d.qpos.set(HOME,0);d.qpos[7]=d.qpos[8]=.04;d.ctrl.set(HOME,0);d.ctrl[7]=255;
  const pos=override||sceneFromSeed(seed,condition);this.initial=[...pos];d.qpos.set(pos,this.cubeAdr);d.qpos.set([1,0,0,0],this.cubeAdr+3);
  m.body_pos.set(condition==='occluded'?[.48,-.20,.47]:[.48,-.20,-.5],3*this.occluder);
  this.mj.mj_forward(m,d);for(let i=0;i<250;i++)this.mj.mj_step(m,d);this.startTime=d.time;this.sync();this.onEvent({phase:'ready',t:0});
 }
 emit(phase,extra={}){this.phase=phase;const e={phase,t:this.elapsed,...extra};this.events.push(e);this.onEvent(e);}
 sense(camera){
  this.sync();const id=this.id('CAMERA',camera),pos=this.data.cam_xpos.slice(3*id,3*id+3),rot=this.data.cam_xmat.slice(9*id,9*id+9),c=this.sensorCamera;
  c.position.fromArray(pos);const M=new THREE.Matrix4().set(rot[0],rot[1],rot[2],0,rot[3],rot[4],rot[5],0,rot[6],rot[7],rot[8],0,0,0,0,1);c.quaternion.setFromRotationMatrix(M);c.updateMatrixWorld();
  const n=224,color=new Uint8Array(n*n*4),packed=new Uint8Array(n*n*4),rgb=new Uint8Array(n*n*4),depth=new Float32Array(n*n),bg=this.scene.background;
  this.scene.background=new THREE.Color(0x000000);this.renderer.setRenderTarget(this.target);this.renderer.render(this.scene,c);this.renderer.readRenderTargetPixels(this.target,0,0,n,n,color);
  this.scene.overrideMaterial=this.depthMaterial;this.scene.background=new THREE.Color(0xffffff);this.renderer.render(this.scene,c);this.renderer.readRenderTargetPixels(this.target,0,0,n,n,packed);this.scene.overrideMaterial=null;this.scene.background=bg;this.renderer.setRenderTarget(null);
  for(let y=0;y<n;y++)for(let x=0;x<n;x++){const i=y*n+x,j=(n-1-y)*n+x;rgb.set(color.subarray(4*j,4*j+4),4*i);const p=4*j;const z=packed[p]/256+packed[p+1]/65536+packed[p+2]/16777216+packed[p+3]/4278190080;depth[i]=c.near*c.far/(c.far-z*(c.far-c.near));}
  const t=performance.now(),est=estimateRGBD(rgb,depth,n,45,pos,rot);this.observations++;
  this.onSensor({rgb,depth,n,camera,estimate:est,t:this.elapsed,processing_ms:performance.now()-t});this.emit('observe',{camera,detected:!!est});
  if(est){this.marker.position.set(est.position[0],est.position[1],.407);this.marker.visible=true;}
  return est;
 }
 ik(target){
  const m=this.model,d=this.ikdata,nv=m.nv;d.qpos.set(this.data.qpos);const desired=[1,0,0,0,-1,0,0,0,-1];
  for(let iter=0;iter<150;iter++){
   this.mj.mj_forward(m,d);const off=9*this.tcp,R=d.site_xmat,rot=[0,0,0];
   for(let k=0;k<3;k++){const a=[R[off+k],R[off+3+k],R[off+6+k]],b=[desired[k],desired[3+k],desired[6+k]];rot[0]+=.5*(a[1]*b[2]-a[2]*b[1]);rot[1]+=.5*(a[2]*b[0]-a[0]*b[2]);rot[2]+=.5*(a[0]*b[1]-a[1]*b[0]);}
   const err=[...target.map((v,i)=>v-d.site_xpos[3*this.tcp+i]),...rot.map(v=>v*.6)];if(Math.hypot(...err)<.0005)break;
   this.mj.mj_jacSite(m,d,this.jp,this.jr,this.tcp);const p=this.jp.GetView(),r=this.jr.GetView();
   const J=Array.from({length:6},(_,i)=>Array.from({length:7},(_,j)=>i<3?p[i*nv+j]:.6*r[(i-3)*nv+j]));
   const A=J.map((a,i)=>J.map((b,j)=>a.reduce((s,x,k)=>s+x*b[k],0)+(i===j?.003:0))),v=solve(A,err);
   for(let j=0;j<7;j++){const dq=J.reduce((s,row,i)=>s+row[j]*v[i],0);d.qpos[j]=Math.max(m.jnt_range[2*j]+.02,Math.min(m.jnt_range[2*j+1]-.02,d.qpos[j]+Math.max(-.08,Math.min(.08,dq))));}
  }return Array.from(d.qpos.slice(0,7));
 }
 move(position,grip=255,duration=1,phase='approach'){return {type:'move',position,grip,duration:duration+.15,motion:duration,phase};}
 hold(duration,phase,grip=null){return {type:'hold',duration,phase,grip};}
 start(method='feedback'){
  this.method=method;this.queue=[{type:'initial'}];this.op=null;this.running=true;this.wallStart=performance.now();this.emit('starting');
 }
 graspPlan(pos,refresh){return [this.move([pos[0],pos[1],.67],255,1.4,'approach'),...(refresh?[{type:'refresh',pos}]:[{type:'grasp',pos}])];}
 next(){
  const op=this.queue.shift();if(!op){this.finish('finished');return;}this.op=op;op.elapsed=0;
  if(op.type==='initial'){
   let est=this.sense('front');if(!est&&this.method==='feedback'){this.emit('change_view');est=this.sense('back');}
   if(!est){this.finish('target_missing');return;}const p=est.position;
   if(p[0]>.70||Math.abs(p[1])>.38){this.finish('outside_workspace');return;}
   this.queue.unshift(...(this.condition==='shifted'?[{type:'disturbance',duration:.06,phase:'disturbance'},this.hold(.35,'settle')]:[]),...this.graspPlan(p,this.method==='feedback'));this.op=null;
  }else if(op.type==='refresh'){
   const est=this.sense('back'),p=est?.position||op.pos;this.queue.unshift(this.move([p[0],p[1],.62],255,.6,'replan'),{type:'grasp',pos:p});this.op=null;
  }else if(op.type==='grasp'){
   const p=op.pos;this.queue.unshift(this.move(p,255,1.2,'descend'),this.hold(.9,'close',0),this.move([p[0],p[1],.62],0,1.2,'lift'),{type:'verify'});this.op=null;
  }else if(op.type==='verify'){
   const width=this.data.qpos[7]+this.data.qpos[8];this.emit('verify_grasp',{width});
   if(width>.018){this.queue.unshift(this.move([.48,.24,.67],0,1.5,'transport'),this.move([.48,.24,.415],0,1.1,'place'),this.hold(.6,'release',255),this.move([.48,.24,.69],255,1,'retreat'),this.hold(.4,'settle'));}
   else if(this.method==='feedback'&&this.retries<1){this.retries++;this.queue.unshift(this.hold(.3,'retry',255),{type:'retry_observe'});}
   else {this.finish('empty_grasp');return;}this.op=null;
  }else if(op.type==='retry_observe'){
   const est=this.sense('back');if(!est){this.finish('target_missing');return;}this.queue.unshift(...this.graspPlan(est.position,true));this.op=null;
  }else {
   this.emit(op.phase);if(op.type==='move'){op.from=Array.from(this.data.ctrl.slice(0,7));op.to=this.ik(op.position);this.data.ctrl[7]=op.grip;}
   if(op.grip!==null&&op.grip!==undefined)this.data.ctrl[7]=op.grip;
   if(op.type==='disturbance')this.data.xfrc_applied[6*this.cube+1]=2;
  }
 }
 step(){
  if(!this.running)return;if(this.replay){this.replayStep();return;}
  if(!this.op){this.next();if(!this.running||!this.op)return;}
  const op=this.op;op.elapsed+=.002;if(op.type==='move'){const u=Math.min(1,op.elapsed/op.motion),s=u*u*(3-2*u);for(let j=0;j<7;j++)this.data.ctrl[j]=op.from[j]+(op.to[j]-op.from[j])*s;}
  this.mj.mj_step(this.model,this.data);this.elapsed=this.data.time-this.startTime;
  // Contact information is for diagnostics and success evaluation, not perception.
  if(!this.collision&&this.condition==='occluded'){
   const cs=this.data.contact;for(let i=0;i<cs.size();i++){const c=cs.get(i),a=c.geom1,b=c.geom2,other=a===this.occluderGeom?b:b===this.occluderGeom?a:-1;
    if(other>=0&&this.model.geom_bodyid[other]>0&&this.model.geom_bodyid[other]<this.cube)this.collision=true;c.delete();}cs.delete();
  }
  if(op.elapsed>=op.duration){if(op.type==='disturbance')this.data.xfrc_applied.fill(0);this.op=null;}
  if(this.elapsed>25)this.finish('timeout');
 }
 finish(reason){
  this.running=false;this.op=null;this.queue=[];this.data.xfrc_applied.fill(0);
  const p=Array.from(this.data.xpos.slice(3*this.cube,3*this.cube+3)),width=this.data.qpos[7]+this.data.qpos[8],success=judgePlacement(p,width,this.collision);
  if(success)reason='placed';else if(this.collision)reason='obstacle_contact';else if(reason==='finished')reason='placement_failed';
  this.result={success,reason,duration_s:this.elapsed,placement_error_mm:Math.hypot(p[0]-.48,p[1]-.24)*1000,observations:this.observations,retries:this.retries,wall_ms:performance.now()-this.wallStart,seed:this.seed,condition:this.condition,method:this.method};this.emit(success?'success':'failure',{result:this.result});
 }
 loadReplay(run){this.reset(run.seed,run.condition);this.replay=run;this.elapsed=0;this.result=null;this.running=false;this.seek(0);}
 seek(t){if(!this.replay)return;const trace=this.replay.trace;this.elapsed=Math.max(0,Math.min(t,this.replay.duration_s));let r=trace[0];for(const row of trace){if(row.t>this.elapsed+1e-6)break;r=row;}if(r){this.data.qpos.set(r.qpos);this.mj.mj_forward(this.model,this.data);let event={phase:r.phase};for(const e of this.replay.events){if(e.t>this.elapsed+1e-6)break;event=e;}this.phase=event.phase;this.sync();this.onEvent({...event,t:this.elapsed,replay:true,terminal:this.elapsed>=this.replay.duration_s});}}
 replayStep(){this.seek(this.elapsed+.002);if(this.elapsed>=this.replay.duration_s)this.running=false;}
 animate(now){requestAnimationFrame(this.animate);const dt=Math.min(.08,(now-this.last)/1000);this.last=now;
  if(this.ready&&this.running){for(let i=0;i<Math.floor(dt*this.speed/.002);i++)this.step();this.sync();}
  this.controls.update();this.renderer.render(this.scene,this.camera);
 }
}

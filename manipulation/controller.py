"""Visual task state machine with motor execution and bounded re-observation.

Policy inputs are RGB-D target estimates, encoder state and gripper width.
Truth is read only for metrics after actions or when recording sensor accuracy.
"""
from pathlib import Path
import time
import cv2
import numpy as np
import mujoco
from .world import Workcell
from .perception import estimate_target

TRAY=np.array([.48,.24,.382])
ENABLE_RETRY = True
class Episode:
    def __init__(self,w,method,record=False,out=None):
        self.w=w;self.method=method;self.record=record;self.out=Path(out) if out else None
        if self.out:self.out.mkdir(parents=True,exist_ok=True)
        self.trace=[];self.events=[];self.observations=[];self.collisions=[]
        self.phase='observe';self.start=w.data.time;self.retries=0;self.sensing_ms=0;self.planning_ms=0
        self.initial_height=float(w.truth()[2]);self.max_height=self.initial_height;self.last_camera='front';self.target=None
        if self.record:self.trace.append({'t':0.,'qpos':w.data.qpos.round(6).tolist(),'ctrl':w.data.ctrl.round(6).tolist(),'phase':self.phase})
    def emit(self,phase,**kw):
        self.phase=phase;self.events.append({'t':round(self.w.data.time-self.start,3),'phase':phase,**kw})
    def tick(self):
        w=self.w;mujoco.mj_step(w.model,w.data)
        self.max_height=max(self.max_height,w.truth()[2])
        for c in w.data.contact:
            names=[mujoco.mj_id2name(w.model,mujoco.mjtObj.mjOBJ_GEOM,int(g)) or '' for g in [c.geom1,c.geom2]]
            if 'occluder_geom' in names:
                other=c.geom2 if names[0]=='occluder_geom' else c.geom1
                # Only robot contact; cube/environment contact is logged separately by physics.
                if w.model.geom_bodyid[other]<w.cube and w.model.geom_bodyid[other]>0:
                    event={'t':round(w.data.time-self.start,3),'position':c.pos.tolist(),'phase':self.phase}
                    if not self.collisions:self.collisions.append(event)
        if self.record and round(w.data.time/.002)%20==0:
            self.trace.append({'t':round(w.data.time-self.start,3),'qpos':w.data.qpos.round(6).tolist(),'ctrl':w.data.ctrl.round(6).tolist(),'phase':self.phase})
    def hold(self,duration):
        for _ in range(round(duration/.002)):self.tick()
    def move(self,pos,grip=255,duration=1.0):
        w=self.w;t=time.perf_counter();q=w.ik(pos);self.planning_ms+=(time.perf_counter()-t)*1000
        before=w.data.ctrl[:7].copy()
        for i in range(round(duration/.002)):
            u=(i+1)/(duration/.002);s=u*u*(3-2*u)
            w.command(before+(q-before)*s,grip);self.tick()
        self.hold(.15)
    def sense(self,camera):
        t=time.perf_counter();obs=self.w.observe(camera);estimate=estimate_target(**obs)
        ms=(time.perf_counter()-t)*1000;self.sensing_ms+=ms;self.last_camera=camera
        entry={'camera':camera,'t':round(self.w.data.time-self.start,3),'estimate':estimate,'processing_ms':ms}
        # Evaluation metadata, never returned as a policy input.
        entry['truth']=self.w.truth().tolist()
        entry['error_mm']=float(np.linalg.norm(np.array(estimate['position'])[:2]-self.w.truth()[:2])*1000) if estimate else None
        if self.out:
            name=f'camera-{len(self.observations)}.jpg';cv2.imwrite(str(self.out/name),cv2.cvtColor(obs['rgb'],cv2.COLOR_RGB2BGR),[cv2.IMWRITE_JPEG_QUALITY,90]);entry['image']=name
            raw=f'camera-{len(self.observations)}.npz'
            np.savez_compressed(self.out/raw,**obs);entry['rgbd']=raw
        self.observations.append(entry)
        self.emit('observe',camera=camera,detected=estimate is not None)
        return estimate
    def disturb(self):
        self.emit('disturbance',description='external lateral force: 2 N for 60 ms')
        self.w.data.xfrc_applied[self.w.cube,1]=2
        self.hold(.06);self.w.data.xfrc_applied[self.w.cube,:]=0;self.hold(.35)
    def execute(self):
        est=self.sense('front')
        if est is None and self.method=='feedback':
            self.emit('change_view');est=self.sense('back')
        if est is None:return 'target_missing'
        pos=np.array(est['position']);self.target=pos.tolist()
        if pos[0]>.70 or abs(pos[1])>.38:return 'outside_workspace'
        if self.w.condition=='shifted':self.disturb()
        for attempt in range(2 if self.method=='feedback' else 1):
            self.emit('approach',target=pos.tolist());self.move([pos[0],pos[1],.67],duration=1.4)
            if self.method=='feedback':
                fresh=self.sense('back')
                if fresh:
                    pos=np.array(fresh['position']);self.target=pos.tolist()
                    self.move([pos[0],pos[1],.62],duration=.6)
            self.emit('descend');self.move(pos,255,1.2)
            self.emit('close');self.w.command(self.w.data.ctrl[:7],0);self.hold(.9)
            self.emit('lift');self.move([pos[0],pos[1],.62],0,1.2)
            width=float(sum(self.w.data.qpos[7:9]))
            self.emit('verify_grasp',gripper_width_m=width,grasp_detected=width>.018)
            if width>.018:break
            if attempt==0 and self.method=='feedback' and ENABLE_RETRY:
                self.retries+=1;self.emit('retry');self.w.command(self.w.data.ctrl[:7],255);self.hold(.3)
                fresh=self.sense('back')
                if fresh:pos=np.array(fresh['position']);continue
            return 'empty_grasp'
        self.emit('transport');self.move([TRAY[0],TRAY[1],.67],0,1.5)
        self.emit('place');self.move([TRAY[0],TRAY[1],.415],0,1.1)
        self.emit('release');self.w.command(self.w.data.ctrl[:7],255);self.hold(.6)
        self.emit('retreat');self.move([TRAY[0],TRAY[1],.69],255,1.0);self.hold(.4)
        return 'finished'
    def result(self,reason,wall):
        w=self.w;final=w.truth();width=float(sum(w.data.qpos[7:9]))
        placed=bool(abs(final[0]-.48)<.065 and abs(final[1]-.24)<.06 and .37<final[2]<.42 and width>.065)
        success=placed and not self.collisions
        if success:reason='placed'
        elif self.collisions:reason='obstacle_contact'
        elif reason=='finished':reason='placement_failed'
        self.emit('success' if success else 'failure',reason=reason)
        if self.record:self.trace.append({'t':round(w.data.time-self.start,3),'qpos':w.data.qpos.round(6).tolist(),'ctrl':w.data.ctrl.round(6).tolist(),'phase':self.phase})
        errors=[o['error_mm'] for o in self.observations if o['error_mm'] is not None]
        return {'retry_enabled': self.method == 'feedback' and ENABLE_RETRY,'id':f'{w.condition}-{w.seed}-{self.method}','seed':w.seed,'condition':w.condition,'method':self.method,'success':success,'reason':reason,'initial_target':w.initial.tolist(),'final_target':final.tolist(),'final_gripper_width_m':width,'placement_error_mm':float(np.linalg.norm(final[:2]-TRAY[:2])*1000),'lift_height_m':float(self.max_height-self.initial_height),'perception_error_mm':float(np.mean(errors)) if errors else None,'observations':len(self.observations),'retries':self.retries,'collisions':self.collisions,'duration_s':w.data.time-self.start,'wall_ms':wall,'sensing_ms':self.sensing_ms,'planning_ms':self.planning_ms,'events':self.events,'sensors':self.observations,'trace':self.trace}

def run(seed=10,condition='normal',method='feedback',record=False,out=None):
    if condition not in ['normal','occluded','shifted','unreachable']:raise ValueError(condition)
    if method not in ['one_shot','feedback']:raise ValueError(method)
    with Workcell(seed,condition) as w:
        e=Episode(w,method,record,out);t=time.perf_counter();reason=e.execute();return e.result(reason,(time.perf_counter()-t)*1000)

if __name__=='__main__':
    import argparse,json
    ap=argparse.ArgumentParser();ap.add_argument('--seed',type=int,default=10);ap.add_argument('--condition',default='normal');ap.add_argument('--method',default='feedback');ap.add_argument('--out',default='work/v3/sample')
    ap.add_argument('--no-retry', action='store_true', help='Stop after an empty grasp; keep feedback observations enabled.')
    args=ap.parse_args()
    if args.no_retry:
        ENABLE_RETRY = False
    r=run(args.seed,args.condition,args.method,True,args.out)
    Path(args.out,'run.json').write_text(json.dumps(r,indent=2))
    print(json.dumps({k:v for k,v in r.items() if k not in ['trace','sensors','events']},indent=2))

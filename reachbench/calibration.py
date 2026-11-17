"""Translation-only calibration from rendered, surveyed green reference markers.
The estimator receives observed reference coordinates, not target GT or injected bias.
Legacy sim.py and the original 400 records remain unchanged.
"""
from dataclasses import asdict
from pathlib import Path
from copy import deepcopy
from collections import Counter
import argparse,csv,hashlib,json,platform,time
import cv2
import numpy as np
import pybullet as p
from .sim import World,scene,perceive,pixel_to_world,plan,fk,QSTART,TARGET_Z,W
from .recording import record_trace
from .evaluate import wilson

MARKERS=np.array([[-.82,-.65],[.82,-.65],[-.82,.65],[.82,.65]])
MIN_MARKERS=3;MAX_RESIDUAL_M=.012
OFFSETS_MM=[0,20,40,65,100]
PROFILES=['standard','markers_missing','board_shift']

class ReferenceWorld(World):
    def __init__(self,s,profile='standard'):
        super().__init__(s);self.profile=profile
        shift=.05 if profile=='board_shift' else 0.
        for i,(x,y) in enumerate(MARKERS):
            # Missing references are a true scene change (not bypassed by the estimator).
            if profile=='markers_missing' and i>=2:continue
            visual=p.createVisualShape(p.GEOM_CYLINDER,radius=.035,length=TARGET_Z,rgbaColor=[.08,.88,.25,1],physicsClientId=self.cid)
            p.createMultiBody(0,-1,visual,[float(x+shift),float(y),TARGET_Z/2],physicsClientId=self.cid)

def reference_observations(rgb,project_pixel):
    hsv=cv2.cvtColor(rgb,cv2.COLOR_RGB2HSV)
    mask=cv2.inRange(hsv,(42,110,30),(82,255,255))
    mask=cv2.morphologyEx(mask,cv2.MORPH_OPEN,np.ones((3,3),np.uint8))
    contours,_=cv2.findContours(mask,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
    obs=[];ids=set()
    for c in contours:
        if cv2.contourArea(c)<7:continue
        (u,v),radius=cv2.minEnclosingCircle(c)
        # Fixed overhead camera + separated reference quadrants provide marker IDs.
        key=int(u>W/2)+2*int(v<W/2)
        if key in ids:return [],'ambiguous_marker'
        ids.add(key);obs.append({'id':key,'pixel':[float(u),float(v)],'measured_xy':project_pixel(u,v),'expected_xy':MARKERS[key].tolist()})
    return sorted(obs,key=lambda x:x['id']),None

def estimate_translation(observations,*,min_markers=MIN_MARKERS,max_residual=MAX_RESIDUAL_M):
    if len(observations)<min_markers:return {'accepted':False,'reason':'insufficient_references','count':len(observations),'offset_xy':None,'residual_max_mm':None}
    deltas=np.array([np.array(o['measured_xy'])-o['expected_xy'] for o in observations])
    offset=np.median(deltas,axis=0);residual=np.linalg.norm(deltas-offset,axis=1)
    accepted=bool(np.max(residual)<=max_residual)
    return {'accepted':accepted,'reason':'accepted' if accepted else 'inconsistent_references','count':len(observations),'offset_xy':offset.tolist(),'residual_max_mm':float(np.max(residual)*1000)}

def correct_detection(det,offset):
    out=deepcopy(det)
    for item in ([out['target']] if out['target'] else [])+out['obstacles']:
        item['xy']=(np.array(item['xy'])-offset).tolist()
    return out

def run_pair(s,profile='standard',directory=None,record=False):
    world=ReferenceWorld(s,profile);rgb=world.image();rows=[]
    try:
        input_hash=hashlib.sha256(rgb.tobytes()).hexdigest()
        for method in ['uncorrected','reference']:
            world.setq(QSTART)
            start=time.perf_counter();det=perceive(rgb,'hsv',s.calibration_dx);perception_ms=(time.perf_counter()-start)*1000
            before=deepcopy(det);calibration=None;observations=[];calibration_ms=0.
            if method=='reference':
                start=time.perf_counter()
                observations,problem=reference_observations(rgb,lambda u,v:pixel_to_world(u,v,TARGET_Z,s.calibration_dx))
                calibration=estimate_translation(observations)
                if problem:calibration['reason']=problem
                if calibration['accepted']:det=correct_detection(det,np.array(calibration['offset_xy']))
                calibration_ms=(time.perf_counter()-start)*1000
            path=None;reason='target_missing';planning_ms=0.
            if method=='reference' and not calibration['accepted']:reason='calibration_unavailable'
            elif det['target']:
                start=time.perf_counter();path,reason=plan(det['target']['xy'],[[*o['xy'],o['radius']] for o in det['obstacles']],'astar');planning_ms=(time.perf_counter()-start)*1000
            qs=[QSTART.copy()]
            if path:
                for a,b in zip(path[:-1],path[1:]):
                    n=max(1,int(np.ceil(np.max(np.abs(b-a))/.025)))
                    qs.extend(a+(b-a)*k/n for k in range(1,n+1))
            trace=[];length=0.;last=fk(QSTART)[-1];hit=False
            for i,q in enumerate(qs):
                world.setq(q);tip=fk(q)[-1];length+=np.linalg.norm(tip-last);last=tip;hit=world.collision()
                trace.append({'t':round(i*.05,3),'q':q.tolist(),'joints':fk(q).tolist(),'collision':bool(hit)})
                if hit:reason='collision';break
            error=float(np.linalg.norm(last-s.target)*1000);success=bool(path and not hit and error<=35)
            if success:reason='reached'
            elif path and not hit:reason='position_error'
            uid=f'{profile}-{int(round(s.calibration_dx*1000))}-{s.seed}-{method}'
            r={'id':uid,'suite':'calibration-v2','seed':s.seed,'condition':profile,'profile':profile,'bias_mm':int(round(s.calibration_dx*1000)),'method':method,'scene':asdict(s),'input_sha256':input_hash,'detected_before':before,'detected':det,'calibration':calibration,'reference_observations':observations,'trace':trace,'frames':len(trace),'success':success,'reason':reason,'collision':bool(hit),'endpoint_error_mm':error,'perception_error_mm':float(np.linalg.norm(np.array(det['target']['xy'])-s.target)*1000) if det['target'] else None,'perception_ms':perception_ms,'calibration_ms':calibration_ms,'planning_ms':planning_ms,'pipeline_ms':perception_ms+calibration_ms+planning_ms,'duration_s':trace[-1]['t'],'path_length_m':float(length)}
            if directory:
                d=Path(directory);d.mkdir(parents=True,exist_ok=True)
                (d/f'{uid}.json').write_text(json.dumps(r,separators=(',',':')))
                cam=d/'cameras'/f'{profile}-{r["bias_mm"]}-{s.seed}.png';cam.parent.mkdir(exist_ok=True)
                if not cam.exists():cv2.imwrite(str(cam),cv2.cvtColor(rgb,cv2.COLOR_RGB2BGR))
                if record:record_trace(r,d/'recordings'/uid,world)
            rows.append(r)
        assert rows[0]['input_sha256']==rows[1]['input_sha256']
        return rows
    finally:world.close()

def summarize(rows):
    out={}
    for profile in PROFILES:
        out[profile]={}
        for bias in ['all']+OFFSETS_MM:
            group=[r for r in rows if r['profile']==profile and (bias=='all' or r['bias_mm']==bias)]
            if not group:continue
            out[profile][str(bias)]={}
            for method in ['uncorrected','reference']:
                rs=[r for r in group if r['method']==method];n=len(rs);k=sum(r['success'] for r in rs)
                if not n:continue
                out[profile][str(bias)][method]={'n':n,'successes':k,'success_rate':k/n,'wilson95':wilson(k,n),'collisions':sum(r['collision'] for r in rs),'perception_error_mean_mm':float(np.mean([r['perception_error_mm'] for r in rs if r['perception_error_mm'] is not None])),'endpoint_error_mean_mm':float(np.mean([r['endpoint_error_mm'] for r in rs])),'pipeline_median_ms':float(np.median([r['pipeline_ms'] for r in rs])),'pipeline_p95_ms':float(np.percentile([r['pipeline_ms'] for r in rs],95)),'calibration_median_ms':float(np.median([r['calibration_ms'] for r in rs])),'reasons':dict(Counter(r['reason'] for r in rs))}
    return out

def evaluate(out,start,count,split,record=False):
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    config={'split':split,'seeds':list(range(start,start+count)),'offsets_mm':OFFSETS_MM,'profiles':{'standard':OFFSETS_MM,'markers_missing':[65],'board_shift':[65]},'methods':['uncorrected','reference'],'success_threshold_mm':35,'min_markers':MIN_MARKERS,'max_residual_mm':MAX_RESIDUAL_M*1000,'markers_nominal_xy':MARKERS.tolist(),'board_shift_mm':50,'legacy_engine_sha256':hashlib.sha256(Path(__file__).with_name('sim.py').read_bytes()).hexdigest(),'experiment_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'python':platform.python_version(),'platform':platform.platform(),'training':'none','ground_truth_policy':'Target/obstacle GT is evaluation only. Surveyed reference positions are known calibration inputs.'}
    (out/'config.json').write_text(json.dumps(config,indent=2));rows=[];begin=time.perf_counter()
    for profile,offsets in config['profiles'].items():
        for bias in offsets:
            for seed in config['seeds']:
                s=scene(seed);s.calibration_dx=bias/1000
                pair=run_pair(s,profile,out,record)
                for r in pair:rows.append({k:v for k,v in r.items() if k not in ['trace','scene','detected','detected_before','reference_observations','calibration']})
                print(profile,bias,seed,[r['reason'] for r in pair],flush=True)
    summary={'config':config,'wall_seconds_including_media':time.perf_counter()-begin,'metrics':summarize(rows),'episodes':rows}
    (out/'summary.json').write_text(json.dumps(summary,indent=2))
    with (out/'episodes.csv').open('w') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    return summary

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--out',default='dist/data-v2');ap.add_argument('--start',type=int,default=3000);ap.add_argument('--count',type=int,default=20);ap.add_argument('--split',choices=['development','evaluation'],default='evaluation');ap.add_argument('--record',action='store_true');a=ap.parse_args()
    evaluate(a.out,a.start,a.count,a.split,a.record)

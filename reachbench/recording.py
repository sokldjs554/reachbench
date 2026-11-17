"""Recorded PyBullet observer frames + contact events, indexed by exact trace sample.
The observer camera is for presentation only; perception still uses World.image().
"""
from pathlib import Path
import hashlib,json,math
import cv2
import numpy as np
import pybullet as p
from .sim import World,Scene,rollout

FRAME_W,FRAME_H=320,240
COLS,PER_PAGE=8,40
OBSERVER={'eye':[1.15,-1.8,1.55],'target':[-.10,.03,.10],'up':[0,0,1],'fov':44}

def observer_image(world):
    view=p.computeViewMatrix(OBSERVER['eye'],OBSERVER['target'],OBSERVER['up'])
    proj=p.computeProjectionMatrixFOV(OBSERVER['fov'],FRAME_W/FRAME_H,.1,5)
    raw=p.getCameraImage(FRAME_W,FRAME_H,view,proj,renderer=p.ER_TINY_RENDERER,shadow=1,lightDirection=[-.4,-.8,2],physicsClientId=world.cid)
    return np.array(raw[2],dtype=np.uint8).reshape(FRAME_H,FRAME_W,4)[:,:,:3].copy()

def contact_points(world):
    out=[]
    for i,body in enumerate(world.obs_ids):
        for c in p.getClosestPoints(world.robot,body,0,physicsClientId=world.cid):
            out.append({'obstacle_index':i,'link_index':int(c[3]),'point_on_robot':list(c[5]),'point_on_obstacle':list(c[6]),'distance_m':float(c[8])})
    return out

def trace_hash(trace):
    return hashlib.sha256(json.dumps(trace,sort_keys=True,separators=(',',':')).encode()).hexdigest()

def record_trace(run,directory,world=None,stride=2):
    """Execute the stored kinematic states again and render only those exact states.
    Contact queries run at *every* sample. Frame indices include both final and contact samples.
    """
    d=Path(directory);d.mkdir(parents=True,exist_ok=True)
    owns=world is None;world=world or World(Scene(**run['scene']))
    trace=run['trace'];chosen=set(range(0,len(trace),stride))|{len(trace)-1}
    chosen.update(i for i,f in enumerate(trace) if f['collision'])
    frames=[];events=[];pixels=[]
    try:
        for i,f in enumerate(trace):
            world.setq(f['q']);contacts=contact_points(world)
            if bool(contacts)!=f['collision']:raise AssertionError(f'Collision replay mismatch: sample {i}')
            if contacts:events.append({'trace_index':i,'t':f['t'],'contacts':contacts})
            if i in chosen:
                j=len(frames);frames.append({'trace_index':i,'t':f['t'],'page':j//PER_PAGE,'tile':j%PER_PAGE,'q':f['q']})
                pixels.append(observer_image(world))
        pages=[]
        for start in range(0,len(pixels),PER_PAGE):
            batch=pixels[start:start+PER_PAGE];rows=math.ceil(len(batch)/COLS)
            sheet=np.zeros((FRAME_H*rows,FRAME_W*COLS,3),dtype=np.uint8)
            for j,im in enumerate(batch):sheet[j//COLS*FRAME_H:(j//COLS+1)*FRAME_H,j%COLS*FRAME_W:(j%COLS+1)*FRAME_W]=im
            name=f'page-{len(pages):03}.webp'
            ok=cv2.imwrite(str(d/name),cv2.cvtColor(sheet,cv2.COLOR_RGB2BGR),[cv2.IMWRITE_WEBP_QUALITY,82])
            if not ok:raise RuntimeError('WebP encoding unavailable')
            pages.append({'file':name,'columns':COLS,'rows':rows,'sha256':hashlib.sha256((d/name).read_bytes()).hexdigest()})
        meta={'run_id':run['id'],'kind':'pybullet-recorded-frames','camera_role':'observer_only_not_perception','camera':OBSERVER,'width':FRAME_W,'height':FRAME_H,'stride':stride,'trace_sha256':trace_hash(trace),'frames':frames,'pages':pages,'contacts':events,'execution':'resetJointState + collision queries; not motor dynamics'}
        (d/'recording.json').write_text(json.dumps(meta,indent=2))
        return meta
    finally:
        if owns:world.close()

def legacy_recordings(root='dist',seeds=None):
    root=Path(root);summary=json.loads((root/'data/summary.json').read_text());records=[]
    for row in summary['episodes']:
        if row['method'] not in ['baseline','improved'] or (seeds is not None and row['seed'] not in seeds):continue
        old=json.loads((root/'data'/f"{row['id']}.json").read_text())
        # Fresh rerun of the unchanged legacy engine, not generated or guessed motion.
        new=rollout(Scene(**old['scene']),old['method']);new['id']=old['id']
        for key in ['trace','detected','success','reason','endpoint_error_mm']:
            if new[key]!=old[key]:raise AssertionError(f'{old["id"]}: fresh run mismatch {key}')
        meta=record_trace(new,root/'media/legacy'/old['id'])
        records.append({'id':old['id'],'legacy_sha256':hashlib.sha256((root/'data'/f"{old['id']}.json").read_bytes()).hexdigest(),'trace_sha256':meta['trace_sha256'],'matched_fresh_execution':True,'observer_frames':len(meta['frames']),'contact_events':len(meta['contacts']),'fresh_perception_ms':new['perception_ms'],'fresh_planning_ms':new['planning_ms']})
        print(old['id'],len(meta['frames']),'frames',flush=True)
    manifest={'original_results_unchanged':True,'engine_sha256':hashlib.sha256(Path(__file__).with_name('sim.py').read_bytes()).hexdigest(),'records':records,'note':'Fresh legacy rerun matches every recorded state; observer frames re-execute those exact states. Observer view does not remove the input occlusion patch.'}
    (root/'media/legacy/manifest.json').write_text(json.dumps(manifest,indent=2))
    return manifest

if __name__=='__main__':
    import argparse
    ap=argparse.ArgumentParser();ap.add_argument('--root',default='dist');ap.add_argument('--seeds',nargs='*',type=int);a=ap.parse_args()
    legacy_recordings(a.root,a.seeds)

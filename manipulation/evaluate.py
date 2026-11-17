"""Paired held-out benchmark. All outcomes, including failures, are retained."""
import argparse,json,hashlib,platform,time
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
import numpy as np
import mujoco
from .controller import run

CONDITIONS=['normal','occluded','shifted','unreachable']
METHODS=['one_shot','feedback']
def summarize(rows):
    groups=[]
    for condition in CONDITIONS+['all']:
        for method in METHODS:
            rs=[r for r in rows if r['method']==method and (condition=='all' or r['condition']==condition)]
            if not rs:continue
            errors=[r['perception_error_mm'] for r in rs if r['perception_error_mm'] is not None]
            groups.append(dict(condition=condition,method=method,n=len(rs),successes=sum(r['success'] for r in rs),success_rate=sum(r['success'] for r in rs)/len(rs),placement_error_mm=float(np.mean([r['placement_error_mm'] for r in rs])),perception_error_mm=float(np.mean(errors)) if errors else None,collisions=sum(bool(r['collisions']) for r in rs),wall_ms=float(np.mean([r['wall_ms'] for r in rs])),sensing_ms=float(np.mean([r['sensing_ms'] for r in rs])),planning_ms=float(np.mean([r['planning_ms'] for r in rs])),observations=float(np.mean([r['observations'] for r in rs])),retries=sum(r['retries'] for r in rs),failures={s:sum(r['reason']==s for r in rs) for s in sorted(set(r['reason'] for r in rs)) if s!='placed'}))
    return groups
def worker(args):
    seed,condition,method,out,record=args
    return run(seed,condition,method,record,Path(out)/f'{condition}-{seed}-{method}' if record else None)
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--split',choices=['dev','eval'],required=True);ap.add_argument('--out',required=True);ap.add_argument('--workers',type=int,default=2);a=ap.parse_args()
    seeds=list(range(10,15)) if a.split=='dev' else list(range(100,120));out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
    args=[(s,c,m,str(out/'runs'),a.split=='eval' and (s in [100,101] or (s==107 and c=='shifted' and m=='feedback'))) for s in seeds for c in CONDITIONS for m in METHODS]
    rows=[];started=time.perf_counter()
    with ProcessPoolExecutor(max_workers=a.workers) as pool:
        for r in pool.map(worker,args):
            rows.append(r)
            if r['trace']:(out/'runs'/r['id']/'run.json').write_text(json.dumps(r,separators=(',',':')))
            print(r['id'],r['reason'],round(r['placement_error_mm'],1),flush=True)
    compact=[{k:v for k,v in r.items() if k!='trace'} for r in rows]
    (out/'episodes.json').write_text(json.dumps(compact,indent=2))
    summary=summarize(rows);(out/'summary.json').write_text(json.dumps(summary,indent=2))
    root=Path(__file__).parent
    config={'split':a.split,'seeds':seeds,'conditions':CONDITIONS,'methods':METHODS,'trials':len(rows),'model':'Franka Emika Panda / MuJoCo Menagerie','mujoco':mujoco.__version__,'python':platform.python_version(),'platform':platform.platform(),'workers':a.workers,'total_wall_s':time.perf_counter()-started,'timing_note':'Per episode time includes cold RGB-D renderer creation and physics/control; parallel workers contend for CPU. Not robot hardware latency.','training':'none; fixed color segmentation, RGB-D geometry, analytic IK, task state machine','success':'Released cube inside tray XY ±65/60 mm, Z in (370,420) mm; fingers open >65 mm; no robot/occluder contact','source_hashes':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in root.glob('*.py')},'model_sha256':hashlib.sha256((root/'assets/workcell.xml').read_bytes()).hexdigest()}
    (out/'config.json').write_text(json.dumps(config,indent=2))
    print(json.dumps(summary,indent=2))
if __name__=='__main__':main()

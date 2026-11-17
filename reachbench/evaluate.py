"""Deterministic paired evaluation; no cherry-picking or discarded hard scenes."""
import argparse,csv,json,platform,time,hashlib
from pathlib import Path
from collections import Counter
import numpy as np
from .sim import scene,rollout,METHODS
CONDITIONS=['nominal','dim','clutter','occluded','calibration']

def wilson(k,n):
    z=1.96;p=k/n;den=1+z*z/n;mid=(p+z*z/(2*n))/den
    half=z*np.sqrt(p*(1-p)/n+z*z/(4*n*n))/den
    return [float(max(0.,mid-half)),float(min(1.,mid+half))]

def aggregate(rows):
    result={}
    for m in METHODS:
        result[m]={}
        for c in ['all']+CONDITIONS:
            a=[r for r in rows if r['method']==m and (c=='all' or r['condition']==c)]
            if not a:continue
            n=len(a);k=sum(r['success'] for r in a)
            errors=[r['perception_error_mm'] for r in a if r['perception_error_mm'] is not None]
            result[m][c]={'n':n,'successes':k,'success_rate':k/n,'wilson95':wilson(k,n),'detected_n':len(errors),'perception_error_mean_mm':float(np.mean(errors)) if errors else None,'endpoint_error_mean_mm':float(np.mean([r['endpoint_error_mm'] for r in a])),'perception_median_ms':float(np.median([r['perception_ms'] for r in a])),'planning_median_ms':float(np.median([r['planning_ms'] for r in a])),'planning_p95_ms':float(np.percentile([r['planning_ms'] for r in a],95)),'reasons':dict(Counter(r['reason'] for r in a))}
    return result

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--start',type=int,default=1000);ap.add_argument('--count',type=int,default=20);ap.add_argument('--out',default='dist/data');args=ap.parse_args()
    out=Path(args.out);out.mkdir(parents=True,exist_ok=True);rows=[];begin=time.time()
    # This manifest is written before execution. The evaluated range is not tuned afterward.
    config={'seeds':list(range(args.start,args.start+args.count)),'conditions':CONDITIONS,'methods':METHODS,'success_tolerance_mm':35,'joint_step_max_rad':.025,'nominal_sample_dt_s':.05,'camera':'320x320 RGB, perspective 47 deg, height 2.6 m','training':'none; fixed color thresholds and analytic kinematics','evaluation':'kinematic motion, discrete PyBullet collision queries, no motor dynamics','python':platform.python_version(),'platform':platform.platform(),'source_sha256':hashlib.sha256(Path(__file__).with_name('sim.py').read_bytes()).hexdigest()}
    (out/'config.json').write_text(json.dumps(config,indent=2))
    for c in CONDITIONS:
        for seed in config['seeds']:
            for method in METHODS:
                uid=f'{c}-{seed}-{method}'
                r=rollout(scene(seed,c),method,out/'frames'/uid)
                r['id']=uid
                (out/f'{uid}.json').write_text(json.dumps(r,separators=(',',':')))
                rows.append({k:v for k,v in r.items() if k not in ['trace','detected','scene']})
            print(c,seed,'done',round(time.time()-begin,1),flush=True)
    summary={'config':config,'wall_seconds':time.time()-begin,'metrics':aggregate(rows),'episodes':rows}
    (out/'summary.json').write_text(json.dumps(summary,indent=2))
    with (out/'episodes.csv').open('w') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    print(json.dumps({m:summary['metrics'][m]['all'] for m in METHODS},indent=2))
if __name__=='__main__':main()

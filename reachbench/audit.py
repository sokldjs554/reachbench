"""Validate recordings, build per-scene dataset manifest and source/data checksums."""
from pathlib import Path
import hashlib,json,csv
import cv2
import numpy as np
from .evaluate import aggregate

def main():
 root=Path('dist/data');s=json.loads((root/'summary.json').read_text());assert s['metrics']==aggregate(s['episodes'])
 rows=[];keys=set()
 for row in s['episodes']:
  r=json.loads((root/(row['id']+'.json')).read_text())
  assert r['id'] not in keys;keys.add(r['id'])
  assert all(np.all(np.isfinite(f['q'])) and len(f['joints'])==3 for f in r['trace'])
  assert all(a['t']<b['t'] for a,b in zip(r['trace'],r['trace'][1:]))
  p=root/'cameras'/f"{r['condition']}-{r['seed']}.png";im=cv2.imread(str(p));assert im is not None and im.shape==(320,320,3)
  if r['method']=='baseline':
   rows.append({'scene_id':f"{r['condition']}-{r['seed']}",'seed':r['seed'],'condition':r['condition'],'rgb_path':str(p.relative_to(root)),'rgb_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'width':320,'height':320,'target_x_m':r['scene']['target'][0],'target_y_m':r['scene']['target'][1],'obstacles_json':json.dumps(r['scene']['obstacles']),'split':'evaluation','synthetic':True})
 with (root/'dataset.csv').open('w') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
 # SHA inventory permits downloaded-data corruption checks. Exclude this inventory itself.
 hashes={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(root.rglob('*')) if p.is_file() and p.name!='checksums.json' and not any(x.startswith('local-') for x in p.parts)}
 (root/'checksums.json').write_text(json.dumps(hashes,indent=2))
 report={'episodes_validated':len(keys),'unique_scenes':len(rows),'invalid_records':0,'files_hashed':len(hashes),'checks':['unique episode IDs','strictly increasing timestamps','finite joints','RGB shape and decode','summary recomputation'],'excluded_records':0}
 Path('docs/data-audit.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
if __name__=='__main__':main()

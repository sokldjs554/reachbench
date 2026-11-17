import json
from pathlib import Path
import numpy as np
import pytest
from reachbench.sim import *
from reachbench.evaluate import aggregate,wilson

@pytest.mark.parametrize('q',[[.3,1.1],[-.6,1.8],[.8,-1.4]])
def test_inverse_forward_kinematics(q):
    point=fk(q)[-1]
    assert any(np.linalg.norm(fk(g)[-1]-point)<1e-9 for g in ik(point))

def test_camera_roundtrip():
    for z in [TARGET_Z,OBSTACLE_Z]:
        xy=[.21,.35];assert np.allclose(pixel_to_world(*world_to_pixel(xy,z),z),xy)

def test_pixel_only_detector_translation():
    image=np.zeros((W,W,3),np.uint8)
    cv2.circle(image,(190,130),7,(240,35,20),-1)
    d=perceive(image,'hsv');assert d['target'] is not None
    assert np.allclose(d['target']['xy'],pixel_to_world(190,130,TARGET_Z))
    assert perceive(np.zeros_like(image),'hsv')['target'] is None

def test_swept_edge_checks_midpoint():
    a=np.array([-.7,1.]);b=np.array([.7,1.]);o=[[*fk((a+b)/2)[1],.035]]
    assert clearance(a,o)>0 and clearance(b,o)>0
    assert not edge(a,b,o)

def test_bullet_geometry_matches_fk_and_collision():
    s=scene(100);w=World(s)
    try:
        for q in [[-.4,1.2],[.3,-.5]]:
            w.setq(q)
            pos=p.getLinkState(w.robot,1,physicsClientId=w.cid)[4]
            assert np.allclose(pos[:2],fk(q)[1],atol=1e-6)
        x,y,_=s.obstacles[0];q1=np.arctan2(y,x-BASE[0]);w.setq([q1,0])
        assert w.collision()
    finally:w.close()

def test_metrics_known_counts():
    assert wilson(0,10)[0]==0
    assert wilson(20,20)[1]==1 and wilson(0,20)[0]>=0
    rows=[{'method':'baseline','condition':'nominal','success':s,'perception_error_mm':e,'endpoint_error_mm':10,'perception_ms':1,'planning_ms':2,'reason':'reached' if s else 'collision'} for s,e in [(True,3),(False,None)]]
    m=aggregate(rows)['baseline']['all'];assert m['success_rate']==.5 and m['n']==2 and m['detected_n']==1 and m['perception_error_mean_mm']==3

def test_repeatable_rollout_and_missing_target_stop():
    a=rollout(scene(18,'occluded'),'improved');b=rollout(scene(18,'occluded'),'improved')
    assert a['trace']==b['trace'] and a['reason']=='target_missing' and a['frames']==1

def test_exported_metrics_and_trace():
    root=Path('dist/data');summary=root/'summary.json'
    if not summary.exists():pytest.skip('run benchmark to validate artifacts')
    s=json.loads(summary.read_text());assert aggregate(s['episodes'])==s['metrics']
    for row in s['episodes']:
        r=json.loads((root/(row['id']+'.json')).read_text())
        assert len(r['trace'])==row['frames']
        assert r['trace'][-1]['t']==row['duration_s']
        error=np.linalg.norm(np.array(r['trace'][-1]['joints'][-1])-r['scene']['target'])*1000
        assert error==pytest.approx(row['endpoint_error_mm'])
        assert row['success']==(row['reason']=='reached')
        if row['success']:assert error<=35 and not any(f['collision'] for f in r['trace'])

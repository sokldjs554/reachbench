import numpy as np
from manipulation.perception import estimate_target
from manipulation.world import Workcell

def test_empty_image_has_no_target():
    rgb=np.zeros((128,128,3),np.uint8)
    assert estimate_target(rgb,np.ones((128,128)),np.eye(3),np.zeros(3),45) is None

def test_rgbd_localization_uses_pixels_and_calibration():
    with Workcell(10,'normal') as w:
        obs=w.observe('front')
        est=estimate_target(**obs)
        assert est is not None
        assert np.linalg.norm(est['position'][:2]-w.truth()[:2])<.008

def test_physical_occluder_and_second_view():
    with Workcell(10,'occluded') as w:
        first=estimate_target(**w.observe('front'))
        second=estimate_target(**w.observe('back'))
        assert first is None
        assert second is not None

def test_motor_motion_does_not_teleport():
    with Workcell(10,'normal') as w:
        before=w.data.qpos[:7].copy()
        target=before.copy();target[0]+=.3
        w.command(target,255)
        np.testing.assert_array_equal(w.data.qpos[:7],before)
        w.advance(.2)
        assert abs(w.data.qpos[0]-before[0])>.01

def test_cube_is_physically_grasped_and_released():
    from manipulation.controller import run
    result=run(10,'normal','feedback')
    assert result['success'],result['reason']
    assert result['lift_height_m']>.07
    assert result['final_gripper_width_m']>.065

def test_hidden_target_baseline_halts_and_feedback_recovers():
    from manipulation.controller import run
    a=run(10,'occluded','one_shot');b=run(10,'occluded','feedback')
    assert a['reason']=='target_missing'
    assert a['observations']==1
    assert b['observations']>=2
    assert b['success'],b['reason']
    assert a['initial_target']==b['initial_target']

def test_recorded_halt_has_initial_pose_and_raw_sensor(tmp_path):
    from manipulation.controller import run
    r=run(100,'occluded','one_shot',True,tmp_path)
    assert r['duration_s']==0 and len(r['trace'])==2
    assert len(r['trace'][0]['ctrl'])==8
    raw=np.load(tmp_path/r['sensors'][0]['rgbd'])
    assert raw['rgb'].shape==(224,224,3)
    assert raw['depth'].shape==(224,224)
    assert estimate_target(**dict(raw)) is None

def test_exported_evaluation_matches_raw_episodes():
    import json
    from pathlib import Path
    from manipulation.evaluate import summarize
    root=Path('dist/bench');rows=json.loads((root/'episodes.json').read_text())
    assert len(rows)==160
    assert summarize(rows)==json.loads((root/'summary.json').read_text())
    for seed in range(100,120):
        for condition in ['normal','occluded','shifted','unreachable']:
            pair=[r for r in rows if r['seed']==seed and r['condition']==condition]
            assert len(pair)==2 and pair[0]['initial_target']==pair[1]['initial_target']
    for path in (root/'runs').glob('*/run.json'):
        r=json.loads(path.read_text());row=next(x for x in rows if x['id']==r['id'])
        assert {k:v for k,v in r.items() if k!='trace'}==row
        assert r['trace'] and r['trace'][0]['t']==0

def test_retry_bound_and_unreachable_halt():
    from manipulation.controller import run
    r=run(100,'unreachable','feedback')
    assert not r['success'] and r['duration_s']==0
    assert r['observations']==2 and r['retries']==0
    assert r['lift_height_m']==0

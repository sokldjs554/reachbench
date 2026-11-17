import hashlib,json
from pathlib import Path
import cv2
import numpy as np
import pytest
from reachbench.calibration import estimate_translation,run_pair,summarize
from reachbench.sim import scene,fk,QSTART
from reachbench.recording import trace_hash

def observations(delta):
    return [{'measured_xy':(np.array(p)+delta).tolist(),'expected_xy':p} for p in [[-.8,-.6],[.8,-.6],[-.8,.6],[.8,.6]]]

def test_translation_estimated_from_reference_pairs():
    r=estimate_translation(observations(np.array([.073,-.021])))
    assert r['accepted'] and np.allclose(r['offset_xy'],[.073,-.021])
    assert r['residual_max_mm']<1e-9

def test_reference_quality_gate():
    assert not estimate_translation(observations([.065,0])[:2])['accepted']
    o=observations([.065,0]);o[0]['measured_xy'][0]+=.05
    assert estimate_translation(o)['reason']=='inconsistent_references'

def test_common_reference_error_is_not_observable_from_residual():
    r=estimate_translation(observations([.015,0]))
    # All wrongly surveyed references can agree: the residual is not absolute accuracy.
    assert r['accepted'] and r['residual_max_mm']<1e-9

@pytest.mark.parametrize('profile',['standard','markers_missing','board_shift'])
def test_reproduce_held_out_pair(profile):
    s=scene(3000);s.calibration_dx=.065
    rows=run_pair(s,profile)
    assert rows[0]['input_sha256']==rows[1]['input_sha256']
    for r in rows:
        saved=json.loads(Path(f"dist/data-v2/{r['id']}.json").read_text())
        for key in ['trace','detected','calibration','reason','endpoint_error_mm','perception_error_mm']:
            assert r[key]==saved[key]
    if profile=='standard':assert rows[1]['success'] and not rows[0]['success']
    if profile=='markers_missing':assert rows[1]['reason']=='calibration_unavailable' and rows[1]['duration_s']==0

def test_new_summary_and_input_integrity():
    root=Path('dist/data-v2');s=json.loads((root/'summary.json').read_text())
    assert len(s['episodes'])==280 and summarize(s['episodes'])==s['metrics']
    assert not set(s['config']['seeds']) & {2000,2001,2002}
    for r in s['episodes']:
        full=json.loads((root/f"{r['id']}.json").read_text())
        rgb=cv2.cvtColor(cv2.imread(str(root/'cameras'/f"{r['profile']}-{r['bias_mm']}-{r['seed']}.png")),cv2.COLOR_BGR2RGB)
        assert hashlib.sha256(rgb.tobytes()).hexdigest()==r['input_sha256']
        assert r['endpoint_error_mm']==pytest.approx(np.linalg.norm(np.array(full['trace'][-1]['joints'][-1])-full['scene']['target'])*1000)
        assert r['success']==(r['reason']=='reached')
        if r['success']:assert r['endpoint_error_mm']<=35 and not r['collision']

def test_all_recorded_frames_are_bound_to_the_same_trace():
    seen=0
    for root,episode_root in [(Path('dist/media/legacy'),Path('dist/data')),(Path('dist/data-v2/recordings'),Path('dist/data-v2'))]:
        for meta_path in root.glob('*/recording.json'):
            m=json.loads(meta_path.read_text());r=json.loads((episode_root/f"{m['run_id']}.json").read_text());seen+=1
            assert m['trace_sha256']==trace_hash(r['trace'])
            assert m['frames'][0]['trace_index']==0 and m['frames'][-1]['trace_index']==len(r['trace'])-1
            for f in m['frames']:
                sample=r['trace'][f['trace_index']]
                assert f['t']==sample['t'] and f['q']==sample['q']
            for page in m['pages']:
                path=meta_path.parent/page['file'];assert hashlib.sha256(path.read_bytes()).hexdigest()==page['sha256']
                image=cv2.imread(str(path));assert image.shape[:2]==(page['rows']*m['height'],page['columns']*m['width'])
            for event in m['contacts']:
                assert r['trace'][event['trace_index']]['collision'] and event['t']==r['trace'][event['trace_index']]['t']
                assert any(f['trace_index']==event['trace_index'] for f in m['frames'])
                assert all(c['distance_m']<=0 for c in event['contacts'])
            assert bool(m['contacts'])==any(f['collision'] for f in r['trace'])
    assert seen==480

def test_occluded_error_is_unmoved_tip_to_ground_truth_distance():
    r=json.loads(Path('dist/data/occluded-1000-improved.json').read_text())
    assert r['detected']['target'] is None and r['perception_error_mm'] is None
    assert r['frames']==1 and r['duration_s']==0 and r['path_length_m']==0
    assert r['endpoint_error_mm']==pytest.approx(np.linalg.norm(fk(QSTART)[-1]-r['scene']['target'])*1000)

def test_legacy_results_remain_byte_identical():
    root=Path('dist/data');checks=json.loads((root/'checksums.json').read_text())
    for name,expected in checks.items():assert hashlib.sha256((root/name).read_bytes()).hexdigest()==expected

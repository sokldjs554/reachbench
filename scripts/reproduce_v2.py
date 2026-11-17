"""Re-execute all held-out pairs without modifying the published benchmark.
Timing is deliberately excluded from equality checks.
"""
import hashlib,json,time
from pathlib import Path
from reachbench.calibration import run_pair,summarize
from reachbench.sim import scene

def main():
    root=Path('dist/data-v2');summary=json.loads((root/'summary.json').read_text())
    checked=[];begin=time.perf_counter()
    for profile,offsets in summary['config']['profiles'].items():
        for bias in offsets:
            for seed in summary['config']['seeds']:
                s=scene(seed);s.calibration_dx=bias/1000
                for row in run_pair(s,profile):
                    old=json.loads((root/f"{row['id']}.json").read_text())
                    for key in ['input_sha256','trace','detected','detected_before','calibration','reference_observations','reason','success','collision','endpoint_error_mm','perception_error_mm']:
                        assert row[key]==old[key],(row['id'],key)
                    checked.append(row['id'])
    assert len(checked)==280 and summarize(summary['episodes'])==summary['metrics']
    legacy=json.loads(Path('dist/media/legacy/manifest.json').read_text())
    for r in legacy['records']:
        assert hashlib.sha256(Path(f"dist/data/{r['id']}.json").read_bytes()).hexdigest()==r['legacy_sha256']
        assert r['matched_fresh_execution']
    report={'passed':True,'held_out_runs_reexecuted':len(checked),'legacy_reexecuted_and_matched':len(legacy['records']),'old_results_overwritten':False,'timing_compared':False,'wall_seconds':time.perf_counter()-begin,'checked_ids':checked}
    p=Path('docs/v2/reproduction.json');p.parent.mkdir(exist_ok=True,parents=True);p.write_text(json.dumps(report,indent=2));print('PASS: 280 held-out runs reproduced; 200 legacy reruns preserved')

if __name__=='__main__':main()

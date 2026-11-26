"""Paired closed-loop runs and no-target camera controls on held-out MuJoCo seeds."""
import argparse
import csv
import json
from pathlib import Path

import mujoco
import numpy as np

from manipulation.controller import run
from manipulation.perception import estimate_target
from manipulation.world import Workcell


def main(out):
    out.mkdir(parents=True, exist_ok=True)
    episodes = []
    observations = []
    controls = []
    for seed in range(320, 332):
        for gain in (1.0, 0.35):
            for adaptive in (False, True):
                r = run(seed, 'shifted', 'feedback', adaptive=adaptive, rgb_gain=gain)
                identity = dict(seed=seed, gain=gain, detector=r['detector'])
                episodes.append(dict(identity, success=r['success'], reason=r['reason'], retries=r['retries'],
                                     contacts=len(r['collisions']), duration_s=round(r['duration_s'], 2),
                                     placement_error_mm=round(r['placement_error_mm'], 4)))
                for index, obs in enumerate(r['sensors']):
                    estimate = obs['estimate']
                    observations.append(dict(identity, index=index, camera=obs['camera'], t=obs['t'],
                                             truth_xy=obs['truth'][:2], estimate_xy=estimate['position'][:2] if estimate else None,
                                             error_mm=obs['error_mm']))
    # Removing the cube leaves the same empty view across seeds. Count each camera once.
    with Workcell(320) as world:
        world.data.qpos[world.adr:world.adr+3] = [0, 0, -10]
        mujoco.mj_forward(world.model, world.data)
        for background in ('ordinary_tray', 'red_tray'):
            if background == 'red_tray':
                world.model.geom('tray_base').rgba[:] = world.model.geom('cube_geom').rgba
            for camera in ('front', 'back'):
                frame = world.observe(camera)
                for gain in (1.0, 0.35):
                    rgb = np.rint(frame['rgb'].astype(float) * gain).astype(np.uint8)
                    for adaptive in (False, True):
                        estimate = estimate_target(**(frame | {'rgb': rgb}), adaptive=adaptive)
                        controls.append(dict(background=background, camera=camera, gain=gain,
                                             detector='adaptive' if adaptive else 'fixed', detected=estimate is not None))
    for name, rows in [('episodes', episodes), ('no-target', controls)]:
        with (out / (name + '.csv')).open('w', newline='') as handle:
            writer = csv.DictWriter(handle, fieldnames=rows[0], lineterminator='\n')
            writer.writeheader()
            writer.writerows(rows)
    (out / 'observations.jsonl').write_text(''.join(json.dumps(row, separators=(',', ':'))+'\n' for row in observations))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    main(parser.parse_args().out)

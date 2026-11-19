"""Render the two archived seed 107 poses from a common external camera.

Run from the repository root:
    MUJOCO_GL=egl python -m scripts.render_retry_replay
Frames are discrete qpos reconstructions. Only mj_forward is used during replay.
"""
import argparse
from bisect import bisect_right
import hashlib
import json
from pathlib import Path
import tarfile

import cv2
from manipulation.world import Workcell
import mujoco
import numpy as np


WIDTH, HEIGHT = 480, 300
COLUMNS, ROWS = 4, 4
SHEET_SIZE = COLUMNS * ROWS


def sample_indices(run):
    trace = run["trace"]
    times = [sample["t"] for sample in trace]
    if any(b <= a for a, b in zip(times, times[1:])):
        raise ValueError("Expected increasing trace times for the seed 107 replay")
    if times[0] != 0 or abs(times[-1] - run["duration_s"]) > 1e-8:
        raise ValueError("Trace does not cover the whole episode")
    # Approximately 8 frames/s. Keep the recorded pose at or immediately
    # before every decision, plus the last recorded pose of each run.
    indices = set(range(0, len(trace), 3))
    indices.add(len(trace) - 1)
    for event in run["events"]:
        indices.add(bisect_right(times, event["t"]) - 1)
    return sorted(indices)


def render_run(run, mode, directory):
    if (run["seed"], run["condition"], run["method"], run["retry_enabled"]) != (
        107, "shifted", "feedback", mode == "on"
    ):
        raise ValueError(f"Unexpected configuration for {mode}")
    camera = mujoco.MjvCamera()
    mujoco.mjv_defaultCamera(camera)
    camera.lookat[:] = [.28, .055, .71]
    camera.distance = 1.35
    camera.elevation = -26
    camera.azimuth = 125
    indices = sample_indices(run)
    sheets = []
    with Workcell(run["seed"], run["condition"]) as cell, mujoco.Renderer(
        cell.model, height=HEIGHT, width=WIDTH
    ) as renderer:
        cell.model.vis.headlight.ambient[:] = .4
        for start in range(0, len(indices), SHEET_SIZE):
            sheet = np.zeros((HEIGHT * ROWS, WIDTH * COLUMNS, 3), dtype=np.uint8)
            for tile, index in enumerate(indices[start:start + SHEET_SIZE]):
                cell.data.qpos[:] = run["trace"][index]["qpos"]
                mujoco.mj_forward(cell.model, cell.data)
                renderer.update_scene(cell.data, camera=camera)
                y, x = divmod(tile, COLUMNS)
                sheet[y*HEIGHT:(y+1)*HEIGHT, x*WIDTH:(x+1)*WIDTH] = cv2.cvtColor(
                    renderer.render(), cv2.COLOR_RGB2BGR
                )
            relative = f"media/{mode}-{start // SHEET_SIZE:02}.jpg"
            if not cv2.imwrite(str(directory / relative), sheet, [cv2.IMWRITE_JPEG_QUALITY, 84]):
                raise IOError(relative)
            sheets.append(relative)
    return {"times": [run["trace"][i]["t"] for i in indices], "sheets": sheets}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, default=Path("docs/v3/retry-study/records.tar.gz"))
    parser.add_argument("--out", type=Path, default=Path("dist/retry"))
    args = parser.parse_args()
    (args.out / "media").mkdir(parents=True, exist_ok=True)
    manifest = {"width": WIDTH, "height": HEIGHT, "columns": COLUMNS, "rows": ROWS}
    with tarfile.open(args.archive) as archive:
        for mode in ("off", "on"):
            path = f"work/retry-study/seed107-{mode}/run.json"
            raw = archive.extractfile(path).read()
            entry = render_run(json.loads(raw), mode, args.out)
            manifest[mode] = dict(entry, source_path=path, source_sha256=hashlib.sha256(raw).hexdigest())
    (args.out / "frames.json").write_text(json.dumps(manifest, indent=2) + "\n")


if __name__ == "__main__":
    main()

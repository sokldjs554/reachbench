"""Reconstruct the seed 107 decision photographs from archived qpos, without stepping.

MUJOCO_GL=egl python -m scripts.render_retry_events --out dist/retry

The decision time and the preceding sampled pose time can differ by 10 ms.
The first two decision views share one fixed camera in world coordinates.
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


WIDTH, HEIGHT = 800, 500
CAMERAS = {
    "gripper": {
        "lookat": [0.503, 0.173, 0.538], "distance": 0.43,
        "azimuth": 166, "elevation": -20,
    },
    "tray": {
        "lookat": [0.48, 0.20, 0.505], "distance": 0.82,
        "azimuth": 139, "elevation": -43,
    },
}


def decision_events(run):
    checks = [event for event in run["events"] if event["phase"] == "verify_grasp"]
    if run["retry_enabled"]:
        ending = run["events"][-1]
        if ([e["grasp_detected"] for e in checks] != [False, True]
                or ending.get("reason") != "placed" or not run["success"]):
            raise ValueError("Expected the archived empty grasp, recovery, and placement.")
        return [("empty", checks[0], "gripper"), ("grasp", checks[1], "gripper"),
                ("placed", ending, "tray")]
    if [e["grasp_detected"] for e in checks] != [False] or run["reason"] != "empty_grasp":
        raise ValueError("Expected the archived empty-grasp termination.")
    return [("empty-off", checks[0], "gripper")]


def render_event_views(archive_path, directory):
    (directory / "media").mkdir(parents=True, exist_ok=True)
    views = {}
    sources = {}
    with tarfile.open(archive_path) as archive, Workcell(107, "shifted") as cell, mujoco.Renderer(
        cell.model, height=HEIGHT, width=WIDTH
    ) as renderer:
        cell.model.vis.headlight.ambient[:] = 0.48
        for mode in ("off", "on"):
            source = f"work/retry-study/seed107-{mode}/run.json"
            raw = archive.extractfile(source).read()
            run = json.loads(raw)
            if (run["seed"], run["condition"], run["method"], run["retry_enabled"]) != (
                107, "shifted", "feedback", mode == "on"
            ):
                raise ValueError(f"Unexpected seed 107 record at {source}")
            sources[mode] = {"path": source, "sha256": hashlib.sha256(raw).hexdigest()}
            times = [sample["t"] for sample in run["trace"]]
            for slug, event, camera_name in decision_events(run):
                index = bisect_right(times, event["t"]) - 1
                if index < 0 or event["t"] - times[index] > 0.041:
                    raise ValueError(f"Missing recorded pose near {event['t']}")
                sample = run["trace"][index]
                cell.data.qpos[:] = sample["qpos"]
                mujoco.mj_forward(cell.model, cell.data)

                camera = mujoco.MjvCamera()
                mujoco.mjv_defaultCamera(camera)
                config = CAMERAS[camera_name]
                camera.lookat[:] = config["lookat"]
                camera.distance = config["distance"]
                camera.azimuth = config["azimuth"]
                camera.elevation = config["elevation"]
                renderer.update_scene(cell.data, camera=camera)
                image = cv2.cvtColor(renderer.render(), cv2.COLOR_RGB2BGR)
                path = f"media/preview-{slug}.jpg"
                if not cv2.imwrite(str(directory / path), image, [cv2.IMWRITE_JPEG_QUALITY, 94]):
                    raise IOError(path)
                views[slug] = {"image": path, "mode": mode, "event_s": event["t"],
                               "pose_s": sample["t"], "trace_index": index, "camera": camera_name}
    manifest = {"width": WIDTH, "height": HEIGHT, "cameras": CAMERAS, "sources": sources,
                "views": views}
    (directory / "event-views.json").write_text(json.dumps(manifest, indent=2) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, default=Path("docs/v3/retry-study/records.tar.gz"))
    parser.add_argument("--out", type=Path, default=Path("dist/retry"))
    args = parser.parse_args()
    render_event_views(args.archive, args.out)

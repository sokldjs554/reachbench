"""Replay the fixed RGB-D estimator on the held-out shifted scenes, without running control."""
import argparse
import csv
import json
import sys
from pathlib import Path

import numpy as np

from manipulation.perception import estimate_target


def measurements(archive):
    # Both retry settings have identical observations here. Count each scene once.
    for seed in range(200, 220):
        folder = archive / "eval-on" / f"seed{seed}"
        run = json.loads((folder / "run.json").read_text())
        for index, sensor in enumerate(run["sensors"]):
            with np.load(folder / sensor["rgbd"]) as frame:
                for gain in (1.0, 0.65, 0.35):
                    rgb = np.rint(frame["rgb"].astype(float) * gain).astype(np.uint8)
                    estimate = estimate_target(
                        rgb, frame["depth"], frame["rotation"], frame["position"], frame["fovy"].item()
                    )
                    error = None
                    if estimate is not None:
                        xy = np.array(estimate["position"][:2])
                        error = np.linalg.norm(xy - sensor["truth"][:2]) * 1000
                    if gain == 1.0:
                        logged = sensor["error_mm"]
                        if (error is None) != (logged is None) or (
                            error is not None and not np.isclose(error, logged, rtol=0, atol=1e-4)
                        ):
                            raise ValueError(f"Original estimate differs from log: {seed}/{index}")
                    yield (seed, index, sensor["camera"], gain, error is not None,
                           "" if error is None else f"{error:.6f}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path, help="Extracted work/retry-study directory")
    args = parser.parse_args()
    writer = csv.writer(sys.stdout, lineterminator="\n")
    writer.writerow(("seed", "observation", "camera", "rgb_gain", "detected", "xy_error_mm"))
    writer.writerows(measurements(args.archive))

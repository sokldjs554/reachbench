"""Verify the shifted/feedback pairs and export the recorded metrics as CSV."""
import argparse
import csv
import json
import math
from pathlib import Path
import sys


def read_run(path, seed, enabled):
    run = json.loads(path.read_text())
    x, y, z = run["final_target"]
    dx, dy = x - .48, y - .24
    placed = (abs(dx) < .065 and abs(dy) < .06 and .37 < z < .42
              and run["final_gripper_width_m"] > .065 and not run["collisions"])
    events = run["events"]
    retries = sum(event["phase"] == "retry" for event in events)
    checks = {
        "configuration": (run["condition"], run["method"], run["seed"]) == ("shifted", "feedback", seed),
        "retry setting": run["retry_enabled"] is enabled,
        "success": run["success"] is placed and ((run["reason"] == "placed") == placed),
        "placement error": math.isclose(run["placement_error_mm"], 1000 * math.hypot(dx, dy), abs_tol=1e-8),
        "retry events": retries == run["retries"] and retries <= int(enabled),
        "observations": run["observations"] == len(run["sensors"]) == sum(e["phase"] == "observe" for e in events),
    }
    for field, ok in checks.items():
        if not ok:
            raise ValueError(f"{path}: inconsistent {field}")
    return run


def rows(root):
    for seed in (107, *range(200, 220)):
        pair = []
        for label in ("off", "on"):
            folder = (f"seed107-{label}" if seed == 107 else f"eval-{label}/seed{seed}")
            pair.append(read_run(root / folder / "run.json", seed, label == "on"))
        if pair[0]["initial_target"] != pair[1]["initial_target"]:
            raise ValueError(f"seed {seed}: initial positions differ")
        for run in pair:
            yield {
                "split": "case" if seed == 107 else "evaluation",
                **{key: run[key] for key in ("seed", "retry_enabled", "success", "reason",
                                             "retries", "observations", "placement_error_mm",
                                             "duration_s", "wall_ms")},
                "occluder_contact": bool(run["collisions"]),
            }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path, help="directory containing seed107-off/on and eval-off/on")
    records = list(rows(parser.parse_args().root))
    writer = csv.DictWriter(sys.stdout, fieldnames=records[0], lineterminator="\n")
    writer.writeheader()
    writer.writerows(records)

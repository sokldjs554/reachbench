"""Export camera observations, preceding encoder samples and subsequent commands."""
import argparse
from bisect import bisect_right
from collections import Counter
import json
import math
from pathlib import Path
import shutil
from tempfile import TemporaryDirectory

from manipulation.check_rgbd import depth_quality

from scripts.summarize_retry_study import read_run


def align_observations(run):
    """Match timestamps within one episode. The JSONL schema is an allowlist."""
    trace = run["trace"]
    times = [frame["t"] for frame in trace]
    if not times or not all(math.isfinite(t) for t in times) or times != sorted(times):
        raise ValueError(f"{run['id']}: missing or unordered trace")
    for frame in trace:
        if len(frame["qpos"]) != 16 or len(frame["ctrl"]) != 8:
            raise ValueError(f"{run['id']}: unexpected robot state or command dimension")
    for index, obs in enumerate(run["sensors"]):
        t = obs["t"]
        if not math.isfinite(t) or t < times[0] or t > times[-1]:
            raise ValueError(f"{run['id']} observation {index}: outside trace")
        right = bisect_right(times, t)
        state = trace[right - 1]
        following = trace[right] if right < len(trace) else None
        estimate = obs["estimate"]
        yield {
            "t": t,
            "camera": obs["camera"],
            "estimate_xy_m": estimate["position"][:2] if estimate else None,
            "state_t": state["t"],
            "state_lag_ms": round((t - state["t"]) * 1000),
            "arm_rad": state["qpos"][:7],
            "fingers_m": state["qpos"][7:9],
            "gap_mm": round(sum(state["qpos"][7:9]) * 1000, 6),
            "next_t": following["t"] if following else None,
            "next_phase": following["phase"] if following else None,
            "next_ctrl": following["ctrl"] if following else None,
        }


def generate(root, out):
    (out / "sensors").mkdir()
    samples = []
    cases = {}
    lag_counts = Counter()
    evaluation = {"n_pairs": 0, "off_successes": 0, "on_successes": 0, "on_retry_runs": 0}
    run_count = 0
    for seed in (107, *range(200, 220)):
        case = seed == 107
        initial_positions = []
        for mode in ("off", "on"):
            relative = Path(f"seed107-{mode}" if case else f"eval-{mode}/seed{seed}")
            folder = root / relative
            run = read_run(folder / "run.json", seed, mode == "on")
            run_count += 1
            initial_positions.append(run["initial_target"])
            observations = []
            for i, (obs, aligned) in enumerate(zip(run["sensors"], align_observations(run), strict=True)):
                rgbd, jpg = obs["rgbd"], obs["image"]
                if (rgbd, jpg) != (f"camera-{i}.npz", f"camera-{i}.jpg") or not (folder / jpg).is_file():
                    raise ValueError(f"{folder}: missing or invalid camera file for observation {i}")
                quality = depth_quality(folder / rgbd)
                lag_counts[aligned["state_lag_ms"]] += 1
                group = f"shifted-{seed}"
                run_id = f"{group}-feedback-{mode}"
                samples.append({
                    "sample_id": f"{run_id}-obs{i}", "run_id": run_id, "group": group,
                    "split": "case" if case else "evaluation", "seed": seed, "retry_enabled": mode == "on",
                    "source": {"record": str(relative / "run.json"), "observation_index": i,
                               "rgbd": str(relative / rgbd), "jpeg": str(relative / jpg)},
                    "observation": {k: aligned[k] for k in ("t", "camera", "estimate_xy_m")},
                    "state": {k: aligned[k] for k in ("state_t", "state_lag_ms", "arm_rad", "fingers_m", "gap_mm")},
                    "next_recorded_command": (
                        {k: aligned[k] for k in ("next_t", "next_phase", "next_ctrl")}
                        if aligned["next_t"] is not None else None
                    ),
                    "quality": quality,
                })
                if case:
                    image = f"sensors/{mode}-{i}.jpg"
                    shutil.copyfile(folder / jpg, out / image)
                    observations.append({**aligned, "image": image})
            if case:
                events = []
                for event in run["events"]:
                    if event["phase"] == "verify_grasp":
                        prior = next(frame for frame in reversed(run["trace"]) if frame["t"] < event["t"])
                        event = {**event, "prior_grip_command": prior["ctrl"][7], "command_t": prior["t"]}
                    events.append(event)
                cases[mode] = {
                    **{key: run[key] for key in ("success", "reason", "placement_error_mm", "retries")},
                    "duration_s": round(run["duration_s"], 3), "observations": observations, "events": events,
                }
            else:
                evaluation[f"{mode}_successes"] += int(run["success"])
                if mode == "on":
                    evaluation["on_retry_runs"] += int(run["retries"] > 0)
        if initial_positions[0] != initial_positions[1]:
            raise ValueError(f"seed {seed}: different initial positions")
        if not case:
            evaluation["n_pairs"] += 1
    study = {
        "version": 1, "runs": cases, "evaluation": evaluation,
        "alignment": {"runs": run_count, "observations": len(samples),
                      "lag_histogram_ms": dict(sorted(lag_counts.items()))},
    }
    with (out / "observations.jsonl").open("w", encoding="utf-8") as stream:
        for sample in samples:
            stream.write(json.dumps(sample, allow_nan=False, separators=(",", ":")) + "\n")
    (out / "study.json").write_text(json.dumps(study, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def export(root, output):
    output.mkdir(exist_ok=True, parents=True)
    # Validate every episode and sensor before publishing derived artifacts.
    with TemporaryDirectory(dir=output) as staging:
        stage = Path(staging)
        generate(root, stage)
        for src in sorted(stage.rglob("*")):
            if src.is_file():
                dest = output / src.relative_to(stage)
                dest.parent.mkdir(exist_ok=True, parents=True)
                src.replace(dest)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path, help="extracted work/retry-study directory")
    parser.add_argument("output", type=Path, help="directory for JSONL, study.json and seed 107 JPEGs")
    args = parser.parse_args()
    export(args.root, args.output)

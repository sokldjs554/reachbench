import json
from pathlib import Path
import tarfile

import pytest

from scripts.export_retry_alignment import align_observations, export


def test_state_comes_from_past_and_command_from_strict_future():
    def frame(t, value):
        return {
            "t": t, "qpos": [value] * 7 + [.02, .02] + [9001] * 7,
            "ctrl": [value] * 7 + [255], "phase": "approach",
        }

    def sensor(t, camera):
        return {"t": t, "camera": camera, "truth": [9001] * 3, "estimate": None}

    run = {
        "id": "test", "trace": [frame(0, 1), frame(.02, 2), frame(.06, 3)],
        "sensors": [sensor(.019, "front"), sensor(.02, "front"), sensor(.02, "back"), sensor(.06, "back")],
    }
    a, b, c, d = align_observations(run)
    assert (a["arm_rad"], a["state_lag_ms"], a["next_ctrl"]) == ([1] * 7, 19, [2] * 7 + [255])
    assert (b["arm_rad"], b["state_lag_ms"], b["next_ctrl"]) == ([2] * 7, 0, [3] * 7 + [255])
    assert c["camera"] != b["camera"] and c["state_t"] == b["state_t"]
    assert d["next_t"] is d["next_ctrl"] is d["next_phase"] is None
    assert not any("9001" in json.dumps(row) for row in (a, b, c, d))

    run["sensors"] = [sensor(-.01, "front")]
    with pytest.raises(ValueError, match="outside trace"):
        list(align_observations(run))


def test_archive_rebuild_matches_every_published_sample_and_sensor(tmp_path):
    # Extract only the referenced study data, leaving the archived Python files unopened.
    root = Path(__file__).resolve().parents[1]
    with tarfile.open(root / "docs/v3/retry-study/records.tar.gz") as tar:
        tar.extractall(tmp_path, members=(m for m in tar if m.name.startswith("work/retry-study/")),
                       filter="data")
    source = tmp_path / "work/retry-study"
    rebuilt = tmp_path / "build"
    export(source, rebuilt)
    for p in rebuilt.rglob("*"):
        if p.is_file():
            assert p.read_bytes() == (root / "dist/retry" / p.relative_to(rebuilt)).read_bytes()
    samples = [json.loads(line) for line in (rebuilt / "observations.jsonl").read_text().splitlines()]
    assert len(samples) == len({r["sample_id"] for r in samples}) == 86
    assert len({r["group"] for r in samples}) == 21
    assert len({r["run_id"] for r in samples}) == 42
    assert {r["seed"] for r in samples if r["split"] == "evaluation"} == set(range(200, 220))
    report = json.loads((rebuilt / "study.json").read_text())
    assert report["alignment"]["lag_histogram_ms"] == {"0": 42, "20": 43, "30": 1}
    assert report["evaluation"] == {"n_pairs": 20, "off_successes": 20,
                                    "on_successes": 20, "on_retry_runs": 0}

# ReachBench Manipulation Implementation Plan

> For agentic workers: execute inline using superpowers:executing-plans; one fresh whole-change reviewer at end.

**Goal:** Make visible, physical 3D manipulation and recovery the primary ReachBench demo.
**Architecture:** Python MuJoCo sensor/controller/evaluator, common MJCF assets, browser WASM physics and Three.js viewer, static immutable evaluation exports; old experiments preserved.
**Tech Stack:** Python, MuJoCo, NumPy/OpenCV, JavaScript, Three.js, MuJoCo WASM.
**Spec:** docs/superpowers/specs/2026-11-17-manipulation-design.md

## Global constraints
- No runtime arm teleportation or cube attachment; truth used only for evaluation and scenario setup/disturbance.
- Dev seeds 10–14; held-out 100–119, same scenes for methods.
- Public live results never substituted for benchmark results.
- Preserve existing evidence; report training and hardware scope honestly.

## Review focus
- Reset while running must clear physics/controller observations.
- Hidden/unreachable target must stop after bounded observation/retry.
- Estimated target must not silently fall back to truth.
- A failed/partial grasp must not count as placement success.
- Camera/model loading errors must remain visible, with functional recorded evidence fallback.

## Task 1: Physics + sensing
Files: manipulation/world.py, perception.py, assets/; tests/test_manipulation.py.
Interface World.observe(camera)->RGB/depth/metadata; perception.estimate(observation)->pose|None; World.step(control) advances physics.
- [x] Write failing tests for empty RGB, projection accuracy, valid model, contact grasp/release.
- [x] Implement and run CPU physical task using calibrated sensor geometry; inspect real rendered output.

## Task 2: Recovery + experiment
Files: manipulation/controller.py, evaluate.py, tests/test_manipulation.py; dist/bench/.
Interface run(seed,condition,method,record=False)->episode; summarize(rows)->aggregate.
- [x] Test bounded recovery, seed equality, final released success and aggregation.
- [x] Tune only dev seeds; freeze config and run held-out pairs; preserve all outcomes and provenance.
- [x] Collect synchronized sensor/actions dataset; optional small CPU learned correction only if supported by measured comparison.

## Task 3: Public workbench
Files: dist/index.html, studio.js, studio.css, vendor/, assets/; tests/test_studio.*.
- [x] Test state transitions and integration contracts.
- [x] Implement live WASM physics, scene/camera interaction, accessible controls and benchmark drill-down; legacy archive.
- [x] Verify actual execution and both viewport sizes; diagnose environment limitations without hiding them.

## Task 4: Review + release
- [x] Run old and new tests, rerun sample episodes and check data aggregation and asset hashes.
- [x] Fresh reviewer checks truth boundaries, grasp physics, live-vs-recorded claims, failure/reset behavior.
- [x] Update documentation/reproduction/licenses, publish same code/data to GitHub and existing Sites URL, verify release.

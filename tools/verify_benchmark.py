#!/usr/bin/env python3
import json
import os
import re
import subprocess
import sys


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
BENCH_RESULTS = os.path.join(ROOT, "bench_results.jsonl")
BENCH_SUMMARY = os.path.join(ROOT, "bench_summary.md")

ALLOWED_CHANNELS = {"writing", "breath", "movement", "social", "environment"}
HEX8_RE = re.compile(r"^[0-9a-f]{8}$")


def _fail(msg: str) -> None:
    raise SystemExit(f"verify_benchmark: {msg}")


def _run_benchmark() -> None:
    for path in (BENCH_RESULTS, BENCH_SUMMARY):
        if os.path.exists(path):
            os.remove(path)
    cmd = [sys.executable, "echolattice.py", "--benchmark"]
    result = subprocess.run(cmd, cwd=ROOT)
    if result.returncode != 0:
        _fail(f"benchmark failed with exit code {result.returncode}")
    if not os.path.exists(BENCH_RESULTS):
        _fail("bench_results.jsonl was not created")


def _load_results() -> list:
    with open(BENCH_RESULTS, "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f if line.strip()]
    if len(lines) != 21:
        _fail(f"expected 21 JSONL lines, found {len(lines)}")
    results = []
    for idx, line in enumerate(lines, start=1):
        try:
            obj = json.loads(line)
        except json.JSONDecodeError as e:
            _fail(f"line {idx} is not valid JSON: {e}")
        results.append(obj)
    return results


def _validate_result(obj: dict, idx: int) -> None:
    for key in ["seed", "category", "config", "structure", "loopiness", "ground", "policy"]:
        if key not in obj:
            _fail(f"line {idx} missing key: {key}")

    if "human_closure_rating" not in obj or obj["human_closure_rating"] is not None:
        _fail(f"line {idx} human_closure_rating must be null")

    config = obj["config"]
    for key in ["novelty", "depth", "branching", "rng_seed"]:
        if key not in config:
            _fail(f"line {idx} config missing key: {key}")
    if config["depth"] not in (4, 6):
        _fail(f"line {idx} depth expected 4 or 6, got {config['depth']}")
    if config["rng_seed"] != 42:
        _fail(f"line {idx} rng_seed expected 42, got {config['rng_seed']}")

    structure = obj["structure"]
    dedup_saved = structure.get("dedup_saved")
    if dedup_saved is None or not (0.0 <= float(dedup_saved) <= 1.0):
        _fail(f"line {idx} dedup_saved out of range: {dedup_saved}")

    loopiness = obj["loopiness"]
    loop_hits = loopiness.get("loop_pattern_hits", {})
    for key in ["echo_of", "shadow_of", "symbols", "total"]:
        if key not in loop_hits:
            _fail(f"line {idx} loop_pattern_hits missing key: {key}")

    ground = obj["ground"]
    ground_hash = ground.get("ground_hash")
    if ground_hash is not None and not HEX8_RE.match(ground_hash):
        _fail(f"line {idx} ground_hash must be 8 hex chars, got: {ground_hash}")

    channel = ground.get("ground_channel")
    if channel is not None and channel not in ALLOWED_CHANNELS:
        _fail(f"line {idx} ground_channel invalid: {channel}")

    if "ground_path" not in ground:
        _fail(f"line {idx} ground_path missing")

    policy = obj["policy"]
    for key in ["version", "mode", "public_safe", "redactions", "notes", "decision"]:
        if key not in policy:
            _fail(f"line {idx} policy missing key: {key}")
    if policy["public_safe"] is not True:
        _fail(f"line {idx} policy public_safe must be true")
    decision = policy["decision"]
    for key in ["action", "severity", "reason_codes", "inputs"]:
        if key not in decision:
            _fail(f"line {idx} policy decision missing key: {key}")


def _index_for_determinism(results: list) -> dict:
    mapping = {}
    for obj in results:
        key = (obj["seed"], obj["config"]["novelty"], obj["config"]["depth"])
        ground = obj["ground"]
        value = (ground.get("ground_hash"), ground.get("ground_path"))
        mapping[key] = value
    return mapping


def main() -> int:
    _run_benchmark()
    results_1 = _load_results()
    for idx, obj in enumerate(results_1, start=1):
        _validate_result(obj, idx)
    index_1 = _index_for_determinism(results_1)

    _run_benchmark()
    results_2 = _load_results()
    for idx, obj in enumerate(results_2, start=1):
        _validate_result(obj, idx)
    index_2 = _index_for_determinism(results_2)

    if index_1 != index_2:
        _fail("determinism check failed: ground_hash or ground_path changed")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

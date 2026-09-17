#!/usr/bin/env python3
"""Inspect the actual Docker job for the configured version, then print its stage and progress.

Runs on the Cathedral host with the system Python: standard library only.
"""

import json
from pathlib import Path
import re
import subprocess
import sys

config_path = Path(sys.argv[1] if len(sys.argv) > 1 else "configs/train_qwen8b_qlora.yaml")
match = re.search(r"^version:\s*(v\d{2,})\s*$", config_path.read_text(), re.M)
if not match:
    raise SystemExit(f"No version key in {config_path}")
version = match.group(1)
container = f"debrief-experiment-{version}"
result = subprocess.run(
    ["docker", "inspect", container, "--format", "{{json .State}}"],
    text=True,
    capture_output=True,
)
if result.returncode:
    print(f"No {container} container found.")
else:
    state = json.loads(result.stdout)
    print(f"Container: {state['Status']} (running={state['Running']}, exit={state['ExitCode']})")
path = Path(f"eval_runs/{version}_status.json")
if path.exists():
    experiment = json.loads(path.read_text())
    stage = experiment.get("stage", "train")
    print(f"Stage: {stage}; recorded status: {experiment['status']}")
    print("Completed:", ", ".join(experiment.get("completed_stages", [])) or "none yet")
    log = Path("logs") / version / f"{stage}.stderr.log"
    if log.exists():
        with log.open("rb") as stream:
            stream.seek(max(0, log.stat().st_size - 4096))
            tail = stream.read().decode("utf-8", errors="replace")
        lines = [
            line.strip()
            for line in re.sub(r"\x1b\[[0-9;]*[A-Za-z]", "", tail).replace("\r", "\n").splitlines()
            if line.strip()
        ]
        if lines:
            print("Latest:", lines[-1])
    metrics = Path(f"eval_runs/{version}_metrics.json")
    if metrics.exists():
        print(json.loads(metrics.read_text())["gates"]["decision"])

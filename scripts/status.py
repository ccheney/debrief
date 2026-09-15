#!/usr/bin/env python3
"""Inspect the actual Docker job, then print its stage and latest progress."""

import json
from pathlib import Path
import re
import subprocess

result = subprocess.run(
    ["docker", "inspect", "debrief-experiment", "--format", "{{json .State}}"],
    text=True,
    capture_output=True,
)
if result.returncode:
    print("No debrief-experiment container found.")
else:
    state = json.loads(result.stdout)
    print(f"Container: {state['Status']} (running={state['Running']}, exit={state['ExitCode']})")
path = Path("eval_runs/experiment_status.json")
if path.exists():
    experiment = json.loads(path.read_text())
    stage = experiment.get("stage", "train")
    print(f"Stage: {stage}; recorded status: {experiment['status']}")
    print("Completed:", ", ".join(experiment.get("completed_stages", [])) or "none yet")
    log = Path("logs") / f"{stage}.stderr.log"
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
    metrics = Path("eval_runs/v01_metrics.json")
    if metrics.exists():
        print(json.loads(metrics.read_text())["gates"]["decision"])

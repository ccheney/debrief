#!/usr/bin/env bash
# Runs on Cathedral under nohup. Train mode: Unsloth Studio holds a CUDA context
# that trips the trainer's exclusive-GPU preflight, so stop it for the run and
# bring it back whatever the outcome. The experiment container is kept (no --rm)
# so scripts/status.py can inspect its exit state.
set -u
CONFIG="${1:?config path}"
VERSION="${2:?version}"
cd "$(dirname "$0")/.."
NAME="debrief-experiment-$VERSION"
docker stop unsloth-studio >/dev/null 2>&1 || true
docker run --gpus all --shm-size=4g --user "$(id -u):$(id -g)" -e HOME=/cache -e PYTHONPATH=/workspace \
  -v "$PWD:/workspace" -v "$PWD/.cache:/cache" -w /workspace --name "$NAME" briefcard:0.1 \
  python -m src.run_experiment --config "$CONFIG"
status=$?
docker start unsloth-studio >/dev/null 2>&1 || true
echo "$(date -Is) $NAME exited with $status; Studio restarted"
exit "$status"

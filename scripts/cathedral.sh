#!/usr/bin/env bash
set -euo pipefail
SERVER="${BRIEFCARD_SERVER:-ccheney@cathedral.lan}"
REMOTE="${BRIEFCARD_REMOTE:-/home/ccheney/briefcard}"
CONFIG="${DEBRIEF_CONFIG:-configs/train_qwen8b_qlora.yaml}"
VERSION="$(sed -n 's/^version:[[:space:]]*\(v[0-9][0-9]*\).*/\1/p' "$CONFIG" | head -1)"
DOCKER_RUN="docker run --gpus all --shm-size=4g --user \$(id -u):\$(id -g) -e HOME=/cache -e PYTHONPATH=/workspace \
      -v '$REMOTE:/workspace' -v '$REMOTE/.cache:/cache' -w /workspace"
case "${1:-help}" in
  sync)
    # Code and processed data only. Raw data, weights, caches, logs and results stay put.
    ssh "$SERVER" "mkdir -p '$REMOTE'"
    rsync -az --exclude=.venv --exclude=data/raw --exclude=adapters --exclude=checkpoints \
      --exclude=.cache --exclude=logs --exclude=eval_runs --exclude=__pycache__ --exclude=.git \
      ./ "$SERVER:$REMOTE/"
    ;;
  build)
    ssh "$SERVER" "cd '$REMOTE' && docker build -t briefcard:0.1 ."
    ;;
  status)
    ssh "$SERVER" "nvidia-smi; docker ps -a --filter name=debrief --format '{{.Names}} {{.Status}}'; cd '$REMOTE' && python3 scripts/status.py '$CONFIG'"
    ;;
  run)
    shift
    # quote every argument across the SSH shell boundary
    printf -v command '%q ' "$@"
    ssh "$SERVER" "cd '$REMOTE' && $DOCKER_RUN --rm briefcard:0.1 $command"
    ;;
  launch)
    # Detached full experiment for the configured version: train, evaluate, demos.
    [ -n "$VERSION" ] || { echo "No version in $CONFIG" >&2; exit 1; }
    ssh "$SERVER" "cd '$REMOTE' && $DOCKER_RUN -d --name debrief-experiment-$VERSION briefcard:0.1 python -m src.run_experiment --config '$CONFIG'"
    ;;
  logs)
    ssh "$SERVER" "docker logs --tail \"\${2:-40}\" debrief-experiment-$VERSION 2>&1; tail -c 600 '$REMOTE/logs/$VERSION/train.stderr.log' 2>/dev/null | tr '\r' '\n' | tail -3"
    ;;
  fetch)
    mkdir -p adapters eval_runs logs
    rsync -az "$SERVER:$REMOTE/adapters/" adapters/
    rsync -az "$SERVER:$REMOTE/eval_runs/" eval_runs/
    rsync -az "$SERVER:$REMOTE/logs/" logs/
    ;;
  *)
    echo 'Usage: scripts/cathedral.sh {sync|build|status|run COMMAND...|launch|logs [N]|fetch}'
    ;;
esac

#!/usr/bin/env bash
set -euo pipefail
SERVER="${BRIEFCARD_SERVER:-ccheney@cathedral.lan}"
REMOTE="${BRIEFCARD_REMOTE:-/home/ccheney/briefcard}"
case "${1:-help}" in
  sync)
    ssh "$SERVER" "mkdir -p '$REMOTE'"
    rsync -az --exclude=.venv --exclude=data/raw --exclude=adapters --exclude=checkpoints \
      --exclude=.cache --exclude=logs --exclude=eval_runs --exclude=__pycache__ \
      ./ "$SERVER:$REMOTE/"
    ;;
  build)
    ssh "$SERVER" "cd '$REMOTE' && docker build -t briefcard:0.1 ."
    ;;
  status)
    ssh "$SERVER" "nvidia-smi; docker ps -a --filter name=debrief --format '{{.Names}} {{.Status}}'; cd '$REMOTE' && python3 scripts/status.py"
    ;;
  run)
    shift
    # quote every argument across the SSH shell boundary
    printf -v command '%q ' "$@"
    ssh "$SERVER" "cd '$REMOTE' && docker run --rm --gpus all --shm-size=4g \
      --user \$(id -u):\$(id -g) -e HOME=/cache -e PYTHONPATH=/workspace \
      -v '$REMOTE:/workspace' -v '$REMOTE/.cache:/cache' -w /workspace briefcard:0.1 $command"
    ;;
  fetch)
    mkdir -p adapters eval_runs
    rsync -az "$SERVER:$REMOTE/adapters/" adapters/
    rsync -az "$SERVER:$REMOTE/eval_runs/" eval_runs/
    ;;
  *)
    echo 'Usage: scripts/cathedral.sh {sync|build|status|run COMMAND...|fetch}'
    ;;
esac

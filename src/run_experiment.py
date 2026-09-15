"""Run the frozen full experiment and record durable stage status and logs."""

import argparse
from pathlib import Path
import subprocess
import sys
import time
from src.common import DEFAULT_CONFIG, read_config, write_json


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default=DEFAULT_CONFIG)
    args = parser.parse_args()
    config = read_config(args.config)
    state_path = Path("eval_runs/experiment_status.json")
    Path("logs").mkdir(exist_ok=True)
    stages = [
        ("train", ["-m", "src.train_unsloth", "--config", args.config]),
        (
            "evaluation",
            ["-m", "src.eval_briefs", "--config", args.config, "--adapter", config["adapter_dir"]],
        ),
    ]
    for name in ("go_around", "docker_oom", "ambiguous"):
        stages.append(
            (
                f"demo_{name}",
                [
                    "-m",
                    "src.infer",
                    "--config",
                    args.config,
                    "--adapter",
                    config["adapter_dir"],
                    "--file",
                    f"fixtures/{name}.txt",
                    "--json",
                ],
            )
        )
    state = {
        "status": "running",
        "started_at": time.time(),
        "completed_stages": [],
        "config": config,
    }
    for stage, command in stages:
        state.update(stage=stage, updated_at=time.time())
        write_json(state_path, state)
        output = (
            Path("eval_runs") / f"{stage}.json"
            if stage.startswith("demo_")
            else Path("logs") / f"{stage}.log"
        )
        with output.open("w") as stdout, Path("logs", f"{stage}.stderr.log").open("w") as stderr:
            result = subprocess.run([sys.executable, *command], stdout=stdout, stderr=stderr)
        if result.returncode:
            state.update(
                status="failed",
                failed_stage=stage,
                returncode=result.returncode,
                updated_at=time.time(),
            )
            write_json(state_path, state)
            raise SystemExit(result.returncode)
        state["completed_stages"].append(stage)
    state.update(
        status="complete",
        updated_at=time.time(),
        wall_seconds=time.time() - state["started_at"],
        acceptance="Read eval_runs/v01_metrics.json and complete the rubric; execution success is not model acceptance.",
    )
    write_json(state_path, state)


if __name__ == "__main__":
    main()

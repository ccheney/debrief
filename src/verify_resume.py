"""Exercise save, pause, restore and one additional QLoRA optimizer step."""

import argparse
import json
import re
from pathlib import Path
import subprocess
import sys
from src.common import DEFAULT_CONFIG, sha256, write_json


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default=DEFAULT_CONFIG)
    parser.add_argument("--run-id", default="debrief-qwen3-8b-resume-check")
    args = parser.parse_args()
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", args.run_id):
        parser.error("--run-id must contain lowercase letters, numbers, and hyphens")
    checkpoint_dir = Path("checkpoints") / args.run_id
    adapter_dir = Path("adapters") / args.run_id
    if checkpoint_dir.exists() or adapter_dir.exists():
        parser.error("Verification outputs already exist; select a new --run-id")
    log_dir = Path("logs") / args.run_id
    log_dir.mkdir(parents=True, exist_ok=True)
    common = [
        sys.executable,
        "-m",
        "src.train_unsloth",
        "--config",
        args.config,
        "--dry-run",
        "--max-steps",
        "2",
        "--run-id",
        args.run_id,
    ]
    meta_path = Path("eval_runs") / f"{args.run_id}_meta.json"
    for phase, extra in [
        ("pause", ["--stop-after-steps", "1"]),
        ("resume", ["--resume", "latest"]),
    ]:
        with (log_dir / f"{phase}.log").open("w") as log:
            subprocess.run(common + extra, stdout=log, stderr=subprocess.STDOUT, check=True)
        metadata = json.loads(meta_path.read_text())
        write_json(Path("eval_runs") / f"{args.run_id}_{phase}_meta.json", metadata)
        if phase == "pause":
            assert metadata["status"] == "paused" and metadata["global_step"] == 1
            assert metadata["optimizer_steps_this_attempt"] == 1
            assert not adapter_dir.exists(), "A paused run must not publish a completed adapter"
        else:
            assert metadata["status"] == "complete" and metadata["global_step"] == 2
            assert metadata["optimizer_steps_this_attempt"] == 1, "Resume repeated completed work"
            assert Path(metadata["resume_checkpoint"]).name == "checkpoint-1"
    # Load states on CPU only after both GPU subprocesses finish.
    import torch
    from safetensors.torch import load_file

    before = checkpoint_dir / "checkpoint-1"
    after = checkpoint_dir / "checkpoint-2"
    optimizer_steps = []
    for path in (before, after):
        optimizer = torch.load(path / "optimizer.pt", map_location="cpu", weights_only=True)
        steps = sorted(
            {int(state["step"]) for state in optimizer["state"].values() if "step" in state}
        )
        assert steps, "No optimizer step state found"
        optimizer_steps.append(steps)
    assert optimizer_steps == [[1], [2]], f"Optimizer state was not restored: {optimizer_steps}"
    initial = load_file(str(before / "adapter_model.safetensors"))
    resumed = load_file(str(after / "adapter_model.safetensors"))
    assert initial.keys() == resumed.keys()
    changed = sum(not torch.equal(initial[key], resumed[key]) for key in initial)
    assert changed > 0, "No adapter tensors changed after the resumed optimizer step"
    result = {
        "status": "passed",
        "run_id": args.run_id,
        "optimizer_steps": optimizer_steps,
        "changed_adapter_tensors": changed,
        "first_attempt_steps": 1,
        "resumed_attempt_steps": 1,
        "final_global_step": 2,
        "train_sha256": metadata["train_sha256"],
        "checkpoint_before_sha256": sha256(before / "adapter_model.safetensors"),
        "checkpoint_after_sha256": sha256(after / "adapter_model.safetensors"),
    }
    write_json(Path("eval_runs") / f"{args.run_id}_verification.json", result)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()

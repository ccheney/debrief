"""Select and validate a completed checkpoint before allocating GPU memory."""

import json
from pathlib import Path
import re


REQUIRED_STATE = (
    "debrief_run.json",
    "trainer_state.json",
    "optimizer.pt",
    "scheduler.pt",
    "rng_state.pth",
    "adapter_config.json",
    "adapter_model.safetensors",
)


def complete_checkpoint(path):
    return all(
        (path / name).is_file() and (path / name).stat().st_size > 0 for name in REQUIRED_STATE
    )


def resolve_resume(output_dir, requested, config, train_sha256, expected_train_rows=None):
    if requested is None:
        existing = list(Path(output_dir).glob("checkpoint-*"))
        if existing:
            raise ValueError(
                f"Checkpoint output already exists in {output_dir}; use --resume or a new --run-id"
            )
        return None
    if requested == "latest":
        candidates = [
            path
            for path in Path(output_dir).glob("checkpoint-*")
            if path.is_dir()
            and re.fullmatch(r"checkpoint-\d+", path.name)
            and complete_checkpoint(path)
        ]
        if not candidates:
            raise ValueError(f"No completed checkpoint found in {output_dir}")
        checkpoint = max(candidates, key=lambda path: int(path.name.rsplit("-", 1)[1]))
    else:
        checkpoint = Path(requested)
    marker = checkpoint / "debrief_run.json"
    if not complete_checkpoint(checkpoint):
        raise ValueError(
            "Checkpoint is incomplete; model, optimizer, scheduler, RNG and provenance are required"
        )
    previous = json.loads(marker.read_text())
    if previous["train_sha256"] != train_sha256 or previous["config"] != config:
        raise ValueError("Resume dataset or training config differs from checkpoint")
    if expected_train_rows is not None and previous.get("train_rows") != expected_train_rows:
        raise ValueError("Resume training subset differs from checkpoint")
    return str(checkpoint)

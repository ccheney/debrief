"""Small I/O helpers; importing the CPU pipeline never imports CUDA libraries."""

import hashlib
import json
from pathlib import Path
import re

DEFAULT_CONFIG = "configs/train_qwen8b_qlora.yaml"


def read_jsonl(path):
    with Path(path).open() as stream:
        return [json.loads(line) for line in stream if line.strip()]


def write_jsonl(path, rows):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as stream:
        for row in rows:
            stream.write(json.dumps(row, ensure_ascii=False) + "\n")


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n")
    temporary.replace(path)


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_config(path=DEFAULT_CONFIG):
    import yaml

    return yaml.safe_load(Path(path).read_text())


def version_of(config):
    """Experiment version used to namespace every artifact of one run."""
    version = str(config.get("version") or Path(config["output_dir"]).name.rsplit("-", 1)[-1])
    if not re.fullmatch(r"v\d{2,}", version):
        raise ValueError(f"Configuration version must look like v02, got {version!r}")
    return version


def adapter_config(adapter, config_path=None):
    """Use saved training provenance; never guess a base from an adapter's name."""
    saved_path = Path(adapter) / "debrief_config.json"
    if not saved_path.exists():
        if config_path:
            return read_config(config_path)
        raise ValueError(
            f"No saved Debrief configuration in {adapter}; provide --config explicitly"
        )
    saved = json.loads(saved_path.read_text())
    if config_path:
        requested = read_config(config_path)
        for key in ("model_id", "model_revision", "narrative_tokens", "max_seq_length"):
            if requested[key] != saved[key]:
                raise ValueError(f"Configuration differs from saved adapter: {key}")
        return requested
    return saved

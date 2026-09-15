import json
import pytest
from src.checkpoints import REQUIRED_STATE, resolve_resume


def checkpoint(root, step, config, digest="dataset"):
    path = root / f"checkpoint-{step}"
    path.mkdir()
    for name in REQUIRED_STATE:
        (path / name).write_text("state")
    (path / "debrief_run.json").write_text(
        json.dumps({"config": config, "train_sha256": digest, "train_rows": 100})
    )
    return path


def test_resume_skips_interrupted_newer_save(tmp_path):
    config = {"model_id": "pinned-base", "seed": 42}
    completed = checkpoint(tmp_path, 500, config)
    (tmp_path / "checkpoint-1000").mkdir()
    assert resolve_resume(tmp_path, "latest", config, "dataset") == str(completed)


def test_resume_refuses_changed_data_or_model(tmp_path):
    config = {"model_id": "pinned-base"}
    checkpoint(tmp_path, 500, config)
    with pytest.raises(ValueError, match="differs"):
        resolve_resume(tmp_path, "latest", config, "changed-data")
    with pytest.raises(ValueError, match="differs"):
        resolve_resume(tmp_path, "latest", {"model_id": "another-base"}, "dataset")


def test_fresh_run_cannot_overwrite_interrupted_checkpoints(tmp_path):
    (tmp_path / "checkpoint-20").mkdir()
    with pytest.raises(ValueError, match="already exists"):
        resolve_resume(tmp_path, None, {}, "dataset")
    with pytest.raises(ValueError, match="No completed"):
        resolve_resume(tmp_path, "latest", {}, "dataset")


def test_complete_marker_cannot_hide_missing_optimizer(tmp_path):
    older = checkpoint(tmp_path, 500, {})
    newer = checkpoint(tmp_path, 1000, {})
    (newer / "optimizer.pt").unlink()
    assert resolve_resume(tmp_path, "latest", {}, "dataset") == str(older)
    with pytest.raises(ValueError, match="incomplete"):
        resolve_resume(tmp_path, str(newer), {}, "dataset")


def test_dry_checkpoint_cannot_resume_as_full_training(tmp_path):
    checkpoint(tmp_path, 50, {})
    with pytest.raises(ValueError, match="subset differs"):
        resolve_resume(tmp_path, "latest", {}, "dataset", expected_train_rows=4000)
    assert resolve_resume(tmp_path, "latest", {}, "dataset", expected_train_rows=100)

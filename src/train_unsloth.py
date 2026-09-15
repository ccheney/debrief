"""Repeatable QLoRA with GPU checks, checkpoint resume and run provenance."""

import argparse
import hashlib
import json
import math
from pathlib import Path
import subprocess
import time

from src.common import DEFAULT_CONFIG, read_config, read_jsonl, sha256, write_json
from src.schema import SYSTEM_PROMPT, parse_brief
from src.prompt import messages_for


def gpu_preflight():
    result = subprocess.run(
        ["nvidia-smi", "--query-compute-apps=pid,used_memory", "--format=csv,noheader,nounits"],
        text=True,
        capture_output=True,
        check=True,
    )
    busy = [
        line
        for line in result.stdout.splitlines()
        if line.strip() and line.split(",")[-1].strip().isdigit() and int(line.split(",")[-1]) > 100
    ]
    if busy:
        raise RuntimeError(
            "GPU busy; stop or finish competing jobs before training: " + "; ".join(busy)
        )


def validate_training_rows(rows):
    if not rows:
        raise ValueError("Empty training dataset")
    for row in rows:
        messages = row["messages"]
        if messages[:2] != messages_for(row["narrative"]):
            raise ValueError(f"Prompt drift in report {row['report_id']}")
        if len(messages) != 3 or messages[2]["role"] != "assistant":
            raise ValueError("Expected one assistant completion")
        parse_brief(messages[2]["content"])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default=DEFAULT_CONFIG)
    parser.add_argument("--dry-run", action="store_true", help="100 rows, 50 optimizer steps")
    parser.add_argument("--max-steps", type=int)
    parser.add_argument("--resume", nargs="?", const="latest")
    parser.add_argument("--seq-length", type=int)
    parser.add_argument("--rank", type=int)
    parser.add_argument("--attention-only", action="store_true")
    args = parser.parse_args()
    config = read_config(args.config)
    if args.seq_length:
        config["max_seq_length"] = args.seq_length
    if args.rank:
        config["lora_rank"] = config["lora_alpha"] = args.rank
    if args.attention_only:
        config["target_modules"] = ["q_proj", "k_proj", "v_proj", "o_proj"]
    run_name = "dry-run" if args.dry_run else "asrs-v01"
    out = Path("checkpoints/dry-run" if args.dry_run else config["output_dir"])
    adapter_dir = Path(
        "adapters/debrief-qwen3-8b-dry-run" if args.dry_run else config["adapter_dir"]
    )
    meta_path = Path(f"eval_runs/{'dry_run' if args.dry_run else 'train'}_meta.json")
    if adapter_dir.exists() and not args.resume:
        raise ValueError(
            f"Adapter output exists: {adapter_dir}. Choose a new directory or --resume."
        )
    rows = read_jsonl(config["train_file"])
    validate_training_rows(rows)
    if args.dry_run:
        rows = rows[:100]
    # A train-only loss probe avoids evaluating the held-out benchmark during fitting.
    # This is NOT a validation score; the report labels its origin explicitly.
    probe = rows[:32]
    gpu_preflight()
    from unsloth import FastLanguageModel, is_bfloat16_supported
    import torch
    from datasets import Dataset
    from trl import SFTConfig, SFTTrainer
    from unsloth.chat_templates import train_on_responses_only

    if not torch.cuda.is_available():
        raise RuntimeError("NVIDIA CUDA GPU required")
    started = time.time()
    torch.cuda.reset_peak_memory_stats()
    metadata = {
        "status": "running",
        "run_id": run_name,
        "config": config,
        "started_at": started,
        "train_rows": len(rows),
        "eval_loss_source": "32 training rows (monitor only)",
        "train_sha256": sha256(config["train_file"]),
        "system_prompt_sha256": hashlib.sha256(SYSTEM_PROMPT.encode()).hexdigest(),
        "git_commit": subprocess.run(
            ["git", "rev-parse", "HEAD"], capture_output=True, text=True
        ).stdout.strip(),
        "gpu": torch.cuda.get_device_name(),
        "gpu_total_bytes": torch.cuda.get_device_properties(0).total_memory,
        "torch": torch.__version__,
        "cuda": torch.version.cuda,
    }
    write_json(meta_path, metadata)
    try:
        model, tokenizer = FastLanguageModel.from_pretrained(
            model_name=config["model_id"],
            revision=config["model_revision"],
            max_seq_length=config["max_seq_length"],
            load_in_4bit=True,
            dtype=torch.bfloat16 if is_bfloat16_supported() else torch.float16,
            trust_remote_code=False,
        )
        model = FastLanguageModel.get_peft_model(
            model,
            r=config["lora_rank"],
            target_modules=config["target_modules"],
            lora_alpha=config["lora_alpha"],
            lora_dropout=0,
            bias="none",
            use_gradient_checkpointing="unsloth",
            random_state=config["seed"],
        )

        def formatted(data):
            texts = [
                tokenizer.apply_chat_template(
                    row["messages"], tokenize=False, enable_thinking=False
                )
                for row in data
            ]
            lengths = [len(tokenizer.encode(t, add_special_tokens=False)) for t in texts]
            # Never silently truncate gold sections at a lower OOM fallback length.
            kept = [text for text, size in zip(texts, lengths) if size <= config["max_seq_length"]]
            if not kept:
                raise ValueError(
                    "No examples fit sequence length; rebuild with a smaller narrative cap"
                )
            return Dataset.from_dict({"text": kept})

        train_dataset, probe_dataset = formatted(rows), formatted(probe)
        metadata["effective_train_rows"] = len(train_dataset)
        metadata["dropped_overlength"] = len(rows) - len(train_dataset)
        max_steps = args.max_steps if args.max_steps is not None else (50 if args.dry_run else -1)
        trainer = SFTTrainer(
            model=model,
            processing_class=tokenizer,
            train_dataset=train_dataset,
            eval_dataset=probe_dataset,
            args=SFTConfig(
                output_dir=str(out),
                dataset_text_field="text",
                max_length=config["max_seq_length"],
                per_device_train_batch_size=config["per_device_train_batch_size"],
                per_device_eval_batch_size=1,
                gradient_accumulation_steps=config["gradient_accumulation_steps"],
                learning_rate=config["learning_rate"],
                lr_scheduler_type=config["lr_scheduler_type"],
                warmup_ratio=config["warmup_ratio"],
                num_train_epochs=config["num_train_epochs"],
                max_steps=max_steps,
                fp16=not is_bfloat16_supported(),
                bf16=is_bfloat16_supported(),
                optim="adamw_8bit",
                logging_steps=1 if args.dry_run else 5,
                save_strategy="epoch",
                save_total_limit=2,
                eval_strategy="epoch",
                eval_accumulation_steps=1,
                prediction_loss_only=True,
                packing=False,
                dataset_num_proc=1,
                seed=config["seed"],
                data_seed=config["seed"],
                report_to="none",
                dataloader_num_workers=0,
            ),
        )
        trainer = train_on_responses_only(
            trainer, instruction_part="<|im_start|>user\n", response_part="<|im_start|>assistant\n"
        )
        # A broken mask can silently train on zero assistant tokens.
        if any(not any(label != -100 for label in row["labels"]) for row in trainer.train_dataset):
            raise ValueError("Assistant response mask is empty")
        resume = args.resume
        if resume == "latest":
            from transformers.trainer_utils import get_last_checkpoint

            resume = get_last_checkpoint(str(out))
            if not resume:
                raise ValueError(f"No checkpoint found in {out}")
        if resume:
            previous = Path(resume) / "debrief_run.json"
            if not previous.exists():
                raise ValueError("Checkpoint has no Debrief provenance")
            provenance = json.loads(previous.read_text())
            if (
                provenance["train_sha256"] != metadata["train_sha256"]
                or provenance["config"] != config
            ):
                raise ValueError("Resume dataset or training config differs from checkpoint")
        from transformers import TrainerCallback

        class ProvenanceCallback(TrainerCallback):
            def on_save(self, args, state, control, **kwargs):
                write_json(
                    Path(args.output_dir) / f"checkpoint-{state.global_step}" / "debrief_run.json",
                    metadata,
                )

        trainer.add_callback(ProvenanceCallback())
        result = trainer.train(resume_from_checkpoint=resume)
        if not math.isfinite(result.training_loss):
            raise RuntimeError("Training loss is non-finite")
        model.save_pretrained(str(adapter_dir))
        tokenizer.save_pretrained(str(adapter_dir))
        write_json(adapter_dir / "debrief_config.json", config)
        metadata.update(
            status="complete",
            metrics=result.metrics,
            global_step=trainer.state.global_step,
            history=trainer.state.log_history,
        )
        # Keep an inspectable CSV; no dashboard required.
        import csv

        with Path(f"eval_runs/{run_name}_loss.csv").open("w") as stream:
            writer = csv.DictWriter(
                stream,
                fieldnames=["step", "epoch", "loss", "eval_loss", "learning_rate"],
                extrasaction="ignore",
            )
            writer.writeheader()
            writer.writerows(trainer.state.log_history)
    except BaseException as exc:
        metadata.update(status="failed", error=f"{type(exc).__name__}: {exc}")
        raise
    finally:
        metadata.update(
            wall_seconds=time.time() - started,
            peak_vram_allocated_bytes=torch.cuda.max_memory_allocated(),
            peak_vram_reserved_bytes=torch.cuda.max_memory_reserved(),
        )
        write_json(meta_path, metadata)


if __name__ == "__main__":
    main()

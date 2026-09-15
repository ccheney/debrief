# Debrief

Turn an incident narrative into a grounded, seven-section investigator brief.
Debrief is a local Python CLI and a QLoRA adapter, trained on Cathedral's RTX 3080 Ti.

**Checkpoint:** `debrief-qwen3-8b-asrs-v01`  
**Base:** `unsloth/Qwen3-8B-unsloth-bnb-4bit`  
**Pinned revision:** `62efd7f9d748e394734a7adae2adf96e13a2abc8`

Status: implementation and CPU checks complete; GPU smoke run, full training, and
held-out acceptance evaluation are in progress. A trained adapter is not yet claimed.

## Quick start

```sh
uv sync --extra dev
uv run python -E -m pytest -q
uv run python -E -m src.build_dataset
```

`-E` prevents unrelated global Python environment variables from contaminating the
virtual environment. Data preparation and scoring existing predictions work on
macOS. Model training and inference require NVIDIA CUDA on Cathedral.

```sh
scripts/cathedral.sh sync
scripts/cathedral.sh build
scripts/cathedral.sh run python -m src.train_unsloth --dry-run
scripts/cathedral.sh run python -m src.train_unsloth
scripts/cathedral.sh run python -m src.eval_briefs
scripts/cathedral.sh run python -m src.infer \
  --adapter adapters/debrief-qwen3-8b-asrs-v01 --file fixtures/dark_tug.txt
```

The training image is isolated from Coolify services. `scripts/cathedral.sh status`
shows GPU and run status; `fetch` downloads adapters and reports. The remote
workspace currently lives at `/home/ccheney/briefcard` (the original working name).

## CLI

```sh
python -m src.infer --file story.txt
python -m src.infer --text 'Something went wrong; the cause is unknown.' --json
python -m src.infer --batch incidents.jsonl
cat story.txt | python -m src.infer --stdin
python -m src.infer --base --file story.txt
```

Batch input is one `{"id":"example","narrative":"..."}` object per line. Batch
output contains `id`, `brief` and `input_truncated`. JSON mode emits structured
fields. Diagnostics go to stderr. Invalid model output is preserved as an error
with its raw text and exits 2; the CLI never repairs an invalid output into a
supposedly valid model prediction. Long inputs keep a bounded head and tail.

## Data and leakage controls

The builder downloads the pinned ASRS source, verifies the card license, rejects
short or unsupervised reports, truncates at the base tokenizer, and builds
4,000/400 train/eval rows. It groups report IDs, related accession IDs and exact
normalized duplicate narratives. The remainder is reserved as IDs only.

Generated files in `data/processed/`:

- `train.jsonl`, `eval.jsonl`: narrative, chat messages and split provenance.
- `label_map.json`, `column_inventory.json`: explicit codes and observed source columns.
- `manifest.json`, `build_report.md`: hashes, revisions, license and drop counts.
- `review_train.md`, `review_eval.md`: reproducible 50-row review samples each.

Only a ten-row sample may be committed. Raw data, full splits, checkpoints and
weights are ignored by git. No synopsis is used as an inference input and no
teacher model writes gold prose. See [mapping notes](docs/data-design.md).

## Training on 12 GB

Default: sequence 2048, rank/alpha 16/16, batch 1, accumulation 8, cosine LR 2e-4,
5% warmup, 2 epochs, no packing, Unsloth gradient checkpointing and bf16 on the
3080 Ti. Loss is masked to assistant completions. Epoch checkpoints retain the
last two and can resume with `--resume latest`; changed data/config is rejected.

The 50-step dry run uses 100 rows and a separate adapter/checkpoint directory.
Measure peak VRAM before a full run. If necessary try `--seq-length 1536`, then
`--rank 8`, then `--attention-only`. Overlength chats are explicitly counted and
excluded rather than silently clipping the gold card. Rebuild with a smaller
narrative cap if excluding rows changes the experiment too much.

Use the GPU exclusively while training. Check `nvidia-smi`; the trainer refuses
to begin if an existing compute process uses more than 100 MiB. Finish or stop
competing Whisper/model jobs explicitly. Do not launch a model in Studio during
a training run. Coolify, DNS, proxy, database and monitoring services can stay up.

`eval_runs/train_meta.json` records resolved config, base/revision, source revision,
train hash, GPU, precision, torch/CUDA, time, peak memory and loss history. The
training-time `eval_loss` is a **32-row training loss probe**, not a held-out
quality score. The 400-row benchmark is never fed to the trainer.

## Evaluation

`python -m src.eval_briefs` generates base and adapter outputs from the same loaded
base weights, prompt, seed per row, temperature 0.2, top-p 0.9, top-k 20 and
400-token budget. It checks ID/group/narrative disjointness before generation.

Outputs: paired predictions, per-report scores, base/adapter table, explicit
acceptance gates and a 20-row rubric packet plus grounding failures. `--limit 10`
is labeled a smoke test; it cannot establish acceptance. `--predictions FILE`
re-scores an existing complete paired run without CUDA.

Acceptance requires at least 95% valid schema, +15 points factor accuracy,
+10 points phase accuracy, no worse grounding and at most 10% specificity flags,
and improved recovery without collapse. The report does not call a training loss
or a schema-only demo a model-quality win.

## Unsloth Studio

The GPU-backed UI is deployed separately via `deploy/unsloth.compose.yaml` at
[unsloth.cathedral.home.arpa](http://unsloth.cathedral.home.arpa). It uses the
existing Cathedral wildcard DNS and Coolify Traefik proxy. Studio state persists
in Docker volumes. The source and adapters are visible at `/workspace/debrief`.
The CLI environment remains separately pinned for reproducible experiments.

## Scope and limitations

The supplied [PRD](prd.md) is preserved as the original specification. The product
name is now Debrief. Qwen3-8B was explicitly selected because its supported Unsloth
prequantized build is available; the proposed Qwen 9B prequantized build was not.
See the [model card](MODEL_CARD.md) for exact provenance and heuristic limitations.
Ops fixtures demonstrate schema compatibility; a second domain pack and GGUF
export are later milestones. This is not an official NASA/NTSB finding or a tool
for operational aviation decisions.

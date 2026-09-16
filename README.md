# Debrief

Turn an incident narrative into a grounded, seven-section investigator brief.
Debrief is a local Python CLI and a QLoRA adapter, trained on Cathedral's RTX 3080 Ti.

**Current checkpoint:** `debrief-qwen3-8b-asrs-v02` (accepted for local experimental use)  
**Base:** `unsloth/Qwen3-8B-unsloth-bnb-4bit`  
**Pinned revision:** `62efd7f9d748e394734a7adae2adf96e13a2abc8`

## Status

| Version | Gold rules | Outcome |
|---|---|---|
| `debrief-qwen3-8b-asrs-v01` | label map 3 | Trained 2026-09-15. **Not accepted.** Seven of nine automatic gates pass (schema 100%, factor +37 pp, phase +44 pp, grounding better than base) but the adapter never emits a lesson and answers Unknown recovery on 391 of 400 rows, because those fields were empty in 92–98% of its gold. See [v0.1 results](docs/v01-results.md). |
| `debrief-qwen3-8b-asrs-v02` | label map 4 | Trained 2026-09-16. **All nine automatic gates pass**: schema 100%, factor +41 pp, phase +47 pp, recovery improves without collapse, grounding better than base under the stricter event-class check. Emits verbatim, grounded lessons on 18% of rows (recall 61%), recovery with evidence on 19%. Rubric: 16 of 20 random briefs clean. See [v0.2 results](docs/v02-results.md). |

v0.2 is accepted for **local experimental use** under PRD Phase 4 ("ship locally if P0 metrics beat base and grounding is not worse"). It is an agent review, not a human sign-off; the adapter stays private and is not for operational decisions.

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
scripts/cathedral.sh deploy    # push the current commit into Cathedral's checkout (it has no GitHub key)
scripts/cathedral.sh sync      # processed data (and any uncommitted code) to /home/ccheney/briefcard
scripts/cathedral.sh build     # training image (only when requirements change)
scripts/cathedral.sh run python -m src.train_unsloth --dry-run
scripts/cathedral.sh run python -m src.verify_resume
scripts/cathedral.sh launch    # detached: train, evaluate, demos for the configured version
scripts/cathedral.sh status    # GPU, container, stage, latest progress line
scripts/cathedral.sh fetch     # adapters, eval_runs and logs back to this machine
```

The training image is isolated from Coolify services. Every artifact of a run is
namespaced by the `version` key in `configs/train_qwen8b_qlora.yaml`:
`checkpoints/asrs-<version>`, `adapters/debrief-qwen3-8b-asrs-<version>`,
`eval_runs/<version>_*`, `logs/<version>/` and the container
`debrief-experiment-<version>`. The remote workspace lives at
`/home/ccheney/briefcard` (the original working name).

## CLI

```sh
python -m src.infer --file story.txt
python -m src.infer --text 'Something went wrong; the cause is unknown.' --json
python -m src.infer --batch incidents.jsonl
cat story.txt | python -m src.infer --stdin
python -m src.infer --base --file story.txt
python -m src.infer --adapter adapters/debrief-qwen3-8b-asrs-v01 --file story.txt
```

The adapter defaults to `adapter_dir` in the project config. Batch input is one
`{"id":"example","narrative":"..."}` object per line. Batch output contains `id`,
`brief` and `input_truncated`. JSON mode emits structured fields. Diagnostics go
to stderr. Invalid model output is preserved as an error with its raw text and
exits 2; the CLI never repairs an invalid output into a supposedly valid model
prediction. Long inputs keep a bounded head and tail.

## Data and leakage controls

The builder downloads the pinned ASRS source, verifies the card license, rejects
short or unsupervised reports, truncates at the base tokenizer, and builds
4,000/400 train/eval rows. It groups report IDs, related accession IDs and exact
normalized duplicate narratives. The remainder is reserved as IDs only.

Gold cards are deterministic and extractive; no teacher model writes prose.
"What happened" is the source-checked synopsis. The near miss, the recovery
evidence and the lesson are sentences copied verbatim from the narrative when a
documented rule matches (label map version 4, see [data design](docs/data-design.md)).
Rows whose synopsis asserts an event class the narrative never mentions are
rejected. Rows with a stated near miss are duplicated three times in the
training split only; the held-out split keeps its natural mix.

Generated files in `data/processed/`:

- `train.jsonl`, `eval.jsonl`: narrative, chat messages and split provenance.
- `label_map.json`, `column_inventory.json`: explicit codes and observed source columns.
- `manifest.json`, `build_report.md`: hashes, revisions, license and drop counts.
- `review_train.md`, `review_eval.md`: reproducible 50-row review samples each.

The full trainer requires `review_decision.json` with a 100-row review bound to
the train/eval file hashes. Reviews so far are agent reviews, recorded in
[docs/gold-review.md](docs/gold-review.md) (v0.1) and
[docs/gold-review-v02.md](docs/gold-review-v02.md) (v0.2); the strict
human-review milestone remains outstanding.

Only a ten-row sample may be committed. Raw data, full splits, checkpoints and
weights are ignored by git. No synopsis is used as an inference input.

## Training on 12 GB

Default: sequence 2048, rank/alpha 16/16, batch 1, accumulation 8, cosine LR 2e-4,
5% warmup, 2 epochs, no packing, Unsloth gradient checkpointing and bf16 on the
3080 Ti. Loss is masked to assistant completions. Epoch checkpoints retain the
last two and can resume with `--resume latest`; changed data/config or training
subset is rejected before GPU allocation. Incomplete newer saves are skipped.
See [resume verification](docs/resume-verification.md) for the isolated GPU test.

v0.1 measured: 1,000 steps in 95 minutes, peak reserved VRAM 9.3 GiB. The 50-step
dry run uses 100 rows and a separate adapter/checkpoint directory. If a run OOMs,
try `--seq-length 1536`, then `--rank 8`, then `--attention-only`. Overlength
chats are counted and excluded rather than silently clipping the gold card.

Use the GPU exclusively while training. Check `nvidia-smi`; the trainer refuses
to begin if an existing compute process uses more than 100 MiB. Do not launch a
model in Studio during a training run. Coolify, DNS, proxy, database and
monitoring services can stay up.

`eval_runs/<run>_meta.json` records resolved config, base/revision, source
revision, train hash, GPU, precision, torch/CUDA, time, peak memory and loss
history. The training-time `eval_loss` is a **32-row training loss probe**, not
a held-out quality score. The 400-row benchmark is never fed to the trainer.

## Evaluation

`python -m src.eval_briefs` generates base and adapter outputs from the same loaded
base weights, prompt, seed per row, temperature 0.2, top-p 0.9, top-k 20 and
400-token budget. It checks ID/group/narrative disjointness before generation.

Outputs: paired predictions, per-report scores, base/adapter table, explicit
acceptance gates, a 20-row rubric packet plus grounding failures, and a 50-row
lesson review packet. Full-narrative packets stay out of git; commit condensed
review notes after inspection. `--limit 10` is labeled a smoke test; it cannot
establish acceptance. `--predictions FILE` re-scores an existing complete paired
run without CUDA.

Acceptance requires at least 95% valid schema, +15 points factor accuracy,
+10 points phase accuracy, no worse grounding and at most 10% grounding flags,
and improved recovery without collapse. Grounding flags cover invented numbers,
invented acronyms and, since v0.2, asserted event classes ("near miss", "runway
incursion", "engine failure", …) absent from the narrative. Lesson recall,
emission rate and a lexical "no new facts" check are reported but not gated.
The report does not call a training loss or a schema-only demo a model-quality win.

## Unsloth Studio

The GPU-backed UI is deployed separately via `deploy/unsloth.compose.yaml` at
[unsloth.cathedral.home.arpa](http://unsloth.cathedral.home.arpa). It uses the
existing Cathedral wildcard DNS and Coolify Traefik proxy. Studio state persists
in Docker volumes. The source and adapters are visible at `/workspace/debrief`.
The CLI environment remains separately pinned for reproducible experiments.
See [Studio operations](docs/cathedral-studio.md).

## Scope and limitations

The supplied [PRD](prd.md) is preserved as the original specification. The product
name is Debrief; checkpoints are named after the base actually trained. Qwen3-8B
was selected because its supported Unsloth prequantized build is available; the
proposed Qwen 9B prequantized build was not. See the [model card](MODEL_CARD.md)
for exact provenance and heuristic limitations. Ops fixtures demonstrate schema
compatibility; a second domain pack and GGUF export are later milestones. This is
not an official NASA/NTSB finding or a tool for operational aviation decisions.

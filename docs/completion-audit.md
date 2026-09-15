# Completion audit

The full experiment is running on Cathedral from training commit `ca46d59`.
This checklist records evidence and remaining verification, not a completion claim.

| Requirement | Evidence / current state |
|---|---|
| Python CLI, repo, schema, ten fixtures | Implemented in `src/`; ten paired fixtures; parser and mappings tested. |
| Frozen system prompt; controlled vocabularies | `src/schema.py`, `src/prompt.py`; same messages at train/infer/eval. Adapter records prompt hashes. |
| Actual ASRS columns, pinned source, license | `data/processed/column_inventory.json`, `manifest.json`, `docs/build-report.md`. |
| Filtering, tokenizer cap, head/tail, deterministic gold | Source-checked synopsis; deterministic maps/heuristics; bounded 2:1 head/tail with omission marker. `docs/data-design.md`. |
| 4,000 train / 400 eval, seed 42, disjoint IDs | Generated files; actual 4,400-card parse and ID/group/narrative disjointness checks passed. |
| 100-row builder review and notes | `docs/gold-review.md`: agent semantic review of 50 train + 50 eval, 12 flagged concerns. Method and limits explicitly recorded; not represented as human peer review. |
| No training data in git beyond ten-row sample | Git ignores raw/full processed data and weights; only `data/processed/sample.jsonl` is tracked. |
| Isolated GPU dependencies, pinned base, 12 GB | Dedicated Docker image; verified NVIDIA 3080 Ti, Unsloth, bf16 and model reload. Exact dependencies in `requirements-gpu.lock.txt`. |
| 50-step dry run; checkpoint write/reload | Completed: `eval_runs/dry_run_meta.json`, 321.8 seconds, peak reserved 8.74 GiB, 50 optimizer steps. Dry adapter reload produced parseable fixture JSON. |
| Full 4k × 2 epochs within six hours | Running in `debrief-experiment`; not yet proven. |
| Resume from checkpoint | Implementation guards dataset/config provenance. Actual resume exercise remains to verify after GPU availability. |
| Loss/LR/time/VRAM/git/model provenance | Dry run recorded. Full metadata pending completion. Training-time eval loss is explicitly a training-set probe; held-out evaluation is separate. |
| Base versus adapter on all 400 reports | Queued after training; metrics and report not yet available. Both modes use identical prompts, decoding and per-row seeds. |
| Validity ≥95%, factor +15 pp, phase +10 pp | Pending held-out results; must not infer from training loss or smoke fixtures. |
| Grounding ≤10% and no worse than base | Pending automatic score and semantic rubric. Lexical check alone cannot prove grounding. |
| Recovery improves without collapsing | Pending. Scorer now checks both binary labels on derivable rows, rather than allowing Unknown to conceal binary collapse. |
| Near-miss distinction, one-sentence lesson, length | Automatic metrics implemented; semantic review and 50-row lesson spot-check pending generated results. |
| Rubric: 20 random outputs plus failure clusters | Packet generation implemented; actual review pending outputs. |
| Adapter model card and reload | Save-time card/config/provenance implemented; full adapter pending. |
| Text, JSON, batch inference | Implemented; dry text/JSON reload verified. Full artifact + batch verification pending. |
| Three unseen examples (aviation, ops, ambiguous) | Queued after evaluation. The ops domain pack remains a later optional milestone. |
| Unsloth Studio on Cathedral with hostname | Live at `http://unsloth.cathedral.home.arpa`; authenticated GPU endpoint and password persistence across container replacement verified. |

## Scoring fixes before the benchmark

A regression test demonstrated that the old recovery gate could pass a model
predicting only Yes on known outcomes by also emitting Unknown elsewhere. The
gate now requires Yes and No predictions among known-outcome rows, with both
classes present in gold. Another test caught unknown headings being accepted
inside a free-text section; these now fail schema validation. All frozen gold
cards remain valid. The benchmark has not yet generated any outputs; the report
will record scorer hashes and adapter-file hashes.

## Remaining work

Wait on the live container; inspect failures without restarting a still-running
job. After completion, inspect the full metric table and output files, perform
the rubric and lesson reviews, exercise resume and batch inference, retrieve
artifacts, update the model card/README with actual results, and commit reports.
Apply the PRD's decision rules honestly; unmet targets are not acceptance.

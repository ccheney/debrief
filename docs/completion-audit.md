# Completion audit

This checklist records evidence against the PRD, not a completion claim. v0.1
ran from training commit `ca46d59`; v0.2 runs from the commit recorded in its
`eval_runs/asrs-v02_meta.json`.

| Requirement | Evidence / current state |
|---|---|
| Python CLI, repo, schema, ten fixtures | Implemented in `src/`; ten paired fixtures; parser and mappings tested (112 tests). |
| Frozen system prompt; controlled vocabularies | `src/schema.py`, `src/prompt.py`; same messages at train/infer/eval. Adapter records prompt hashes; unchanged between v0.1 and v0.2. |
| Actual ASRS columns, pinned source, license | `data/processed/column_inventory.json`, `manifest.json`, `docs/build-report.md`. |
| Filtering, tokenizer cap, head/tail, deterministic gold | Source-checked synopsis; deterministic maps/rules (label map 4); bounded 2:1 head/tail with omission marker. `docs/data-design.md`. |
| 4,000 train / 400 eval, seed 42, disjoint IDs | v0.2 build: 4,000 unique train rows plus 220 near-miss copies, 400 eval; parse and ID/group/narrative disjointness checks passed. |
| 100-row builder review and notes | v0.1: `docs/gold-review.md` (12 concerns). v0.2: `docs/gold-review-v02.md`, agent review bound to the split hashes. Neither is a human sign-off. |
| No training data in git beyond ten-row sample | Git ignores raw/full processed data and weights; only `data/processed/sample.jsonl` is tracked. |
| Isolated GPU dependencies, pinned base, 12 GB | Dedicated Docker image; verified NVIDIA 3080 Ti, Unsloth, bf16 and model reload. Exact dependencies in `requirements-gpu.lock.txt`. |
| 50-step dry run; checkpoint write/reload | Completed: `eval_runs/dry_run_meta.json`, 321.8 seconds, peak reserved 8.74 GiB. Dry adapter reload produced parseable fixture JSON. |
| Full 4k × 2 epochs within six hours | v0.1: 1,000 steps in 5,679 s, peak reserved 9.34 GiB (`eval_runs/asrs-v01_meta.json`). |
| Resume from checkpoint | CPU tests cover incomplete saves, changed data/config and subset mismatch. GPU restart check passed 2026-09-15 on the v0.2 data: `docs/resume-verification.md`. |
| Loss/LR/time/VRAM/git/model provenance | Recorded per run in `eval_runs/<run>_meta.json` and `<run>_loss.csv`. Training-time eval loss is a training-set probe. |
| Base versus adapter on all 400 reports | v0.1: `eval_runs/v01.md`, `v01_metrics.json`. v0.2: pending. |
| Validity ≥95%, factor +15 pp, phase +10 pp | v0.1 passed all three (1.00; +37 pp; +44 pp). |
| Grounding ≤10% and no worse than base | v0.1 passed the lexical check (0.5% vs 3.0%); the rubric found semantic errors in 8 of 22 rows. v0.2 adds event-class grounding to the automatic check. |
| Recovery improves without collapsing | v0.1 failed both: 0.23 vs 0.58 on 31 rows, and no No predictions. Root cause is gold prevalence; see `docs/v01-results.md`. |
| Near-miss distinction, one-sentence lesson, length | v0.1: 0.56 on 9 rows (target 0.80); no lesson ever emitted; median 59 tokens. |
| Rubric: 20 random outputs plus failure clusters | v0.1 reviewed in `docs/v01-results.md`. |
| Adapter model card and reload | v0.1 adapter reloads; card written at save time. |
| Text, JSON, batch inference | Text/JSON verified on v0.1 demos. Batch verified 2026-09-15 with the v0.1 adapter on `fixtures/batch.jsonl`: three valid briefs, exit 0, 30 s including model load. |
| Three unseen examples (aviation, ops, ambiguous) | v0.1 demos recorded in `docs/v01-results.md`; all three missed the lesson and recovery. |
| Unsloth Studio on Cathedral with hostname | Live at `http://unsloth.cathedral.home.arpa`; password persistence across container replacement verified. |

## Decision after v0.1

PRD Phase 4 rule: schema good and factor accuracy up, grounding not worse than
base, three fields collapsed to their gold priors. **Fix data**, keep base and
hyperparameters, retrain as v0.2. Unmet targets are not acceptance.

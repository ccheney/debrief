# Checkpoint restart verification

The trainer checks checkpoint completeness, dataset hash, configuration and
training subset before allocating GPU memory. `--resume latest` skips an
unfinished newer save and selects the last complete checkpoint. A checkpoint
must contain adapter weights/configuration, optimizer, scheduler, RNG, Trainer
state and the atomic Debrief provenance marker. Fresh runs refuse to overwrite
existing checkpoints.

`--run-id` isolates diagnostic output directories. `--stop-after-steps` saves a
checkpoint and pauses without publishing an adapter as completed.

## GPU verification command

Run after the main experiment releases the GPU:

```sh
scripts/cathedral.sh run python -m src.verify_resume
```

This uses the frozen data/model configuration and a separate
`debrief-qwen3-8b-resume-check` namespace. It plans two optimizer steps, pauses
and saves after step one, then resumes for exactly one more optimizer step.
The verifier requires:

- First attempt is paused at step 1, with no completed adapter published.
- Resumed attempt explicitly loaded checkpoint 1 and performed only one step.
- Final global step is 2; stored optimizer counters advance from 1 to 2.
- Adapter tensors actually change after the resumed update.

Results are written to `eval_runs/debrief-qwen3-8b-resume-check_verification.json`.
A passing result has not yet been claimed; the GPU exercise is pending main-job
completion. CPU regression tests cover incomplete checkpoints, changed data or
model, dry/full subset mismatch and accidental checkpoint overwrite.

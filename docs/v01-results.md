# v0.1 results — `debrief-qwen3-8b-asrs-v01`

Reviewer: Claude (agent review of the automatic report and the rubric packet), 2026-09-15.
Decision under PRD §Phase 4: **fix data**. Not accepted; not shipped.

## Run

| Item | Value |
|---|---|
| Base | `unsloth/Qwen3-8B-unsloth-bnb-4bit@62efd7f9d748e394734a7adae2adf96e13a2abc8` |
| Data | 4,000 train / 400 held-out, seed 42, label map version 3 |
| Training | 1,000 optimizer steps, 2 epochs, 5,679 s, peak reserved VRAM 9.34 GiB |
| Loss | 3.04 → 0.49 (train), 0.43 on the 32-row training probe; no spikes |
| Evaluation | 400 paired base/adapter generations, temperature 0.2, per-row seeds |
| Provenance | `eval_runs/asrs-v01_meta.json`, `eval_runs/v01_metrics.json`, adapter sha256 `a67e4153…5b6d9` |

## Held-out metrics (`eval_runs/v01.md`)

| Metric | Base | Adapter | Gate |
|---|---:|---:|---|
| Valid schema | 0.565 | 1.000 | pass (≥ 0.95, not worse) |
| Primary factor accuracy | 0.328 | 0.698 | pass (+37 pp ≥ +15) |
| Phase accuracy | 0.323 | 0.767 | pass (+44 pp ≥ +10) |
| Grounding failures (numbers/acronyms) | 0.030 | 0.005 | pass (≤ 0.10, not worse) |
| Recoverable accuracy, 31 derivable rows | 0.581 | 0.226 | **fail** (must improve) |
| Recoverable predicts both Yes and No | yes | never No | **fail** (collapse) |
| Near-miss distinct, 9 gold rows | 0.222 | 0.556 | should-hit target 0.80 not met |
| Median tokens | 171 | 59 | should-hit met |

The base "wins" recovery only because it answers Yes on 224 of 400 rows and 28
of the 31 derivable rows happen to be Yes. Its overall recoverable accuracy is 0.05.

## Root cause: the adapter learned the gold priors

| Field | Non-empty in train gold | Adapter on 400 eval rows |
|---|---:|---:|
| Lesson | 2.5% | 0 of 400 emit a lesson |
| What almost happened | 1.4% | 7 of 400 |
| Recoverable is Yes or No | 7.9% | 9 of 400 (all 7 known-row Yes predictions correct, no No) |
| Contributing factors | 17.6% | 13.0% |

Version 3 of the deterministic extractors accepted a lesson only when a sentence
began with "We/Pilots/... should", accepted a near miss only on a handful of
explicit phrases, and derived recovery from a short pattern list that the 100-row
gold review had already flagged for false negatives ("I stopped", "performed the
reject", "went missed", off-field landings). At those prevalences the cheapest
policy is to always emit the empty value, and the adapter did exactly that: the
go-around and Docker OOM fixtures both end with an explicit "We should …"
sentence and both demos returned `None stated.`.

## Rubric review (20 random rows + 2 lexical grounding failures)

Scores 0–2 for grounding of "What happened", near-miss handling, primary factor,
and lesson handling, from `eval_runs/v01_rubric.md` against the full narratives.

| Report | Ground | Near miss | Factor | Lesson | Note |
|---|---|---|---|---|---|
| 1826165 | 1 | 2 | 2 | 2 | "engine failure … hard landing" for a partial power loss and a gear collapse in a field; recovery should be No |
| 1667630 | 2 | 2 | 2 | 2 | Accurate; recovery Unknown although the crew rejected the takeoff |
| 1477796 | 0 | 0 | 2 | 2 | Reporter attributed as "PA-28 pilot"; the PA-28 was the other aircraft; near-miss field copied the landing clearance sentence |
| 1746444 | 0 | 2 | 2 | 0 | "runway incursion" invented for a wrong taxiway turn; explicit "I should have delayed…" lesson missed |
| 1676949 | 1 | 0 | 2 | 1 | "near miss" for an encounter the narrator says was not a factor; near-miss field copied commentary |
| 1418305 | 2 | 2 | 2 | 2 | Accurate |
| 1504017 | 2 | 2 | 2 | 1 | Accurate; "Will now always realize failure can happen" not surfaced |
| 1104407 | 2 | 2 | 2 | 2 | Accurate compression of a long report |
| 1593509 | 2 | 2 | 2 | 1 | Accurate; study-the-unit recommendation not surfaced |
| 1835977 | 2 | 1 | 2 | 2 | Accurate; explicit "possible wingtip collision" not surfaced; injury means recovery No |
| 1829597 | 2 | 2 | 2 | 2 | Accurate; the only Yes recovery with evidence in the sample |
| 1001364 | 2 | 2 | 2 | 2 | Accurate |
| 1053801 | 2 | 2 | 1 | 2 | Bird strike labeled Unknown factor |
| 1713005 | 2 | 2 | 2 | 0 | "All aircraft should comply promptly to ATC instructions…" missed |
| 1057479 | 1 | 2 | 2 | 2 | Magneto failure was found after landing; in-flight event was a surge and precautionary shutdown |
| 1874135 | 2 | 2 | 2 | 2 | Accurate; diversion and safe landing not reflected in recovery |
| 988193 | 2 | 2 | 2 | 2 | Accurate |
| 1760063 | 2 | 2 | 2 | 0 | Two explicit suggestions in the narrative missed |
| 1853596 | 0 | 2 | 2 | 2 | "after takeoff" invented; the HAZMAT message arrived during taxi-out and the crew returned to the gate |
| 1684237 | 2 | 2 | 1 | 0 | "we should be advised by ATC…" missed; factor arguably ATC |
| 1710694 | 0 | 2 | 1 | 1 | "CVG" invented for Charlottesville (caught by the acronym check) |
| 997520 | 1 | 2 | 2 | 2 | Reporter is maintenance staff, not Maintenance Control; "C-Check" is a false acronym flag |

Grounding: 14 clean, 4 partial, 4 wrong out of 22. The wrong ones are semantic
(attribution, invented event class, invented timing) and invisible to the
numbers/acronyms check, which reports 0.5%. The adapter writes in ASRS synopsis
voice and classifies events with taxonomy terms ("near miss", "runway
incursion", "loss of separation") the narrative never uses; a probe over all 400
outputs finds such an unsupported term in roughly one brief in ten.

## Demo fixtures

| Fixture | Adapter | Gold | Miss |
|---|---|---|---|
| go_around | Approach / Human / Unknown / no lesson | Approach / Weather / Yes / "We should abandon an unstable approach." | factor, recovery, lesson |
| docker_oom | Unknown / Human / Unknown / no lesson | Unknown / Procedure / Yes / "Measure memory use under load…" | factor, recovery, lesson |
| ambiguous | Parked / Equipment / Unknown / no lesson | Unknown / Unknown / Unknown / no lesson | invented phase and factor |

## What v0.2 changes

Data only; base, hyperparameters and prompts are unchanged so the runs compare.

- Label map version 4: extractive lesson rule accepts any explicit reporter
  recommendation (modal recommendations, "In the future I will…", lead-in
  imperatives) and rejects reported speech and narration; near-miss and
  recovery rules cover the wordings the v0.1 review recorded as misses;
  completed-event rules add injuries, damage, excursions and off-field landings.
- Synopsis sentences that assert an event class absent from the narrative are
  rejected, and the same check is applied to model outputs as a third grounding
  category.
- Near-miss rows are duplicated three times in the training split only.
- Every run artifact is namespaced by version (`eval_runs/v02_*`, `logs/v02/`,
  `checkpoints/asrs-v02`, `adapters/debrief-qwen3-8b-asrs-v02`).

## Outstanding from the v0.1 checklist

Checkpoint resume was verified on CPU tests only; the isolated GPU restart check
and a batch-inference check were queued for after the run and are exercised
before the v0.2 launch. The 50-row lesson spot-check is moot for v0.1: every
lesson is `None stated.`.

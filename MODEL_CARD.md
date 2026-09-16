---
language: en
license: apache-2.0
base_model: unsloth/Qwen3-8B-unsloth-bnb-4bit
datasets:
  - elihoole/asrs-aviation-reports
library_name: peft
pipeline_tag: text-generation
tags: [qlora, incident-briefs, asrs, debrief]
---
# Debrief — debrief-qwen3-8b-asrs-v02

**Status: v0.2 passes all automatic gates and the agent rubric; accepted for local experimental use only.**

Debrief converts incident narratives into seven-section briefs. The checkpoint
name identifies the base, domain and version; it is independent of the product name.

## Provenance

- Base: `unsloth/Qwen3-8B-unsloth-bnb-4bit`
- Base revision: `62efd7f9d748e394734a7adae2adf96e13a2abc8`
- Source: `elihoole/asrs-aviation-reports`
- Source revision: `f1e681e92cddae20d01fc498d685f1cf6a052d34`
- Source split: `asrs-aviation-reports-train.jsonl`, 38,655 raw rows.
- Dataset card declares `apache-2.0`, verified against this revision at build time.
- 4,000 train and 400 held-out reports; seed 42; accession links and duplicate narratives grouped.
  v0.2 duplicates the 110 training rows with a stated near miss three times (4,220 rows written).
- Training method: Unsloth QLoRA, 4-bit base, rank/alpha 16/16, assistant-only loss.
- Actual hardware, effective parameters, losses, wall time and peak VRAM: `eval_runs/<run>_meta.json`.

## Results so far

| Checkpoint | Gold rules | Held-out verdict |
|---|---|---|
| `debrief-qwen3-8b-asrs-v01` | label map 3 | Not accepted. Schema 100%, factor 0.70 (base 0.33), phase 0.77 (base 0.32), grounding flags 0.5% (base 3.0%); lesson never emitted, recovery collapsed to Unknown. [Details](docs/v01-results.md). |
| `debrief-qwen3-8b-asrs-v02` | label map 4 | All gates pass. Schema 1.00, factor 0.73 (base 0.32), phase 0.81 (base 0.34), recovery 0.51 on 109 derivable rows (base 0.43) with both classes predicted, grounding flags 3.3% (base 6.2%) including event classes; lessons verbatim and grounded, recall 0.61. [Details](docs/v02-results.md). |

## Schema

What happened; What almost happened; Phase of flight; Primary factor;
Contributing factors; Recoverable; Lesson. See `src/schema.py` and `src/prompt.py`.
The system prompt is frozen. The schema instructions in the user message are
identical for base, adapter, training and inference across versions.

## Supervision and limitations

Gold prose uses the first source-checked synopsis sentences. Unsupported aircraft
types, named models and descriptors are generalized to aircraft; unsupported role
titles to reporter; a stated cause must be attested by the narrative.
A target is rejected for ungrounded numbers/acronyms, an asserted event class the
narrative never mentions, less than 50% content-word overlap, explicit narrator
uncertainty, or unsupported airport elevation claims. The first synopsis sentence
must pass; a later sentence cannot replace the main event. These checks provide
weak supervision, not proof of semantic grounding: the v0.1 rubric review found
attribution and timing errors in about one brief in five that the lexical checks
cannot see.

Phase and factor classes are mapped from analyst codes. Multiple phases use the
first listed source code, which is not necessarily chronological. `ATC Equipment`
maps to Equipment; explicit controller-clearance attribution can map Human Factors
to ATC. These labels are noisy and may disagree with a reasonable reader.

Recoverability uses deterministic, locally negation-aware rules: completed
outcomes (collision, damage, injury, excursion, gear collapse, off-field landing)
give No; successful interventions and safe outcomes (go-around, rejected takeoff,
stopped, returned or diverted, landed safely) give Yes; otherwise Unknown. It is
not an assessment of how controllable the event was. Near misses and lessons are
narrative sentences copied verbatim when an explicit rule matches; a reporter's
recommendation phrased without a modal or lead-in is missed and the lesson stays
`None stated.`. Agent spot-checks of the v0.2 rules found roughly one false
positive in ten lessons and fewer in near-miss and recovery evidence.

Near-miss recall is deliberately conservative. The model has not been trained on
an ops domain pack. No operational reliability or improvement over the base is
claimed until the held-out report and rubric support it.

## Use constraints (PRD §15)

- ASRS is a confidential voluntary system. Training data on the Hub is already sanitized by NASA, but outputs must not be presented as official NASA/NTSB findings.
- Do not re-identify reporters.
- Do not use Debrief as the authority for flight decisions.
- If the repo is published, include the limitation section verbatim.

Not for operational aviation decisions. Keep adapters private until their
limitations and evaluation have been reviewed.

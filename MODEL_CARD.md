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
# Debrief — debrief-qwen3-8b-asrs-v01

**Status: pipeline implemented; training and acceptance evaluation pending.**

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
- Training method: Unsloth QLoRA, 4-bit base, rank/alpha 16/16, assistant-only loss.
- Actual hardware, effective parameters, losses, wall time and peak VRAM: `eval_runs/train_meta.json`.

## Schema

What happened; What almost happened; Phase of flight; Primary factor;
Contributing factors; Recoverable; Lesson. See `src/schema.py` and `src/prompt.py`.
The system prompt is frozen. The schema instructions in the user message are
identical for base, adapter, training and inference.

## Supervision and limitations

Gold prose uses the first source-checked synopsis sentences. Unsupported known
aircraft types are generalized to aircraft; unsupported role titles to reporter.
A target is rejected for ungrounded numbers/acronyms, less than 50% content-word
overlap, explicit narrator uncertainty, or unsupported airport elevation claims.
The first synopsis sentence must pass; a later sentence cannot replace the main
event. These checks provide weak supervision, not proof of semantic grounding.

Phase and factor classes are mapped from analyst codes. Multiple phases use the
first listed source code, which is not necessarily chronological. `ATC Equipment`
maps to Equipment; explicit controller-clearance attribution can map Human Factors
to ATC. These labels are noisy and may disagree with a reasonable reader.

Recoverability uses deterministic, locally negation-aware intervention and
completed-event patterns. It is not an assessment of how controllable the event
was. Many restored software incidents remain Unknown under the aviation heuristic.
A reported risk is not proof of a completed accident. Unrecognized paraphrases,
passive voice, and distant negation can be misclassified.

The numbers/acronyms grounding check misses semantic hallucinations. Passing it
does not prove truthfulness. Near-miss recall is deliberately conservative and
lessons are often `None stated.` The model has not been trained on an ops domain
pack. No operational reliability or improvement over the base is claimed until
the held-out report and rubric support it.

## Use constraints (PRD §15)

- ASRS is a confidential voluntary system. Training data on the Hub is already sanitized by NASA, but outputs must not be presented as official NASA/NTSB findings.
- Do not re-identify reporters.
- Do not use Debrief as the authority for flight decisions.
- If the repo is published, include the limitation section verbatim.

Not for operational aviation decisions. Keep adapters private until their
limitations and evaluation have been reviewed.

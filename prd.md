# Product Requirements Document

**Product:** Local Incident Brief Model  
**Working name:** BriefCard  
**Version:** 0.1  
**Date:** 2026-09-14  
**Status:** Draft for first implementation  
**Owner:** Chris Cheney  
**Hardware target:** Ubuntu home lab, 1× NVIDIA RTX 3080 Ti 12 GB (Founders Edition)

---

## 1. Summary

Build a locally trained LoRA adapter that turns a messy first-person incident narrative into a structured investigator brief.

The first training domain is NASA Aviation Safety Reporting System (ASRS) near-miss reports. Aviation is the *gym*, not the product. The product is a small on-prem model that performs causal compression: what happened, what almost happened, primary factor, contributing factors, recoverability, and the single lesson — without inventing facts.

After the aviation adapter proves the pipeline, the same schema is retargeted with a small set of personal / software-ops incidents so the model is useful on this machine.

This document covers problem, scope, requirements, data, training, evaluation, serving, risks, and a phased implementation plan sized for a single 12 GB GPU.

---

## 2. Problem

Base instruct models will summarize an incident. They will not reliably *file* one.

Typical failure modes of an untuned 8–12B model on incident text:

- Narrates instead of compressing
- Collapses “what happened” and “what almost happened”
- Picks a single tidy cause and drops contributors
- Invents procedures, altitudes, part names, or intentions not in the source
- Omits uncertainty
- Writes an essay when a card is required

NASA already paid analysts to do this job on ~47k public ASRS reports: a first-person narrative plus a synopsis and coded fields (phase of flight, anomalies, human factors, aircraft, etc.). That is scarce, high-quality supervision for the exact speech act we want.

There is no widely published 8–12B LoRA that maps ASRS narrative → a causal brief schema. Packaged Hub SFT sets (function calling, SQL, Alpaca) optimize for leaderboards, not this skill.

---

## 3. Goals

### 3.1 Primary goals

1. Stand up a repeatable fine-tune pipeline on the 3080 Ti that can be reused for later domains.
2. Train a QLoRA adapter on ASRS that beats the untuned base model on a held-out brief-scoring rubric.
3. Export an adapter that can be loaded locally for inference (Unsloth / transformers, optional GGUF later).
4. Document the data transform so the same schema can be filled from non-aviation incidents.

### 3.2 Secondary goals

5. Demonstrate format transfer: paste a software or home-lab incident and get a valid card (quality may be weak until domain data is added).
6. Add a second, small domain pack (ops / home lab) without collapsing aviation performance.

### 3.3 Non-goals (v0.1)

- Becoming an aviation-safety product or NTSB replacement
- Full-weight fine-tune, DPO, GRPO, or multi-GPU training
- Models above ~14B dense or any 27B+ / Kimi / GLM-5 / DeepSeek V4-class base
- Serving a public API
- Long-context training (8k+)
- Multimodal (cockpit audio, images)
- Replacing RAG over ASRS; this is a generator, not a search index
- Legal advice, official safety findings, or operational use on live aircraft

---

## 4. Users and use cases

| User | Job | v0.1 support |
|---|---|---|
| Builder (you) | Train, eval, iterate the adapter | In scope |
| Local operator (you) | Paste a narrative, get a brief | In scope |
| Later: on-call / postmortem | File a card from a Slack dump or ticket | Schema-compatible; data not in v0.1 |
| Aviation safety reader | Skim ASRS dumps faster | Incidental; not a target market |

**Primary use case:**  
Given a raw incident narrative (ASRS-style or similar prose), return a filled brief in a fixed schema, grounded only in the text.

**Secondary use case:**  
Batch-score a folder of narratives into JSONL for search / clustering later.

---

## 5. Success metrics

Evaluation is on a **held-out ASRS split the model never trains on** (target N = 400). Compare **base Qwen instruct** vs **base + adapter** with identical decoding settings.

### 5.1 Must-hit for v0.1

| Metric | Definition | Target vs base |
|---|---|---|
| Schema validity | Output contains all seven headings, parseable | ≥ 95% valid |
| Primary factor accuracy | Exact match to mapped gold class | +15 pp over base |
| Phase accuracy | Exact match to mapped gold phase (or “unknown” when absent) | +10 pp over base |
| Grounding | Judge or checklist: no entity/number not present in the narrative | Hallucinated specifics ≤ 10% of briefs |
| Recoverable flag | Binary match to derived gold when derivable; else “unknown” | Better than base, no collapse to one label |

### 5.2 Should-hit

| Metric | Target |
|---|---|
| “What almost happened” present and distinct from “what happened” | ≥ 80% of near-miss gold rows |
| Lesson is one sentence, no new facts | Qualitative spot-check 50 rows |
| Token length of brief | Median < 250 tokens |

### 5.3 Pipeline success (independent of model quality)

- One command builds train/eval JSONL from Hugging Face
- One command runs QLoRA to completion without OOM on 12 GB
- Adapter reloads and produces a brief for a fixture narrative
- Train run wall time ≤ 6 hours for the v0.1 data size

### 5.4 Failure of v0.1 (ship blockers)

- Adapter is less schema-valid than a good system prompt on the base model
- Adapter invents more facts than the base
- Training does not finish on the 3080 Ti without heroic hacks
- Eval set leaked into train

---

## 6. Product shape

v0.1 is a **repo + artifact**, not a SaaS.

```
briefcard/
  README.md
  prd.md                          # this document
  configs/train_qwen9b_qlora.yaml
  src/
    build_dataset.py              # ASRS → chat JSONL
    schema.py                     # headings, factor map, parsers
    train_unsloth.py
    eval_briefs.py
    infer.py
  data/
    raw/                          # optional local cache
    processed/train.jsonl
    processed/eval.jsonl
    processed/label_map.json
  adapters/briefcard-asrs-v01/
  eval_runs/
  fixtures/                       # 10 hand-checked narratives
```

**Runtime interface (v0.1):** CLI.

```text
python -m src.infer --adapter adapters/briefcard-asrs-v01 --file story.txt
```

Stdout: the seven-heading brief. Optional `--json` for machine use.

**Out of v0.1:** HTTP server, OpenAI-compatible API, desktop app, Unsloth Desktop wrapper. Those are phase 4+.

---

## 7. Output schema (normative)

Every assistant completion must use exactly these headings, in this order, with a blank line between sections:

```text
What happened:
<1–3 sentences. Only events attested in the narrative.>

What almost happened:
<The near-miss or blast radius. "None stated" if the text is a completed accident with no counterfactual.>

Phase of flight:
<one of the controlled vocabulary below, or Unknown>

Primary factor:
<one of: Human | Procedure | ATC | Weather | Equipment | Other | Unknown>

Contributing factors:
<- bullet list, or "None stated">

Recoverable:
<Yes | No | Unknown>
<optional one-line justification grounded in the text>

Lesson:
<exactly one sentence. No new causal claims.>
```

### 7.1 Controlled vocabularies

**Phase of flight** (map ASRS codes down to this list; drop rare leftovers into Other / Unknown):

- Parked / ramp
- Taxi
- Takeoff
- Climb
- Cruise
- Descent
- Approach
- Landing
- Go-around
- Other
- Unknown

**Primary factor**

| Class | Meaning |
|---|---|
| Human | Perception, memory, fatigue, skill, decision of a flight crew or ground person |
| Procedure | Checklist, SOP, published procedure missing, wrong, or not followed as written |
| ATC | Clearance, frequency, phraseology, traffic call from ATC |
| Weather | Wind, icing, visibility, convective, turbulence as a driver |
| Equipment | Aircraft, avionics, airport lighting/signage, tug, ground gear |
| Other | Security, wildlife, cabin, medical — does not fit above |
| Unknown | Narrative does not support a primary class |

If two classes are equal, pick the one the narrator treats as the triggering failure, and put the rest under contributing.

### 7.2 Grounding rule

The model may **rephrase**. It may not introduce:

- Aircraft types, airports, altitudes, headings, frequencies, or names absent from the narrative
- Regulatory citations not in the narrative
- A “lesson” that assumes a fix the text does not support

Uncertainty is expressed as `Unknown` or `None stated`, not as a guess.

### 7.3 System prompt (frozen for train and infer)

```text
You convert an incident narrative into an investigator brief.
Use only information present in the narrative.
Do not invent facts, numbers, or causes.
If the narrative does not support a field, write Unknown or None stated.
Follow the required headings exactly.
```

Do not change this text between training and evaluation.

---

## 8. Data requirements

### 8.1 Source

| Field | Value |
|---|---|
| Dataset | `elihoole/asrs-aviation-reports` on Hugging Face |
| Scale | ~47,723 reports |
| Gold signals | `Report 1_Narrative` (input); `Report 1.2_Synopsis` + coded metadata (supervision) |
| License | Verify card at download time; treat as U.S. government-sourced public research use |

If the Hub dataset is missing columns, fall back to a direct ASRS public query export and keep a column map in `src/schema.py`.

### 8.2 Transform (the actual dataset)

`build_dataset.py` must:

1. Load the source split.
2. Drop rows with empty or tiny narratives (< 200 characters) or empty synopsis + empty factor codes.
3. Truncate narrative to **1,200 tokens** at the tokenizer used for training (head + tail preferred over head-only if length exceeds cap: first 800 + last 400 tokens).
4. Map coded fields → schema via an explicit, unit-tested dictionary (`label_map.json`).
5. Compose the gold brief:
   - **What happened** / **What almost happened**: derived from synopsis with a deterministic template, not another LLM, for v0.1 gold. (Optional teacher rewrite is phase 3 and must be flagged.)
   - **Phase / primary factor**: from mapped codes.
   - **Contributing factors**: remaining coded anomalies / human factors, de-duplicated, max 5 bullets.
   - **Recoverable**: heuristic in v0.1 (see 8.3), overridable later.
   - **Lesson**: one sentence distilled from synopsis with a template, or “None stated.”
6. Emit OpenAI-style chat JSONL:

```json
{"messages":[
  {"role":"system","content":"<frozen system prompt>"},
  {"role":"user","content":"<narrative>"},
  {"role":"assistant","content":"<gold brief>"}
]}
```

7. Split **by report ID**, not by row hash after shuffle of duplicates:
   - Train: 4,000 rows (v0.1)
   - Eval: 400 rows, no ID overlap
   - Reserve: unused remainder, never touched until a later experiment

8. Write `label_map.json` and a `build_report.md` with drop counts.

### 8.3 Recoverable heuristic (v0.1, documented so we can replace it)

`Yes` if the narrative/synopsis contains a successful intervention pattern (go-around, TCAS RA followed, rejected takeoff, “we stopped,” “we queried ATC,” “we went around”) and no completed collision/CFIT/loss of hull.

`No` if the event completed (ground contact, loss of separation that was not recovered, engine failure that forced off-airport, etc.) per synopsis keywords.

`Unknown` otherwise.

This heuristic will be wrong on a slice of rows. That is acceptable for v0.1 if it is deterministic and tested. Do not hide it.

### 8.4 What we will not do in v0.1 data

- Teacher-model rewriting of all gold briefs (contaminates the task with another model’s style)
- Mixing Glaive / ShareGPT / general instruct data
- Training on the synopsis as the *input*
- Using eval narratives in train

### 8.5 Quality bar for gold

Spot-check **50 random train rows** and **50 eval rows** by hand before the first long train. If > 20% of gold briefs violate the grounding rule or dump synopsis verbatim with no structure, stop and fix the mapper.

---

## 9. Model and training requirements

### 9.1 Base model

**Primary:** Qwen 3.5 9B Instruct or Qwen 3.8 9B Instruct (whichever Unsloth 4-bit build is current and Apache-class).

**Fallback:** Gemma 4 12B Instruct 4-bit, only if Qwen 9B is unavailable.

**Rejected for v0.1:** gpt-oss-20b (14 GB QLoRA floor vs 12 GB card), 27B dense, full LoRA in BF16.

Load Unsloth 4-bit (`*-bnb-4bit`) weights.

### 9.2 Method

| Knob | v0.1 value |
|---|---|
| Method | Unsloth QLoRA |
| Rank / alpha | 16 / 16 |
| Targets | q, k, v, o, gate, up, down |
| Dropout | 0 |
| Bias | none |
| Max seq length | 2048 |
| Per-device batch | 1 |
| Grad accum | 8 |
| Effective batch | 8 |
| LR | 2e-4 |
| Scheduler | cosine |
| Warmup | 5% |
| Epochs | 2 |
| Precision | 4-bit base, LoRA in bf16 if the 3080 Ti driver stack supports it; else fp16 |
| Gradient checkpointing | on |
| Packing | off for v0.1 (simpler eval of length) |

If OOM: seq 1536, then rank 8, then disable unused target modules (`gate/up/down` last).

### 9.3 Hardware / process constraints

- Exclusive GPU during train. Stop Whisper, Coolify inference, GitHub runners that pin the 3080 Ti.
- Train in a dedicated Docker image or venv; do not contaminate the inference stack.
- Checkpoint every epoch to disk. Keep last 2.
- Log train loss, eval loss, and learning rate.

### 9.4 Expected cost

- Disk: ~20 GB for 4-bit base + tokenizer + processed data + adapter
- Time: 2–5 hours for 4k × 2 epochs at seq 2048 batch 1 on 3080 Ti (measure; do not treat as SLA)
- Adapter size: hundreds of MB, not tens of GB

---

## 10. Evaluation requirements

`eval_briefs.py` runs three layers.

### 10.1 Automatic

- Parse headings
- Vocab check for phase, factor, recoverable
- Exact match vs gold for phase, factor, recoverable
- Brief length
- Simple grounding: numbers and ALL-CAPS callsigns/airport-like tokens in the output must appear in the input (imperfect, useful)

### 10.2 Rubric (20-row deep dive + any failure cluster)

Score 0–2 each:

1. Grounded (no invented specifics)
2. Happened vs almost-happened split
3. Factor class reasonable even if not exact
4. Lesson is one grounded sentence

Two humans are not required for v0.1; one pass by the builder is enough if notes are kept in `eval_runs/`.

### 10.3 Baseline

Always report **base model + same system prompt + same decoding**. If the adapter does not beat that baseline on schema validity and factor accuracy, the train is not a win.

### 10.4 Decoding for eval and demo

- temperature 0.2
- max new tokens 400
- no system-prompt drift

---

## 11. Inference requirements

- Load base 4-bit + adapter
- Single narrative in, brief out
- Fixture file `fixtures/dark_tug.txt` (the dark RJ-on-tug ASRS-style story) must produce all headings
- Optional JSON mode matching:

```json
{
  "what_happened": "...",
  "what_almost_happened": "...",
  "phase_of_flight": "...",
  "primary_factor": "...",
  "contributing_factors": ["..."],
  "recoverable": "Yes|No|Unknown",
  "recoverable_note": "...",
  "lesson": "..."
}
```

v0.1 does not require an OpenAI tool-call wrapper.

---

## 12. Functional requirements

| ID | Requirement | Priority |
|---|---|---|
| F1 | Dataset builder produces train/eval JSONL and a drop-count report | P0 |
| F2 | Label maps are data, not tribal knowledge; unit-tested | P0 |
| F3 | Trainer runs QLoRA on 12 GB without manual notebook clicks | P0 |
| F4 | Eval script prints base vs adapter table | P0 |
| F5 | Infer CLI prints a valid brief for fixtures | P0 |
| F6 | README documents GPU exclusivity and exact model ID used | P0 |
| F7 | `--json` infer output | P1 |
| F8 | Batch infer over a `.jsonl` of narratives | P1 |
| F9 | Domain pack #2 (ops incidents) builder with the same schema | P2 |
| F10 | GGUF / llama.cpp export | P2 |
| F11 | Merge adapter into standalone weights | P2 |

---

## 13. Non-functional requirements

| ID | Requirement |
|---|---|
| N1 | Train must be restartable from last epoch checkpoint |
| N2 | No training data committed to git; `data/processed` is gitignored except a 10-row sample |
| N3 | Model card lists source dataset, schema, heuristic limitations, “not for operational aviation decisions” |
| N4 | Wall-clock and peak VRAM recorded in `eval_runs/train_meta.json` |
| N5 | Deterministic dataset split (`seed=42`, split by ID) |

---

## 14. Risks and mitigations

| Risk | Mitigation |
|---|---|
| 12 GB OOM | Short seq, batch 1, Unsloth only; fallback Gemma/Qwen smaller if needed |
| Gold briefs are just dumped synopses | Hand-check 100 rows; tighten templates before train |
| Recoverable heuristic is noisy | Keep field but down-weight it in “must-hit” if noisy; fix in v0.2 |
| Model memorizes ASRS style and fails on software incidents | Expected in v0.1; domain pack is v0.2 |
| Adapter makes model *more* hallucinatory | Grounding metric is a ship blocker |
| Hub dataset schema drift | Column adapter in `schema.py`; pin dataset revision |
| GPU contention with Whisper / runners | Document a “train mode” that stops those containers |
| License / attribution miss | Record dataset card license in the model card before any share |

---

## 15. Ethics and use constraints

- ASRS is a confidential voluntary system. Training data on the Hub is already sanitized by NASA, but outputs must not be presented as official NASA/NTSB findings.
- Do not re-identify reporters.
- Do not use BriefCard as the authority for flight decisions.
- If the repo is published, include the limitation section verbatim.

---

## 16. Milestones

| Milestone | Meaning | Exit |
|---|---|---|
| M0 | Repo + schema + 10 fixtures | Fixtures parse |
| M1 | 4.4k JSONL built, 100 rows hand-checked | Check notes committed |
| M2 | Train completes on 3080 Ti | `train_meta.json` exists |
| M3 | Eval table beats base on P0 metrics | Written eval report |
| M4 | Infer CLI usable on new text | Demo on 3 unseen narratives |
| M5 (optional) | 100–200 ops-domain rows mixed or as a second adapter | Transfer spot-check |

---

# Implementation plan

## Phase 0 — Repo and environment (half evening)

**Outcome:** Empty train command would have a place to live.

1. Create `briefcard` repo. Python 3.11+, `uv` or venv.
2. Pin:
   - `unsloth` current
   - `transformers` / `peft` / `trl` versions Unsloth documents
   - `datasets`, `accelerate`, `bitsandbytes`
3. Docker optional but preferred on the lab box so Coolify apps are untouched.
4. Confirm GPU: `nvidia-smi`, 12 GB visible, no other process > 100 MB VRAM.
5. Download the 4-bit base once; record the exact Hub revision.

**Done when:** `python -c "import torch; print(torch.cuda.get_device_properties(0).total_mem)"` and Unsloth import succeed.

## Phase 1 — Schema and dataset builder (one evening)

**Outcome:** `data/processed/train.jsonl` and `eval.jsonl`.

1. Inspect one raw ASRS row; list actual column names (they are awkward).
2. Implement `schema.py`:
   - heading constants
   - phase map
   - factor map
   - recoverable heuristic
   - parser for model output
3. Unit tests for maps with 15 fixture rows (including missing fields).
4. Implement `build_dataset.py`:
   - pin dataset revision
   - filters, truncate, maps, split by ID
   - write `build_report.md`
5. Hand-label notes for 50 train + 50 eval in a spreadsheet or markdown table. Fix the worst mapping bugs.

**Done when:** 4,000 / 400 files exist, IDs disjoint, 100-row review notes stored.

**Explicit non-work:** no training yet. A bad mapper wastes the GPU night.

## Phase 2 — Dry-run train (1–2 hours)

**Outcome:** Proof the 3080 Ti can take a step.

1. 100-row subset, 50 steps, seq 2048, batch 1.
2. Watch VRAM. If peak ≥ 11.5 GB, cut seq to 1536 before the real run.
3. Confirm checkpoints write and reload.

**Done when:** 50 steps finish, VRAM budget known.

## Phase 3 — v0.1 train (one night)

**Outcome:** `adapters/briefcard-asrs-v01`.

1. Stop competing GPU jobs.
2. Full 4k × 2 epochs with config in `configs/train_qwen9b_qlora.yaml`.
3. Write `eval_runs/train_meta.json` (VRAM peak, hours, git commit, model id, dataset revision, seed).
4. Do not peek at eval narratives during training.

**Done when:** adapter files exist and train loss is finite (loss number is not a success metric by itself).

## Phase 4 — Eval and decide (half evening)

**Outcome:** Keep, tweak data, or kill the approach.

1. Run `eval_briefs.py` on 400 eval rows for base and adapter.
2. Produce a markdown table: validity, factor, phase, recoverable, length, grounding heuristic.
3. Read 20 random adapter outputs and 10 worst grounding failures.
4. Decision rule:
   - **Ship locally** if P0 metrics beat base and grounding is not worse.
   - **Fix data / train 1 more epoch** if schema is good but factor accuracy is flat.
   - **Stop** if grounding got worse. Do not stack DPO on a liar.

**Done when:** `eval_runs/v01.md` exists with the call.

## Phase 5 — Infer polish (short)

1. `infer.py` CLI + `--json`.
2. README: how to run, GPU warning, limitation text.
3. Three demo narratives: one ASRS-like, one software outage, one ambiguous one-liner (must say Unknown, not invent).

## Phase 6 — Domain pack (optional, after it works)

1. Write 100–200 ops incidents in the *same* schema (Coolify, Docker, OOM, agent loop, bad spec).
2. Either:
   - **Adapter B** trained only on ops rows from the aviation adapter as start, or
   - Mix 10:1 ASRS:ops and accept some aviation regression.
3. Eval both domains separately.

Do not start phase 6 until phase 4 is a keep.

---

## Suggested calendar

Assuming evenings only:

| Session | Work |
|---|---|
| 1 | Phase 0 + start Phase 1 inspection |
| 2 | Finish builder + 100-row review |
| 3 | Dry-run train |
| 4 | Full train (can run unattended) |
| 5 | Eval + infer CLI |

Five sessions to a real artifact. Dataset quality in session 2 determines whether session 4 is wasted.

---

## Work breakdown (checklist)

### P0

- [ ] Repo skeleton and gitignore for `data/` and `adapters/`
- [ ] Frozen system prompt constant
- [ ] Column inventory of `elihoole/asrs-aviation-reports`
- [ ] Phase and factor maps with tests
- [ ] Recoverable heuristic with tests
- [ ] Dataset builder + split-by-ID
- [ ] 100-row manual review
- [ ] Unsloth train script + yaml
- [ ] 50-step dry run on GPU
- [ ] Full 4k train
- [ ] Base vs adapter eval table
- [ ] Infer CLI + fixture
- [ ] Model card limitations

### P1

- [ ] `--json` and batch infer
- [ ] Grounding token-overlap metric
- [ ] Plot of loss (even a text dump)

### P2

- [ ] Ops-domain pack
- [ ] GGUF export
- [ ] Second eval set of non-aviation incidents (hand-made, ~30)

---

## Technical notes for the builder

### Why gold is templated, not teacher-written

v0.1 is testing whether the *model* can learn the schema from deterministic targets. If a frontier model writes the gold, you mostly distill that model’s voice and cannot debug mapper errors. Teacher rewrite is allowed later, as a labeled experiment, not as the default.

### Why 4k rows, not 40k

12 GB and two epochs. 4k short-to-medium chats is enough to learn headings and factor vocabulary. More rows help factor accuracy only after the mapper is trustworthy. Expanding is a config change, not a new project.

### Why not DPO yet

Preference data needs a definition of “better brief.” That definition is the eval rubric. Collect rejected/chosen pairs from eval failures in v0.2 if SFT plateaus.

### Why Qwen 9B not gpt-oss-20b

Unsloth lists gpt-oss-20b QLoRA at ~14 GB. This machine has 12 GB. A first train that OOMs teaches nothing about the task.

---

## Open questions (resolve only if they block M1)

1. Exact column names in the current Hub snapshot vs the 2022 card.
2. Whether Unsloth’s current Qwen 3.8 9B 4-bit tag exists or we pin 3.5 9B.
3. Whether synopsis-derived “what almost happened” is too often empty; if so, add a small keyword near-miss detector for gold only.
4. Publish adapter or keep private. Default: private until the limitation card is written.

None of these block Phase 0.

---

## Appendix A — Example gold brief

**User (abridged):**  
While taxiing a B757 from gate to hangar we were cleared via A-T to join the runway. Near T1 we caught up to a dark, apparently unpowered company ERJ-145 on a towbarless tug with no external lighting.

**Assistant:**

What happened:  
A B757 taxiing to the hangar overtook a company ERJ-145 being towed dark, with no external lighting visible until the 757 was close.

What almost happened:  
A ground collision on the taxiway with an unlit aircraft in tow.

Phase of flight:  
Taxi

Primary factor:  
Equipment

Contributing factors:  
- Unlit aircraft being towed  
- Tow operation on an active taxi routing  
- Recognition delayed until close range  

Recoverable:  
Yes  
Crew saw the dark aircraft in time to avoid contact.

Lesson:  
Towed aircraft need conspicuous lighting whenever they share taxi routes with powered traffic.

---

## Appendix B — Eval table template

```text
run_id:
base_model:
adapter:
n_eval:

             base    adapter
valid_schema
factor_acc
phase_acc
recoverable_acc
grounding_fail
median_tokens
```

Fill this before calling v0.1 done.

---

## Appendix C — Stop conditions

Stop the project if:

- After one honest data pass and one train, the adapter loses to the system-prompted base on factor accuracy *and* grounding
- The 3080 Ti cannot complete 50 training steps at seq 1536 rank 8
- The Hub source cannot yield 2k clean rows

Then either switch the *source* (NHTSA complaints with the same schema) or drop the product, do not add more frameworks.

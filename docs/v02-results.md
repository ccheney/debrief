# v0.2 results — `debrief-qwen3-8b-asrs-v02`

Reviewer: Claude (agent review of the automatic report and the rubric packet), 2026-09-16.
Decision under PRD §Phase 4: **ship locally as an experimental adapter**. All nine
automatic gates pass and grounding is better than the base under a stricter
check; the rubric read finds the residual errors below. This is not a human
sign-off and the adapter stays private.

## Run

| Item | Value |
|---|---|
| Base | `unsloth/Qwen3-8B-unsloth-bnb-4bit@62efd7f9d748e394734a7adae2adf96e13a2abc8`, unchanged from v0.1 |
| Data | 4,000 train rows plus 222 near-miss copies, 400 held-out, seed 42, label map 4 |
| Review gate | 100-row agent review, 14/100 PRD §7.2 violations, `docs/gold-review-v02.md` |
| Training | 1,056 optimizer steps, 2 epochs, 5,998 s, peak reserved VRAM 8.74 GiB |
| Loss | 2.89 → 0.41 (train), 0.38 on the 32-row training probe; no spikes |
| Full run | 2 h 50 min wall including the 400-row paired evaluation and three demos |
| Provenance | `eval_runs/asrs-v02_meta.json`, `eval_runs/v02_metrics.json`, adapter sha256 `2d4895ee0f6a…` |

The run recorded commit `41b07a5` with a dirty flag: the review commit could not
be deployed while a synced file was modified, and the checkout was cleaned after
launch. The code hashes recorded are identical to the launched commit.

## Held-out metrics (`eval_runs/v02.md`)

Different held-out rows, gold rules and scorer from v0.1 (the base is re-run
each time), so v0.1 numbers are context, not a paired comparison.

| Metric | v0.1 base | v0.1 adapter | v0.2 base | v0.2 adapter | Gate |
|---|---:|---:|---:|---:|---|
| Valid schema | 0.565 | 1.000 | 0.550 | **1.000** | pass |
| Primary factor accuracy | 0.328 | 0.698 | 0.320 | **0.733** | pass (+41 pp) |
| Phase accuracy | 0.323 | 0.767 | 0.340 | **0.805** | pass (+47 pp) |
| Recoverable accuracy, all rows | 0.050 | 0.935 | 0.117 | 0.833 | — |
| Recoverable accuracy, derivable rows | 0.581 (31) | 0.226 (31) | 0.431 (109) | **0.514** (109) | pass (improves) |
| Predicts both Yes and No | yes | never No | yes | **Yes 52, No 8** | pass |
| Grounding flags | 0.030 | 0.005 | 0.062 | **0.033** | pass (stricter check, see below) |
| Median tokens | 171 | 59 | 171 | 64 | should-hit met |
| Near-miss distinct, gold rows | 0.222 (9) | 0.556 (9) | 0.182 (11) | 0.545 (11) | should-hit 0.80 not met |
| Lesson recall, gold-lesson rows | — | 0 (never emitted) | 0.667 (75) | **0.613** (75) | reported |
| Lesson emitted, all rows | — | 0.000 | 0.395 | 0.177 | reported |
| Emitted lessons lexically grounded | — | — | 0.133 | **1.000** | reported |

Grounding flags now include the event-class check (a brief may not assert
"engine failure", "loss of separation", "near miss" and 25 similar classes the
narrative never mentions). The adapter is flagged on 13 rows: 11 event-class
assertions and 2 acronyms. The base is flagged on 25.

## What the adapter does now

- **Lessons.** Emits a lesson on 71 of 400 rows; 69 are verbatim narrative
  sentences and all 71 pass the lexical "no new facts" check. It matches the
  gold lesson exactly on 35 of 75 gold rows and emits some lesson on 46 of them.
  The 25 lessons emitted where the extractive gold had none are, in the 50-row
  packet, genuine recommendations the rule missed ("JAX Center/Tampa Approach
  needs to consider a better airspace management plan…"). v0.1 emitted none.
- **Recovery.** Answers Yes on 63 rows and No on 11, with a verbatim evidence
  line on every one of the 74. On derivable rows: gold Yes 86 → Yes 49, Unknown
  36, No 1; gold No 23 → No 7, Unknown 13, Yes 3. It is conservative rather
  than wrong: 13 of 23 completed events still get Unknown.
- **Near miss.** Present on 12 rows: 6 of the 11 gold rows (5 verbatim
  matches) and 6 where gold had none, of which four are real near-miss
  statements the gold rule missed (a taxiway near collision the 60-word cap
  excluded, traffic 50–100 feet below).
- **Classification.** Phase per class is 75–87% except Descent (62%) and the
  rare Unknown/Other. Factor: Equipment 94%, Weather 86%, Human 74%, Procedure
  35%, Unknown 19%; ATC is never predicted (0.2% of gold).
- **Demos.** All three fixtures now behave as the PRD asked.

| Fixture | v0.1 | v0.2 | Gold |
|---|---|---|---|
| go_around | Approach / Human / Unknown / no lesson | Approach / Human / **Yes** with evidence / **"We should abandon an unstable approach."** | Approach / Weather / Yes / same lesson |
| docker_oom | Unknown / Human / Unknown / no lesson | Unknown / **Procedure** / Unknown / **"We should measure memory use under load before setting the limit."** | Unknown / Procedure / Yes / "Measure memory use…" |
| ambiguous | Parked / Equipment / Unknown / no lesson | **Unknown / Unknown / Unknown** / no lesson | same |

## Rubric review (20 random rows + 10 lexical grounding failures)

Scores 0–2 for grounding of "What happened", near-miss handling, primary
factor and lesson handling, from `eval_runs/v02_rubric.md` against the full
narratives. The first twenty are the random sample.

| Report | Ground | Near miss | Factor | Lesson | Note |
|---|---|---|---|---|---|
| 1477738 | 2 | 2 | 2 | 2 | Accurate; fatigue contributor attested; closing advice has no modal, none extracted |
| 1664243 | 2 | 1 | 2 | 2 | Accurate; RA followed and go-around should give recovery Yes, got Unknown |
| 1283705 | 2 | 2 | 2 | 2 | Accurate; return and landing not reflected in recovery |
| 1684237 | 2 | 2 | 2 | 2 | The "we should be advised by ATC" lesson v0.1 missed is extracted verbatim |
| 1438631 | 0 | 2 | 2 | 2 | **"diverting to an alternate airport" invented**: the crew considered it, continued and climbed back to FL370 |
| 1211218 | 2 | 1 | 2 | 1 | Explicit counterfactual and "should not have been released" recommendation both missed |
| 1696265 | 0 | 2 | 2 | 2 | **"The Captain reported"**: the reporter is the dispatcher; lesson is the reporter's own second recommendation |
| 1198535 | 2 | 2 | 1 | 2 | Prop contact with terrain should give recovery No; factor Equipment for a surface depression |
| 1095615 | 2 | 2 | 2 | 2 | Narrator is the Captain; "In the future; I; The Captain; will ask more questions…" extracted |
| 1802781 | 2 | 2 | 1 | 2 | Near-miss sentence found although the gold rule missed it; controller error labeled Human, not ATC |
| 1690252 | 2 | 2 | 2 | 2 | Accurate; miscommunication contributor and lesson attested |
| 1124106 | 2 | 2 | 2 | 2 | Recovery Yes via go-around despite a bent prop; matches gold, debatable |
| 1817781 | 1 | 2 | 2 | 2 | "taxiway incursion" for lining up on the runway on another aircraft's clearance |
| 1781084 | 2 | 2 | 2 | 2 | Accurate |
| 1805583 | 2 | 2 | 1 | 2 | "ATC needs to better separate aircraft" extracted; factor Procedure where ATC fits |
| 1005649 | 2 | 2 | 1 | 0 | Policy concern, no flight event; "I would recommend either changing the title back…" missed |
| 1758212 | 2 | 2 | 2 | 2 | "engine reverser malfunction", not the "engine failure" v0.1's gold asserted |
| 1147935 | 1 | 2 | 2 | 2 | "a ground reporter alerted them" is the role-generalization artifact (see below) |
| 1367958 | 2 | 2 | 2 | 1 | Recovery Yes with verbatim evidence; "Fly The Airplane" advice has no modal |
| 1679760 | 2 | 2 | 2 | 2 | Accurate; diversion not reflected in recovery |
| 1182343 | 1 | 1 | 1 | 2 | "light transport aircraft" for a Cirrus; explicit RA and 400 ft pass not surfaced as the near miss |
| 1323946 | 2 | 2 | 2 | 1 | Accurate; "I would ban the batteries" starts with "If it were up to me", missed |
| 1009096 | 2 | 2 | 2 | 2 | Flameout stated as engine failure, attested |
| 999793 | 1 | 2 | 2 | 2 | "engine failure" compresses a lost cowling and jammed thrust lever; lesson extracted |
| 1816751 | 0 | 2 | 2 | 2 | **"loss of separation event" invented** (caught by the event-class check); "We need more staffing." extracted |
| 1120658 | 2 | 2 | 2 | 2 | Accurate; lesson extracted |
| 1452545 | 0 | 2 | 2 | 2 | **"critical engine failure"** for bleed failures (caught by the event-class check) |
| 1038734 | 0 | 2 | 2 | 2 | **"loss of separation event" invented** (caught); "Tower reporter" artifact |
| 1272489 | 2 | 1 | 2 | 2 | Explicit "his tail would have hit my winglet" counterfactual missed |
| 1010910 | 2 | 2 | 2 | 2 | Accurate |

On the twenty random rows: 16 clean, 2 partial, 2 wrong (v0.1: 14, 4, 4 of 22).
Three of the five wrong rows overall are the lexical failures the new
event-class check already flags. The two it cannot see are an invented outcome
(a diversion that did not happen) and a report attributed to the wrong role.
Every emitted lesson in the packet (9) is a verbatim, genuine recommendation;
four explicit recommendations were missed, mostly ones without a modal verb.

## Known artifacts and limitations

- **"Tower reporter", "Maintenance reporter".** The v0.2 role generalization
  replaces header roles with "reporter" but keeps the modifier, so 107 of 4,222
  training cards read "<modifier> reporter" and the adapter reproduces it on 16
  of 400 rows. Cosmetic, fix in v0.3 by dropping the modifier or using a common
  noun ("the controller").
- **Synopsis voice.** 374 of 400 briefs use "reported"; the model summarizes in
  the analyst's voice and still classifies events with taxonomy terms. The
  event-class check catches the listed classes only.
- **Conservative recovery and near miss.** Recall is 57% on gold Yes, 30% on
  gold No, 6 of 11 on near misses. The should-hit near-miss target (80%) is not
  met on 11 rows.
- **ATC never predicted.** 0.2% of gold; controller-attributed events land in
  Human or Procedure.
- **Semantic errors survive.** About one brief in ten asserts something the
  narrative does not support in a way no lexical check sees.

## Suggested v0.3

Data: drop the modifier when generalizing roles; widen the near-miss rule for
"prior to colliding", "passed below us by", "converging traffic"; consider
oversampling derivable-recovery rows; revisit whether the ATC class is
learnable from this source. Evaluation: add a semantic grounding judge as a
labeled experiment, separate from the lexical gates. Product: the ops domain
pack (PRD Phase 6) is now unblocked by the Phase 4 keep decision.

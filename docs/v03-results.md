# v0.3 results — `debrief-qwen3-8b-asrs-v03`

Reviewer: Claude (agent review of the automatic report and the 29-row rubric packet), 2026-09-16.
Decision under PRD §Phase 4: **ship locally as the current experimental adapter.**
All nine automatic gates pass. Recovery, the weakest field in v0.1 and v0.2,
improves materially. Grounding does not improve. Not a human sign-off; the
adapter stays private.

## Run

| Item | Value |
|---|---|
| Base | `unsloth/Qwen3-8B-unsloth-bnb-4bit@62efd7f9d748e394734a7adae2adf96e13a2abc8`, unchanged since v0.1 |
| Data | 4,000 train rows plus 718 oversampled copies, 400 held-out, seed 42, label map 4 plus four synopsis checks |
| Review gate | 100-row agent review, 16/100 PRD §7.2 violations, `docs/gold-review-v03.md` |
| Training | 1,180 optimizer steps, 2 epochs, 6,733 s, peak reserved VRAM 8.39 GiB |
| Loss | 2.92 → 0.31 (train), 0.34 on the 32-row training probe; no spikes |
| Full run | 3 h 5 min wall including the 400-row paired evaluation and three demos |
| Provenance | `eval_runs/asrs-v03_meta.json`, commit `0729037`, clean tree, adapter sha256 `f0d5220e7644…` |

## Held-out metrics (`eval_runs/v03.md`)

Every version draws a new held-out split from its own build, and the base is
re-run each time, so the gap over base is the comparable quantity, not the
absolute adapter number.

| Metric | v0.2 base | v0.2 adapter | v0.3 base | v0.3 adapter | v0.2 gap | v0.3 gap |
|---|---:|---:|---:|---:|---:|---:|
| Valid schema | 0.550 | 1.000 | 0.550 | 1.000 | +0.450 | +0.450 |
| Primary factor accuracy | 0.320 | 0.733 | 0.310 | 0.695 | +0.413 | +0.385 |
| Phase accuracy | 0.340 | 0.805 | 0.320 | 0.777 | +0.465 | +0.457 |
| Recovery accuracy, derivable rows | 0.431 | 0.514 | 0.355 | 0.582 | +0.083 | **+0.227** |
| Grounding flags | 0.062 | 0.033 | 0.045 | 0.025 | −0.030 | −0.020 |
| Near-miss distinct | 0.182 | 0.545 | 0.429 | 0.643 | +0.364 | +0.214 |
| Lesson recall | 0.667 | 0.613 | 0.613 | 0.570 | −0.053 | −0.043 |
| Emitted lessons lexically grounded | 0.133 | 1.000 | 0.171 | 1.000 | +0.867 | +0.829 |
| Median tokens | 171 | 64 | 168 | 65 | −107 | −103 |

Recovery scored on 110 derivable rows, near miss on 14, lesson recall on 93.
The v0.3 grounding check is stricter than v0.2's: it adds named taxiway, runway
and gate designators to the numbers, acronyms and event-class categories.

## What the oversampling did

Completed-event rows were written three times in the training split, taking
"No" from 6% to 16% of written rows against a true held-out rate of 8%.

| | v0.2 | v0.3 |
|---|---:|---:|
| "No" predicted | 11 | 31 |
| "No" in gold | 23 | 32 |
| "No" recall | 30% | 56% |
| "No" precision against gold | 64% | 58% |
| "Yes" recall / precision | 57% / — | 59% / 74% |
| Evidence lines verbatim | 74/74 | 93/93 |

It did not run away: 31 predicted against 32 in gold. Precision against gold is
58%, but that number is misleading. Of the 13 "No" predictions gold disagrees
with, 8 are rows where gold says Unknown and the narrative plainly describes a
completed outcome the heuristic missed ("struck a construction berm ... damaged
the nose and left gear", "damage to the wall of the hangar", "drifted onto
grassy area and I had to pull the EM/PARK BRAKE"). On those the model is more
right than its own labels. The genuinely wrong ones are about five, the clearest
being report 1082786, where the left main gear eventually extended and the
aircraft landed uneventfully but the adapter answered No.

## Rubric review (20 random rows plus grounding failures, 29 total)

Scoring "What happened" for grounding, on the 20 random rows:

| | v0.2 | v0.3 |
|---|---:|---:|
| Clean | 16 | 12 |
| Partial | 2 | 5 |
| Wrong | 2 | 3 |

Grounding did not improve, and on this sample it looks slightly worse. With 20
rows a four-row difference is inside sampling noise, so the honest reading is
"no measurable grounding change", not "a regression". Across all 29 rubric rows:
16 clean, 8 partial, 5 wrong.

The wrong ones are semantic, and every one of them passes the lexical checks
because the narrative contains the trigger words:

- **1030597** "reported a loss of separation event" when the controller wrote "[I] vectored the A320 off to the right **to avoid** loss of separation".
- **1476363** "near miss with a King Air in restricted airspace" when the narrator turned to avoid the restricted area, did avoid it, and had visual separation throughout.
- **1298759** "turbulence in cruise caused injuries to Flight Attendants" when the narrative describes the *risk* of injury, not injuries.
- **1053870** "engine failure on takeoff" for a fuel-control fault that appeared passing 20,000 ft.
- **1751463** "near miss with terrain" when the narrative describes coming within 200 feet of Class B airspace laterally.

Partial rows cluster on the same overstatement habit: "loss of separation" for a
spacing issue (1677425), "engine failure" for a precautionary shutdown (1249384),
"taxiway incursion" for an aircraft stopped on a runway (1011612).

Direct wins over v0.2 visible in the packet: report 1469826 is summarized
correctly as "a near miss with a regional airliner at 10,500 ft" where v0.2's
gold invented "vintage military aircraft"; lessons are extracted verbatim and
correctly withheld where the narrator explicitly declines to recommend anything
(1190020).

## Demos

| Fixture | v0.3 | Gold |
|---|---|---|
| go_around | Approach / **Weather** / Yes with evidence / "We should abandon an unstable approach." | Approach / Weather / Yes / same lesson |
| docker_oom | Unknown / Procedure / Unknown / "We should measure memory use under load before setting the limit." | Unknown / Procedure / Yes / same lesson |
| ambiguous | Unknown / Unknown / Unknown / None stated | same |

The go-around fixture now gets Weather, matching gold; v0.2 answered Human.

## Artifacts and limitations

- **Role modifier fixed.** "Tower reporter" style output fell from 16 of 400 to **0**.
- **New residue found.** Aircraft-type generalization leaves a model suffix behind: "Aircraft MAX reporter", "Aircraft 737-800 reporter". 29 training cards and 2 of 400 briefs. Same fix shape as the modifier: consume the suffix when generalizing the type.
- **Overstatement is the dominant remaining error.** The model reaches for ASRS taxonomy terms ("loss of separation", "engine failure", "near miss") that are one step stronger than the narrative supports. The event-class check only fires when the trigger word is absent from the narrative, and in these cases it is present.
- **Recall still conservative.** Recovery answers Unknown on 29 of 78 gold Yes rows and 14 of 32 gold No rows; near miss is present on 9 of 14; lessons on 53 of 93.
- **Procedure and Unknown factors remain weak**: 36% and 19%, with 29 Procedure rows predicted as Human. ATC is still never predicted.
- **Descent phase** is the weakest at 52%, confused with Cruise and Approach.

## Suggested v0.4

The fixable items are small: consume the type suffix in role generalization, and
widen the lesson rule to imperatives with an explicit lead-in, which the rubric
shows being missed on at least four rows ("Corporate pilots need to pay attention
and follow ATC instructions", "Add a note to the 10-7 page").

The structural item is not small, and it now bounds two separate numbers. Both
the gold review floor (16 of 100 rows violating the grounding rule, unchanged
across four passes of rule tightening) and the adapter's overstatement habit come
from the same source: the ASRS synopsis is written against the full report, so it
carries blame, places and event classes the narrative field does not contain, and
the model learns that voice. Lexical filtering cannot reach it. The next real
move is the PRD's deferred experiment, a labeled teacher rewrite or an
extractive-only "What happened", evaluated against the same gates so the change
is measurable rather than assumed.

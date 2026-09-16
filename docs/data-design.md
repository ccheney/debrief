# Data decisions

The 2022 ASRS Hub train split contains 38,655 rows, not the full 47,723 total
across all upstream splits. We draw the experiment solely from this pinned train
source and make a new independent 4,000/400 split.

The original synopsis can include facts absent from `Report 1_Narrative`. For
example, report 1574675's synopsis names a B737-700 even though its narrative does
not. Copying that synopsis would train the model to invent an aircraft type.

The mapper uses up to two synopsis sentences only when the first sentence passes
source checks. It generalizes unsupported known aircraft types and role titles,
rejects new numbers/acronyms and explicit uncertainty, and requires at least 50%
content-word overlap. A later sentence cannot replace a rejected central event.
The earlier extractive fallback was removed after review found it selected
setup details and hypotheticals. This retains analyst compression but filters
aggressively; the checks remain weak supervision and require review. Contributors require both a source code and an attested
phrase. Recommendations are copied only from short explicit recommendations beginning
with a speaker and should/need to/must, or set
to `None stated.` Near misses require explicit counterfactual wording; absent
counterfactuals stay `None stated`.

Phase and primary factor remain coded weak labels. Every observed primary problem
has an explicit mapping; unknown new factor codes become Unknown. Unmapped phase
codes become Other; missing phases become Unknown. Multi-phase values retain the
first listed source code. This rule is deterministic, not a causal inference.

Recovery is computed on the actual truncated narrative, not hidden synopsis text.
Completed collision/contact patterns take precedence over later stopping;
intervention patterns count only when not locally negated. These rules cannot
cover all natural language and must be replaced by reviewed labels in a later
experiment. Unit tests include negated accidents, avoided collisions and
completed accidents after intervention.

The five-line system prompt remains verbatim. Both base and adapter also receive
the schema in their user message so the baseline is not disadvantaged by having
to guess the required headings. This format instruction is identical at training
and inference. It never includes gold fields or synopsis metadata.

Training-time loss probes use 32 training rows. They are labeled as such and
never substituted for the held-out base-vs-adapter benchmark.

Review packets are generated separately. Automated lexical checks and an agent's
review are not represented as a human review. Acceptance notes must name the
reviewer and explicitly retain this distinction.

Human Factors reports map to ATC only for explicit controller attribution, or a known controller function together with explicit first-person error wording. A controller merely reporting a pilot error stays Human.

The frozen 100-row agent review is in [gold-review.md](gold-review.md). It is not a human sign-off. The trainer checks its dataset hashes before a full run.

## v0.2 (label map version 4)

The v0.1 adapter learned the empty priors of three fields (lesson 97.5%,
near miss 98.6%, recovery Unknown 92% of training gold) and never emitted a
lesson on the held-out set. v0.2 changes the gold rules only; the prompt, base,
split procedure and hyperparameters are unchanged.

- **Lesson.** The last narrative sentence that is an explicit reporter
  recommendation: a subject plus should/need to/must/ought to, a passive
  "should be", "I recommend/suggest", or a lead-in such as "In the future I
  will", "Next time", "Lessons learned", "Do not/Never/Always". Sentences with
  a reporting or decision verb before the modal ("Tower said we should",
  "we determined that … should"), comparisons ("higher than we should have
  been"), inverted conditionals, questions, anaphoric openers and sentences
  under five or over thirty-five words are excluded. Enumerators left by the
  sentence splitter are stripped. Coverage rose from 2.5% to 22% of training
  rows; an agent spot-check of 65 extracted lessons found about one in ten to
  be narration rather than a takeaway.
- **Near miss.** Explicit near-miss phrases, "almost/nearly" plus a collision
  verb, "close call", "came (too) close to", "narrowly missed", evasive action,
  and counterfactuals whose consequence is an accident class ("could have
  resulted in a collision", "would have been a disaster"). Local negation is
  respected ("at no time was there a near miss"). Coverage rose from 1.4% to
  2.8%; because that is still rare, rows with a stated near miss are written
  three times in the training split only.
- **Recovery.** Completed outcomes now include damage, injuries, excursions,
  ground loops, wingtip and prop strikes and off-field landings; successful
  interventions now include first-person singular forms, progressive
  wording ("rejecting the takeoff"), "went missed", return or diversion, and
  landing safely or without incident. "Exited/departed the runway" and
  "contacted ground" are normal operations and are not matched. Negation
  context adds "neither/nobody/none", "if/whether/any", concern and inspection
  wording and "rather than". Known-outcome rows rose from 8% to 26% of training
  gold (Yes 20%, No 6%).
- **Synopsis specifics.** Beyond B737-style type codes, named aircraft and
  descriptors the analyst adds from the report header ("King Air", "narrow body
  Airbus", "vintage military aircraft") are generalized to "aircraft" unless the
  narrative names them. Reporter roles the analyst takes from the report header
  (Flight Attendant, Dispatcher, Instructor, Mechanic, …) become "reporter"
  when the narrative never uses the word, and "Captain"/"First Officer" become
  "reporter" when the narrator refers to that role in the third person ("my
  Captain") without claiming it. A stated cause ("due to fuel mismanagement")
  must have most of its words attested, and a cause whose words overlap a
  hedged narrative sentence ("I believe the … was caused by") is rejected.
  Reports whose narrator says they are not certain what happened are not
  supervised at all. Softer hedges promoted to fact by the analyst ("sounded
  like the gear horn") remain a known leak; the review records them.
- **Event-class grounding.** Twenty-eight analyst event and condition classes ("near miss",
  "runway incursion", "loss of separation", "engine failure", "hard landing",
  "bird strike", "night", "icing", "crosswind", …) must have lexical evidence in the narrative. The check
  rejects synopsis sentences at build time (about 100 more source rows are
  dropped) and counts against model outputs as a third grounding category at
  evaluation time, for base and adapter alike.

The 100-row agent review of the v0.2 splits is in [gold-review-v02.md](gold-review-v02.md).

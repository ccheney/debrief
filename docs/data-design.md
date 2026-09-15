# Data decisions

The 2022 ASRS Hub train split contains 38,655 rows, not the full 47,723 total
across all upstream splits. We draw the experiment solely from this pinned train
source and make a new independent 4,000/400 split.

The original synopsis can include facts absent from `Report 1_Narrative`. For
example, report 1574675's synopsis names a B737-700 even though its narrative does
not. Copying that synopsis would train the model to invent an aircraft type.

The mapper therefore ranks complete narrative sentences by synopsis word overlap
and selects up to two in original order. This trades polished compression for
traceable evidence. Contributors require both a source code and an attested
phrase. Recommendations are copied from a short narrator recommendation, or set
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

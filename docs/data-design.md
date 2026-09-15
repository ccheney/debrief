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

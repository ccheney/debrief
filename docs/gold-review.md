# Gold review — 100-row agent audit

Reviewer: Codex agent. This is an agent semantic review, not a human sign-off.

Reviewed the fixed seed-42 samples: 50 train and 50 eval. Compared all cards with selected narrative evidence (first/last and synopsis-overlap sentences), expanding full narratives for disputed cases. Earlier extractive versions were rejected and replaced before this review.

12/100 rows retain grounding concerns (7 train, 5 eval). This is below the PRD’s >20% stop threshold, so proceed with an **experimental** full train. No quality acceptance is implied. The strict human-review milestone remains outstanding.

Known systematic limits: code-derived phase/factor noise, sparse near-miss fields, mostly Unknown recovery, and often None stated lessons. Quantitative scores must be read alongside these limits. The review exposes residual errors; it does not claim the lexical filter proves grounding.

| Split | Report | Grounding concern | Notes |
|---|---|---|---|
| train | 1104280 | No | Awkward aircraft-generalization article repaired; primary factor remains a noisy analyst label. |
| train | 1589528 | No | No additional factual issue found in inspected narrative evidence; coded labels and recovery remain weak supervision. |
| train | 1108940 | No | No additional factual issue found in inspected narrative evidence; coded labels and recovery remain weak supervision. |
| train | 1733986 | No | No additional factual issue found in inspected narrative evidence; coded labels and recovery remain weak supervision. |
| train | 1721939 | No | No additional factual issue found in inspected narrative evidence; coded labels and recovery remain weak supervision. |
| train | 1777765 | Yes | Grounding concern: synopsis presents knob movement confidently; crew was uncertain about its cause. |
| train | 1020914 | No | No additional factual issue found in inspected narrative evidence; coded labels and recovery remain weak supervision. |
| train | 1104304 | No | No additional factual issue found in inspected narrative evidence; coded labels and recovery remain weak supervision. |
| train | 1213141 | No | No additional factual issue found in inspected narrative evidence; coded labels and recovery remain weak supervision. |
| train | 1598728 | No | No additional factual issue found in inspected narrative evidence; coded labels and recovery remain weak supervision. |
| train | 1698911 | No | No additional factual issue found in inspected narrative evidence; coded labels and recovery remain weak supervision. |
| train | 1791460 | No | No additional factual issue found in inspected narrative evidence; coded labels and recovery remain weak supervision. |
| train | 1101452 | No | Controller report; source flight phase is a coded proxy and is not established by the excerpt. |
| train | 1044797 | No | No additional factual issue found in inspected narrative evidence; coded labels and recovery remain weak supervision. |
| train | 1323817 | No | No additional factual issue found in inspected narrative evidence; coded labels and recovery remain weak supervision. |
| train | 1809400 | No | No additional factual issue found in inspected narrative evidence; coded labels and recovery remain weak supervision. |
| train | 1176060 | No | No additional factual issue found in inspected narrative evidence; coded labels and recovery remain weak supervision. |
| train | 1487135 | No | Recovery false negative retained: performed the reject is outside the intervention patterns; eighty equals source 80. |
| train | 1365483 | No | No additional factual issue found in inspected narrative evidence; coded labels and recovery remain weak supervision. |
| train | 1577830 | No | No additional factual issue found in inspected narrative evidence; coded labels and recovery remain weak supervision. |
| train | 1306003 | No | No additional factual issue found in inspected narrative evidence; coded labels and recovery remain weak supervision. |
| train | 1597014 | No | No additional factual issue found in inspected narrative evidence; coded labels and recovery remain weak supervision. |
| train | 1669334 | Yes | Grounding concern: narrator belief about heat causing illness is compressed into a definite causal statement. |
| train | 1439934 | Yes | Grounding concern: turbulence is promoted to a confirmed door-opening cause; narrator suspects latch engagement. |
| train | 1448461 | No | No additional factual issue found in inspected narrative evidence; coded labels and recovery remain weak supervision. |
| train | 1073162 | No | No additional factual issue found in inspected narrative evidence; coded labels and recovery remain weak supervision. |
| train | 1336398 | No | No additional factual issue found in inspected narrative evidence; coded labels and recovery remain weak supervision. |
| train | 1284046 | Yes | Grounding concern: light-twin aircraft classification is absent from the narrative. |
| train | 1269638 | No | Doubled article repaired; precautionary shutdown is supported. |
| train | 1003534 | No | No additional factual issue found in inspected narrative evidence; coded labels and recovery remain weak supervision. |
| train | 1633089 | No | No additional factual issue found in inspected narrative evidence; coded labels and recovery remain weak supervision. |
| train | 1732661 | Yes | Grounding concern: a belief that parts were missing over multiple flights becomes a definite history. |
| train | 1040633 | No | No additional factual issue found in inspected narrative evidence; coded labels and recovery remain weak supervision. |
| train | 1868241 | No | Reporter is a controller but the pilot caused the error; fixed controller mapping to require explicit controller error. |
| train | 1805340 | No | No additional factual issue found in inspected narrative evidence; coded labels and recovery remain weak supervision. |
| train | 1032788 | No | No additional factual issue found in inspected narrative evidence; coded labels and recovery remain weak supervision. |
| train | 1700350 | No | No additional factual issue found in inspected narrative evidence; coded labels and recovery remain weak supervision. |
| train | 1789831 | No | Recovery false negative retained: first-person singular stopped is not recognized by the current heuristic. |
| train | 1037203 | No | No additional factual issue found in inspected narrative evidence; coded labels and recovery remain weak supervision. |
| train | 1759559 | No | No additional factual issue found in inspected narrative evidence; coded labels and recovery remain weak supervision. |
| train | 1605752 | No | No additional factual issue found in inspected narrative evidence; coded labels and recovery remain weak supervision. |
| train | 1717536 | No | No additional factual issue found in inspected narrative evidence; coded labels and recovery remain weak supervision. |
| train | 1867033 | No | No additional factual issue found in inspected narrative evidence; coded labels and recovery remain weak supervision. |
| train | 1807796 | Yes | Grounding concern: probable fuel-starvation explanation becomes certain. |
| train | 1054066 | No | No additional factual issue found in inspected narrative evidence; coded labels and recovery remain weak supervision. |
| train | 1762538 | No | No additional factual issue found in inspected narrative evidence; coded labels and recovery remain weak supervision. |
| train | 992504 | No | Narrative says descent while synopsis says approach; mapped label follows the source code. |
| train | 1261836 | No | No additional factual issue found in inspected narrative evidence; coded labels and recovery remain weak supervision. |
| train | 1615153 | No | No additional factual issue found in inspected narrative evidence; coded labels and recovery remain weak supervision. |
| train | 1127499 | Yes | Grounding concern: single-engine turboprop classification is absent from the narrative. |
| eval | 1826165 | No | No additional factual issue found in inspected narrative evidence; coded labels and recovery remain weak supervision. |
| eval | 1667630 | No | Recovery false negative retained: progressive rejecting wording is not recognized. |
| eval | 1477796 | Yes | Grounding concern: corporate turboprop classification is not stated; Pilatus traffic is mentioned. |
| eval | 1746444 | No | No additional factual issue found in inspected narrative evidence; coded labels and recovery remain weak supervision. |
| eval | 1676949 | No | No additional factual issue found in inspected narrative evidence; coded labels and recovery remain weak supervision. |
| eval | 1418305 | No | No additional factual issue found in inspected narrative evidence; coded labels and recovery remain weak supervision. |
| eval | 1504017 | No | No additional factual issue found in inspected narrative evidence; coded labels and recovery remain weak supervision. |
| eval | 1104407 | No | No additional factual issue found in inspected narrative evidence; coded labels and recovery remain weak supervision. |
| eval | 1593509 | No | No additional factual issue found in inspected narrative evidence; coded labels and recovery remain weak supervision. |
| eval | 1835977 | Yes | Grounding concern: synopsis calls the reporter Captain; narrative refers to my Captain. |
| eval | 1829597 | No | No additional factual issue found in inspected narrative evidence; coded labels and recovery remain weak supervision. |
| eval | 1001364 | No | No additional factual issue found in inspected narrative evidence; coded labels and recovery remain weak supervision. |
| eval | 1053801 | No | No additional factual issue found in inspected narrative evidence; coded labels and recovery remain weak supervision. |
| eval | 1713005 | No | No additional factual issue found in inspected narrative evidence; coded labels and recovery remain weak supervision. |
| eval | 1057479 | No | No additional factual issue found in inspected narrative evidence; coded labels and recovery remain weak supervision. |
| eval | 1874135 | No | No additional factual issue found in inspected narrative evidence; coded labels and recovery remain weak supervision. |
| eval | 988193 | No | No additional factual issue found in inspected narrative evidence; coded labels and recovery remain weak supervision. |
| eval | 1760063 | No | No additional factual issue found in inspected narrative evidence; coded labels and recovery remain weak supervision. |
| eval | 1853596 | No | No additional factual issue found in inspected narrative evidence; coded labels and recovery remain weak supervision. |
| eval | 1684237 | No | No additional factual issue found in inspected narrative evidence; coded labels and recovery remain weak supervision. |
| eval | 1612690 | No | No additional factual issue found in inspected narrative evidence; coded labels and recovery remain weak supervision. |
| eval | 1703305 | No | No additional factual issue found in inspected narrative evidence; coded labels and recovery remain weak supervision. |
| eval | 1682915 | No | No additional factual issue found in inspected narrative evidence; coded labels and recovery remain weak supervision. |
| eval | 1268284 | No | No additional factual issue found in inspected narrative evidence; coded labels and recovery remain weak supervision. |
| eval | 1287858 | No | No additional factual issue found in inspected narrative evidence; coded labels and recovery remain weak supervision. |
| eval | 989070 | Yes | Grounding concern: fuel starvation is compressed to exhaustion, which can imply all usable fuel was depleted. |
| eval | 1580930 | No | No additional factual issue found in inspected narrative evidence; coded labels and recovery remain weak supervision. |
| eval | 1733947 | No | No additional factual issue found in inspected narrative evidence; coded labels and recovery remain weak supervision. |
| eval | 1023524 | Yes | Grounding concern: synopsis says gear-up position; narrative says gear dropped when selector went to OFF. |
| eval | 989406 | No | Off-field landing wording is not recognized; Unknown is a known recovery-heuristic limitation. |
| eval | 1504938 | No | No additional factual issue found in inspected narrative evidence; coded labels and recovery remain weak supervision. |
| eval | 1760776 | No | No additional factual issue found in inspected narrative evidence; coded labels and recovery remain weak supervision. |
| eval | 1605614 | No | No additional factual issue found in inspected narrative evidence; coded labels and recovery remain weak supervision. |
| eval | 1090331 | No | No additional factual issue found in inspected narrative evidence; coded labels and recovery remain weak supervision. |
| eval | 1227481 | No | No additional factual issue found in inspected narrative evidence; coded labels and recovery remain weak supervision. |
| eval | 1128106 | No | No additional factual issue found in inspected narrative evidence; coded labels and recovery remain weak supervision. |
| eval | 1748617 | No | No additional factual issue found in inspected narrative evidence; coded labels and recovery remain weak supervision. |
| eval | 1593213 | No | No additional factual issue found in inspected narrative evidence; coded labels and recovery remain weak supervision. |
| eval | 1226717 | No | No additional factual issue found in inspected narrative evidence; coded labels and recovery remain weak supervision. |
| eval | 1685376 | No | No additional factual issue found in inspected narrative evidence; coded labels and recovery remain weak supervision. |
| eval | 1860230 | Yes | Grounding concern: seemed like GPS jamming becomes a confirmed signal jam. |
| eval | 1633851 | No | No additional factual issue found in inspected narrative evidence; coded labels and recovery remain weak supervision. |
| eval | 1244670 | No | No additional factual issue found in inspected narrative evidence; coded labels and recovery remain weak supervision. |
| eval | 988233 | No | No additional factual issue found in inspected narrative evidence; coded labels and recovery remain weak supervision. |
| eval | 1590838 | No | No additional factual issue found in inspected narrative evidence; coded labels and recovery remain weak supervision. |
| eval | 1691136 | No | No additional factual issue found in inspected narrative evidence; coded labels and recovery remain weak supervision. |
| eval | 1008357 | No | No additional factual issue found in inspected narrative evidence; coded labels and recovery remain weak supervision. |
| eval | 1129965 | No | No additional factual issue found in inspected narrative evidence; coded labels and recovery remain weak supervision. |
| eval | 1114191 | No | Multiple controller/pilot reports and attribution ambiguity; phase/factor remain code-derived proxies. |
| eval | 1148188 | No | Recovery false negative retained: went missed and later successful approach are not matched. |

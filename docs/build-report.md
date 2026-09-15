# Dataset build

- source_rows: 38655
- truncated: 118
- drop_unsupported_synopsis: 33059
- drop_short_narrative: 727
- train: 4000
- eval: 400
- reserve: 469

Source: `elihoole/asrs-aviation-reports@f1e681e92cddae20d01fc498d685f1cf6a052d34`
License in source card: `['apache-2.0']`

Split groups combine report IDs, linked accession IDs and duplicate narratives. Reserve contains IDs only. Gold prose is source-checked synopsis; phase/factor labels and recoverability are noisy proxies. Human review is pending.

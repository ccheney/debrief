#!/usr/bin/env python3
"""Turn per-row review JSONL into the trainer's review gate and a condensed record.

Usage: python scripts/assemble_review.py --reviewer 'Name' --version v02 review_train.jsonl review_eval.jsonl

Each input line: {"split", "report_id", "grounding_concern", "fields", "note"}.
Rows must match data/processed/review_<split>.jsonl in order. Writes
data/processed/review_decision.json (bound to the split hashes) and
docs/gold-review-<version>.md. Approval follows the PRD stop threshold: more
than 20% of rows with a grounding concern blocks the full run.
"""

import argparse
from collections import Counter
from datetime import date
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.common import DEFAULT_CONFIG, read_config, read_jsonl, sha256, write_json  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("reviews", nargs="+")
    parser.add_argument("--reviewer", required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--config", default=DEFAULT_CONFIG)
    args = parser.parse_args()
    config = read_config(args.config)
    rows = [row for path in args.reviews for row in read_jsonl(path)]
    processed = Path(config["train_file"]).parent
    for split in ("train", "eval"):
        expected = [r["report_id"] for r in read_jsonl(processed / f"review_{split}.jsonl")]
        got = [r["report_id"] for r in rows if r["split"] == split]
        if got != expected:
            raise SystemExit(f"{split}: reviewed IDs do not match the review packet order")
    for row in rows:
        if not isinstance(row["grounding_concern"], bool) or not row.get("note"):
            raise SystemExit(f"Row {row['report_id']} is missing a boolean concern or a note")
    concerns = [row for row in rows if row["grounding_concern"]]
    rate = len(concerns) / len(rows)
    approved = rate <= 0.20
    decision = {
        "reviewer": args.reviewer,
        "review_type": "agent semantic review using narrative evidence; not a human sign-off",
        "date": date.today().isoformat(),
        "version": args.version,
        "n_reviewed": len(rows),
        "grounding_concerns": len(concerns),
        "concern_rate": round(rate, 3),
        "approved_for_experiment": approved,
        "human_review_complete": False,
        "train_sha256": sha256(config["train_file"]),
        "eval_sha256": sha256(config["eval_file"]),
        "rows": [
            {
                "split": row["split"],
                "report_id": row["report_id"],
                "grounding_concern": row["grounding_concern"],
                "fields": row.get("fields", []),
                "note": row["note"],
            }
            for row in rows
        ],
    }
    write_json(processed / "review_decision.json", decision)
    by_field = Counter(field for row in concerns for field in row.get("fields", []))
    by_split = Counter(row["split"] for row in concerns)
    verdict = (
        "below the PRD's 20% stop threshold, so the **experimental** full train may proceed"
        if approved
        else "above the PRD's 20% stop threshold; **do not train** until the rules are fixed"
    )
    text = f"# Gold review {args.version} — 100-row agent audit\n\n"
    text += f"Reviewer: {args.reviewer}, {decision['date']}. Agent semantic review, not a human sign-off.\n\n"
    text += "Fixed seed-42 samples: 50 train and 50 eval rows compared against the full narrative. "
    text += f"Bound to train `{decision['train_sha256'][:12]}…` and eval `{decision['eval_sha256'][:12]}…`.\n\n"
    text += f"{len(concerns)}/{len(rows)} rows retain a grounding concern "
    text += f"({by_split.get('train', 0)} train, {by_split.get('eval', 0)} eval), {verdict}. "
    text += "No quality acceptance is implied.\n\n"
    if by_field:
        text += (
            "Concerns by field: "
            + ", ".join(f"{k} {v}" for k, v in by_field.most_common())
            + ".\n\n"
        )
    text += "| Split | Report | Concern | Fields | Note |\n|---|---|---|---|---|\n"
    for row in rows:
        fields = ", ".join(row.get("fields", [])) or "—"
        note = row["note"].replace("|", "/").replace("\n", " ")
        text += f"| {row['split']} | {row['report_id']} | {'Yes' if row['grounding_concern'] else 'No'} | {fields} | {note} |\n"
    Path("docs", f"gold-review-{args.version}.md").write_text(text)
    print(json.dumps({k: v for k, v in decision.items() if k != "rows"}, indent=2))


if __name__ == "__main__":
    main()

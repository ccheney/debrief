"""Paired base/adapter evaluation with identical prompts, decoding and seeds."""

import argparse
from collections import Counter
import contextlib
import json
from pathlib import Path
import random
import statistics
import sys

from src.common import (
    DEFAULT_CONFIG,
    adapter_config,
    read_config,
    read_jsonl,
    sha256,
    version_of,
    write_json,
)
from src.schema import grounding_flags, parse_brief, words


def score_output(row, text, token_count):
    gold = parse_brief(row["messages"][2]["content"])
    flags = grounding_flags(row["narrative"], text)
    result = {
        "report_id": row["report_id"],
        "schema_valid": False,
        "factor_correct": False,
        "phase_correct": False,
        "recoverable_correct": False,
        "recoverable_known": gold.recoverable != "Unknown",
        "recoverable_gold": gold.recoverable,
        "grounding_fail": any(flags.values()),
        "grounding_flags": flags,
        "tokens": token_count,
        "near_miss_gold": row.get("near_miss_gold", False),
        "near_miss_distinct": False,
        "recoverable_prediction": "invalid",
        "lesson_gold": gold.lesson != "None stated.",
        "lesson_present": False,
        "lesson_grounded": False,
    }
    try:
        brief = parse_brief(text)
    except ValueError as exc:
        result["parse_error"] = str(exc)
        return result
    result.update(
        schema_valid=True,
        factor_correct=brief.primary_factor == gold.primary_factor,
        phase_correct=brief.phase_of_flight == gold.phase_of_flight,
        recoverable_correct=brief.recoverable == gold.recoverable,
        recoverable_prediction=brief.recoverable,
        near_miss_distinct=brief.what_almost_happened
        not in ("None stated", "Unknown", brief.what_happened),
        lesson_present=brief.lesson != "None stated.",
    )
    if result["lesson_present"]:
        # "No new facts" proxy: most content words of the lesson appear in the narrative.
        content = words(brief.lesson)
        result["lesson_grounded"] = (
            len(content & words(row["narrative"])) / max(1, len(content)) >= 0.6
        )
    return result


def aggregate(scores):
    if not scores:
        raise ValueError("Cannot evaluate an empty set")

    def mean(key, data=scores):
        return sum(bool(row[key]) for row in data) / len(data) if data else None

    known = [row for row in scores if row["recoverable_known"]]
    near = [row for row in scores if row["near_miss_gold"]]
    lesson_gold = [row for row in scores if row["lesson_gold"]]
    lesson_emitted = [row for row in scores if row["lesson_present"]]
    return {
        "n": len(scores),
        "valid_schema": mean("schema_valid"),
        "factor_acc": mean("factor_correct"),
        "phase_acc": mean("phase_correct"),
        "recoverable_acc": mean("recoverable_correct"),
        "recoverable_known_acc": mean("recoverable_correct", known),
        "recoverable_known_n": len(known),
        "grounding_fail": mean("grounding_fail"),
        "median_tokens": statistics.median(row["tokens"] for row in scores),
        "near_miss_distinct": mean("near_miss_distinct", near),
        "near_miss_n": len(near),
        "lesson_recall": mean("lesson_present", lesson_gold),
        "lesson_n": len(lesson_gold),
        "lesson_emitted": mean("lesson_present"),
        "lesson_grounded": mean("lesson_grounded", lesson_emitted),
        "recoverable_distribution": dict(Counter(row["recoverable_prediction"] for row in scores)),
        "recoverable_gold_distribution": dict(Counter(row["recoverable_gold"] for row in known)),
        "recoverable_known_distribution": dict(
            Counter(row["recoverable_prediction"] for row in known)
        ),
    }


def decide(base, adapter):
    checks = {
        "schema_at_least_95_percent": adapter["valid_schema"] >= 0.95,
        "schema_not_worse": adapter["valid_schema"] >= base["valid_schema"],
        "factor_gain_15pp": adapter["factor_acc"] - base["factor_acc"] >= 0.15 - 1e-9,
        "phase_gain_10pp": adapter["phase_acc"] - base["phase_acc"] >= 0.10 - 1e-9,
        "grounding_at_most_10_percent": adapter["grounding_fail"] <= 0.10,
        "grounding_not_worse": adapter["grounding_fail"] <= base["grounding_fail"],
        "recoverable_improves": (
            adapter["recoverable_known_acc"] is not None
            and base["recoverable_known_acc"] is not None
            and adapter["recoverable_known_acc"] > base["recoverable_known_acc"]
        ),
        "recoverable_binary_support": all(
            adapter["recoverable_gold_distribution"].get(label, 0) > 0 for label in ("Yes", "No")
        ),
        "recoverable_not_collapsed": all(
            adapter["recoverable_known_distribution"].get(label, 0) > 0 for label in ("Yes", "No")
        ),
    }
    if not checks["grounding_not_worse"]:
        decision = "STOP: adapter grounding is worse than base; do not ship"
    elif all(checks.values()):
        decision = "AUTOMATIC GATES PASS: rubric review still required before acceptance"
    else:
        decision = "NOT ACCEPTED: one or more v0.1 targets were missed"
    return {"decision": decision, "checks": checks}


def assert_disjoint(train, evaluation):
    for key in ("report_id", "group_id", "narrative_sha256"):
        if any(key not in row for row in train + evaluation):
            raise ValueError(f"Missing leakage metadata: {key}")
        if {row[key] for row in train} & {row[key] for row in evaluation}:
            raise ValueError(f"Evaluation leaked into training ({key})")
    if len({row["report_id"] for row in evaluation}) != len(evaluation):
        raise ValueError("Duplicate evaluation report IDs")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default=DEFAULT_CONFIG)
    parser.add_argument("--adapter", help="Default: adapter_dir from --config")
    parser.add_argument("--output", help="Default: eval_runs/<version> from --config")
    parser.add_argument(
        "--limit", type=int, help="Smoke evaluation only; never a full acceptance result"
    )
    parser.add_argument("--predictions", help="Score existing paired JSONL; no GPU required")
    args = parser.parse_args()
    if args.limit is not None and args.limit <= 0:
        parser.error("--limit must be positive")
    args.adapter = args.adapter or read_config(args.config)["adapter_dir"]
    config = (
        read_config(args.config) if args.predictions else adapter_config(args.adapter, args.config)
    )
    args.output = args.output or f"eval_runs/{version_of(config)}"
    evaluation = read_jsonl(config["eval_file"])
    assert_disjoint(read_jsonl(config["train_file"]), evaluation)
    if args.limit:
        evaluation = evaluation[: args.limit]
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    predictions_path = out.with_suffix(".predictions.jsonl")
    if args.predictions:
        predictions = read_jsonl(args.predictions)
        if len(predictions) != len(evaluation) or [p["report_id"] for p in predictions] != [
            r["report_id"] for r in evaluation
        ]:
            raise ValueError("Predictions must match every evaluation report in order")
    else:
        if predictions_path.exists():
            raise ValueError(f"Output exists: {predictions_path}; choose a fresh --output")
        with contextlib.redirect_stdout(sys.stderr):
            from src.runtime import Generator

            generator = Generator(config, args.adapter)
        predictions = []
        with predictions_path.open("w") as stream:
            for i, row in enumerate(evaluation):
                item = {"report_id": row["report_id"]}
                for name, adapter in (("base", False), ("adapter", True)):
                    with contextlib.redirect_stdout(sys.stderr):
                        item[name] = generator.generate(
                            row["narrative"], use_adapter=adapter, seed=config["seed"] + i
                        )
                predictions.append(item)
                stream.write(json.dumps(item) + "\n")
                stream.flush()
                print(f"Evaluated {i + 1}/{len(evaluation)}", file=sys.stderr)
    scores = {
        name: [
            score_output(row, item[name]["text"], item[name]["tokens"])
            for row, item in zip(evaluation, predictions)
        ]
        for name in ("base", "adapter")
    }
    metrics = {name: aggregate(value) for name, value in scores.items()}
    result = {
        "config": config,
        "adapter_path": args.adapter,
        "eval_sha256": sha256(config["eval_file"]),
        "adapter_files_sha256": {
            p.name: sha256(p) for p in sorted(Path(args.adapter).glob("adapter*")) if p.is_file()
        },
        "scorer_sha256": {
            str(p): sha256(p)
            for p in (Path(__file__), Path("src/schema.py"), Path("src/prompt.py"))
        },
        "smoke_only": bool(args.limit),
        "metrics": metrics,
        "gates": decide(**metrics),
        "rubric_review": "pending",
        "scoring_limitations": "Lexical specifics check misses semantic hallucinations; coded labels are noisy.",
    }
    if args.limit:
        result["gates"]["decision"] = "SMOKE ONLY: no acceptance conclusion"
    write_json(out.with_name(out.name + "_metrics.json"), result)
    write_json(out.with_suffix(".scores.json"), scores)
    report = f"# Debrief evaluation\n\nBase: `{config['model_id']}@{config['model_revision']}`\n\nN = {len(evaluation)}\n\n"
    report += "| Metric | Base | Adapter |\n|---|---:|---:|\n"
    for metric in (
        "valid_schema",
        "factor_acc",
        "phase_acc",
        "recoverable_acc",
        "recoverable_known_acc",
        "grounding_fail",
        "median_tokens",
        "near_miss_distinct",
        "lesson_recall",
        "lesson_emitted",
        "lesson_grounded",
    ):

        def fmt(value):
            return "N/A" if value is None else f"{value:.3f}"

        report += (
            f"| {metric} | {fmt(metrics['base'][metric])} | {fmt(metrics['adapter'][metric])} |\n"
        )
    report += (
        f"\nRecovery scored on {metrics['adapter']['recoverable_known_n']} derivable rows; "
        f"near-miss distinction scored on {metrics['adapter']['near_miss_n']} labeled rows; "
        f"lesson recall on {metrics['adapter']['lesson_n']} rows with a gold lesson.\n"
    )
    report += f"\n**{result['gates']['decision']}**\n\n"
    report += "Grounding is a numbers/acronyms heuristic, not a semantic judge. The held-out source labels and recovery heuristic are noisy.\n"
    out.with_suffix(".md").write_text(report)
    indexes = random.Random(config["seed"]).sample(range(len(evaluation)), min(20, len(evaluation)))
    failures = [i for i, score in enumerate(scores["adapter"]) if score["grounding_fail"]][:10]
    rubric = "# Rubric review\n\nScore 0–2: grounding, event/near-miss distinction, reasonable factor, grounded one-sentence lesson.\n"
    for i in dict.fromkeys(indexes + failures):
        rubric += f"\n## {evaluation[i]['report_id']}\n\n{evaluation[i]['narrative']}\n\n{predictions[i]['adapter']['text']}\n\nScores / notes: pending\n"
    out.with_name(out.name + "_rubric.md").write_text(rubric)
    lesson_indexes = random.Random(config["seed"] + 1).sample(
        range(len(evaluation)), min(50, len(evaluation))
    )
    lessons = (
        "# Lesson review\n\nCheck each lesson for one sentence and no unsupported facts or fixes.\n"
    )
    for i in lesson_indexes:
        try:
            lesson = parse_brief(predictions[i]["adapter"]["text"]).lesson
        except ValueError:
            lesson = "Invalid brief; raw output follows:\n\n" + predictions[i]["adapter"]["text"]
        lessons += (
            f"\n## {evaluation[i]['report_id']}\n\n"
            f"### Narrative\n\n{evaluation[i]['narrative']}\n\n"
            f"### Lesson\n\n{lesson}\n\nGrounded / useful / notes: pending\n"
        )
    out.with_name(out.name + "_lessons.md").write_text(lessons)
    print(report)


if __name__ == "__main__":
    main()

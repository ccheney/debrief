"""Build a revision-pinned, grouped, source-grounded ASRS chat dataset."""

import argparse
from collections import Counter
import hashlib
from pathlib import Path
import random
import re

from src.common import DEFAULT_CONFIG, read_config, read_jsonl, sha256, write_json, write_jsonl
from src.prompt import messages_for
from src.schema import supported_synopsis
from src.schema import COLUMNS, SYSTEM_PROMPT, compose_gold, grounding_flags, label_map


def truncate_narrative(text, tokenizer, cap=1200):
    ids = tokenizer.encode(text, add_special_tokens=False)
    if len(ids) <= cap:
        return text, False
    # Reserve the omission marker inside the budget. Keep complete sentences at
    # the cut when possible, avoiding new facts assembled across the join.
    marker = "\n[... narrative excerpt omitted ...]\n"
    marker_size = len(tokenizer.encode(marker, add_special_tokens=False))
    head_size = (cap - marker_size) * 2 // 3
    tail_size = cap - marker_size - head_size
    head = tokenizer.decode(ids[:head_size], skip_special_tokens=True)
    tail = tokenizer.decode(ids[-tail_size:], skip_special_tokens=True)
    if ". " in head:
        head = head.rsplit(". ", 1)[0] + "."
    if ". " in tail:
        tail = tail.split(". ", 1)[1]
    result = head + marker + tail
    while len(tokenizer.encode(result, add_special_tokens=False)) > cap:
        head = head.rsplit(" ", 1)[0]
        result = head + marker + tail
    return result, True


def grouped_split(rows, train_size, eval_size, seed):
    """Keep accession links AND exact normalized narrative duplicates together."""
    parent = {}

    def find(key):
        parent.setdefault(key, key)
        if parent[key] != key:
            parent[key] = find(parent[key])
        return parent[key]

    def union(a, b):
        a, b = find(a), find(b)
        parent[max(a, b)] = min(a, b)

    for row in rows:
        rid = row["report_id"]
        find(rid)
        for related in row.get("related_ids", []):
            union(rid, related)
        union(rid, "text:" + row["narrative_sha256"])
    groups = {}
    for row in rows:
        groups.setdefault(find(row["report_id"]), []).append(row)
    keys = sorted(groups)
    random.Random(seed).shuffle(keys)
    train, evaluation, reserve = [], [], []
    for key in keys:
        group = sorted(groups[key], key=lambda row: row["report_id"])
        if len(evaluation) + len(group) <= eval_size:
            evaluation.extend(group)
        elif len(train) + len(group) <= train_size:
            train.extend(group)
        else:
            reserve.extend(group)
    if len(train) != train_size or len(evaluation) != eval_size:
        raise ValueError(
            f"Insufficient eligible groups: train={len(train)}, eval={len(evaluation)}"
        )
    for split in (train, evaluation, reserve):
        for row in split:
            row["group_id"] = find(row["report_id"])
    return train, evaluation, reserve


def build(rows, tokenizer, config):
    counts = Counter()
    eligible = []
    seen = set()
    for raw in rows:
        counts["source_rows"] += 1
        rid = str(raw.get(COLUMNS["id"], "") or "").strip()
        if not rid:
            counts["drop_missing_id"] += 1
            continue
        if rid in seen:
            counts["drop_duplicate_id"] += 1
            continue
        seen.add(rid)
        original = str(raw.get(COLUMNS["narrative"], "") or "").strip()
        if len(original) < 200:
            counts["drop_short_narrative"] += 1
            continue
        if not raw.get(COLUMNS["synopsis"]) and not raw.get(COLUMNS["factor"]):
            counts["drop_no_supervision"] += 1
            continue
        if not supported_synopsis(str(raw.get(COLUMNS["synopsis"], "") or ""), original):
            counts["drop_unsupported_synopsis"] += 1
            continue
        narrative, truncated = truncate_narrative(original, tokenizer, config["narrative_tokens"])
        counts["truncated"] += int(truncated)
        brief = compose_gold(raw, narrative)
        if brief is None:
            counts["drop_unsupported_synopsis"] += 1
            continue
        gold = brief.render()
        flags = grounding_flags(narrative, gold)
        if any(flags.values()):
            counts["drop_grounding"] += 1
            continue
        messages = messages_for(narrative) + [{"role": "assistant", "content": gold}]
        length = len(tokenizer.apply_chat_template(messages, tokenize=True, enable_thinking=False))
        if length > config["max_seq_length"]:
            counts["drop_sequence_length"] += 1
            continue
        eligible.append(
            {
                "report_id": rid,
                "messages": messages,
                "narrative": narrative,
                "related_ids": re.findall(r"\b\d{6,8}\b", str(raw.get(COLUMNS["related_id"], ""))),
                "narrative_sha256": hashlib.sha256(
                    " ".join(original.lower().split()).encode()
                ).hexdigest(),
                "truncated": truncated,
                "token_count": length,
                "near_miss_gold": brief.what_almost_happened != "None stated",
            }
        )
    train, evaluation, reserve = grouped_split(
        eligible, config["train_size"], config["eval_size"], config["seed"]
    )
    counts.update(train=len(train), eval=len(evaluation), reserve=len(reserve))
    # Rare positive fields collapse to their empty value at ~1-3% prevalence
    # (v0.1 never emitted a lesson). Exact copies of near-miss rows raise their
    # share in the training split only; the held-out split keeps its natural mix.
    copies = int(config.get("oversample_near_miss", 1))
    boosted = [row for row in train if row["near_miss_gold"]] * (copies - 1)
    counts.update(train_near_miss_rows=sum(row["near_miss_gold"] for row in train))
    counts.update(
        train_oversampled_copies=len(boosted), train_rows_written=len(train) + len(boosted)
    )
    return train, evaluation, reserve, dict(counts), boosted


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default=DEFAULT_CONFIG)
    parser.add_argument("--input", help="Local raw JSONL from the pinned source")
    parser.add_argument("--output", default="data/processed")
    args = parser.parse_args()
    config = read_config(args.config)
    from huggingface_hub import HfApi, hf_hub_download
    from transformers import AutoTokenizer

    info = HfApi().dataset_info(config["dataset_id"], revision=config["dataset_revision"])
    card = info.card_data.to_dict() if info.card_data else {}
    if not card.get("license"):
        raise ValueError("Source dataset card has no license; record provenance before building")
    source_path = args.input or hf_hub_download(
        config["dataset_id"],
        f"asrs-aviation-reports-{config['dataset_split']}.jsonl",
        repo_type="dataset",
        revision=config["dataset_revision"],
    )
    rows = read_jsonl(source_path)
    # Freeze actual column names and frequencies, independently of our mapping.
    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)
    inventory = {
        "columns": sorted(rows[0]),
        "frequencies": {
            key: dict(Counter(str(row.get(COLUMNS[key], "")) for row in rows))
            for key in ("phase", "factor")
        },
    }
    write_json(out / "column_inventory.json", inventory)
    tokenizer = AutoTokenizer.from_pretrained(config["model_id"], revision=config["model_revision"])
    train, evaluation, reserve, counts, boosted = build(rows, tokenizer, config)
    for name, split in (("train", train + boosted), ("eval", evaluation)):
        write_jsonl(out / f"{name}.jsonl", split)
    # Reserve IDs only: no reserve narrative inspection or training.
    (out / "reserve_ids.txt").write_text("\n".join(row["report_id"] for row in reserve) + "\n")
    write_jsonl(out / "sample.jsonl", train[:10])
    write_json(out / "label_map.json", label_map())
    manifest = {
        "config": config,
        "source_revision": info.sha,
        "dataset_license": card["license"],
        "source_file_sha256": sha256(source_path),
        "counts": counts,
        "train_sha256": sha256(out / "train.jsonl"),
        "eval_sha256": sha256(out / "eval.jsonl"),
        "label_map_sha256": sha256(out / "label_map.json"),
        "system_prompt_sha256": hashlib.sha256(SYSTEM_PROMPT.encode()).hexdigest(),
        "gold_method": "source-checked synopsis; absent aircraft types generalized; coded class labels; "
        "extractive lesson/near-miss/recovery rules (label_map version 4); no teacher model",
        "label_map_version": label_map()["version"],
        "oversample_near_miss": int(config.get("oversample_near_miss", 1)),
    }
    write_json(out / "manifest.json", manifest)
    for split_name, split in (("train", train), ("eval", evaluation)):
        sample = random.Random(config["seed"]).sample(split, min(50, len(split)))
        write_jsonl(out / f"review_{split_name}.jsonl", sample)
        text = f"# {split_name.title()} gold review\n\nBuilder review required; automated checks are not human review.\n"
        for row in sample:
            text += f"\n## {row['report_id']}\n\n### Narrative\n\n{row['messages'][1]['content']}\n\n### Gold\n\n{row['messages'][2]['content']}\n\nReview: pending\n"
        (out / f"review_{split_name}.md").write_text(text)
    report = "# Dataset build\n\n" + "\n".join(f"- {k}: {v}" for k, v in counts.items())
    report += f"\n\nSource: `{config['dataset_id']}@{info.sha}`\nLicense in source card: `{card['license']}`\n\n"
    report += "Split groups combine report IDs, linked accession IDs and duplicate narratives. Reserve contains IDs only. "
    report += "Gold prose is source-checked synopsis; phase/factor labels and recoverability are noisy proxies. "
    report += "Lesson, near-miss and recovery fields are extracted by deterministic rules. "
    report += "Near-miss rows are duplicated in the training split only. Human review is pending.\n"
    (out / "build_report.md").write_text(report)
    print(report)


if __name__ == "__main__":
    main()

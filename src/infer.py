"""Generate one brief or a JSONL batch on the local NVIDIA GPU."""

import argparse
import contextlib
import json
from pathlib import Path
import sys
from src.common import DEFAULT_CONFIG, adapter_config, read_config, read_jsonl
from src.schema import parse_brief


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config", help="Default: saved adapter configuration, or project config for --base"
    )
    parser.add_argument("--adapter", help="Default: adapter_dir from the project config")
    parser.add_argument("--base", action="store_true", help="Run the untuned baseline")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--file", type=Path)
    source.add_argument("--text")
    source.add_argument("--batch", type=Path, help='JSONL rows with "narrative" and optional "id"')
    source.add_argument("--stdin", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    args.adapter = args.adapter or read_config(args.config or DEFAULT_CONFIG)["adapter_dir"]
    if not args.base and not Path(args.adapter, "adapter_config.json").exists():
        parser.error(f"Adapter not found: {args.adapter}; train first or use --base")
    rows = (
        read_jsonl(args.batch)
        if args.batch
        else [
            {
                "narrative": args.text
                if args.text is not None
                else args.file.read_text()
                if args.file
                else sys.stdin.read()
            }
        ]
    )
    for i, row in enumerate(rows):
        if not isinstance(row.get("narrative"), str) or not row["narrative"].strip():
            parser.error(f"Row {i + 1}: narrative must be a nonempty string")
    # Keep package banners, download logs and CUDA diagnostics off machine stdout.
    with contextlib.redirect_stdout(sys.stderr):
        from src.runtime import Generator

        config = (
            read_config(args.config or DEFAULT_CONFIG)
            if args.base
            else adapter_config(args.adapter, args.config)
        )
        generator = Generator(config, None if args.base else args.adapter)
    invalid = False
    for i, row in enumerate(rows):
        with contextlib.redirect_stdout(sys.stderr):
            generated = generator.generate(row["narrative"], seed=generator.config["seed"])
        try:
            brief = parse_brief(generated["text"])
            value = brief.to_dict()
        except ValueError as exc:
            invalid = True
            value = {"error": str(exc), "raw_output": generated["text"]}
            print(f"Invalid model output: {exc}", file=sys.stderr)
        if generated["input_truncated"]:
            print(f"Row {i + 1}: narrative truncated to head/tail context", file=sys.stderr)
        if args.batch:
            print(
                json.dumps(
                    {
                        "id": row.get("id", i),
                        "brief": value,
                        "input_truncated": generated["input_truncated"],
                    },
                    ensure_ascii=False,
                )
            )
        elif args.json:
            print(json.dumps(value, ensure_ascii=False, indent=2))
        else:
            print(generated["text"])
    if invalid:
        raise SystemExit(2)


if __name__ == "__main__":
    main()

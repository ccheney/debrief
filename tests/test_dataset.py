import pytest
from src.build_dataset import grouped_split, truncate_narrative
from src.eval_briefs import aggregate, assert_disjoint, decide, score_output
from src.schema import Brief


def row(rid, text=None, related=()):
    return {
        "report_id": str(rid),
        "narrative_sha256": text or str(rid),
        "related_ids": list(related),
    }


def test_group_split_is_stable_and_never_leaks():
    rows = [row(i) for i in range(30)] + [row(99, text="1"), row(100, related=["2"])]
    a, b, r = grouped_split(rows, 16, 8, 42)
    a2, b2, _ = grouped_split(list(reversed(rows)), 16, 8, 42)
    assert [x["report_id"] for x in a] == [x["report_id"] for x in a2]
    assert [x["report_id"] for x in b] == [x["report_id"] for x in b2]
    assert_disjoint(a, b)
    partitions = [{x["report_id"] for x in split} for split in (a, b, r)]
    assert any({"1", "99"} <= split for split in partitions)
    assert any({"2", "100"} <= split for split in partitions)


def test_transitive_linkage():
    rows = [row("1", related=["2"]), row("2", related=["3"]), row("3")] + [
        row(i) for i in range(4, 40)
    ]
    splits = grouped_split(rows, 20, 8, 42)
    assert any({"1", "2", "3"} <= {r["report_id"] for r in split} for split in splits)


def test_short_source_fails_loudly():
    with pytest.raises(ValueError, match="Insufficient"):
        grouped_split([row(1)], 4000, 400, 42)


class CharacterTokenizer:
    def encode(self, text, **kwargs):
        return list(text)

    def decode(self, tokens, **kwargs):
        return "".join(tokens)


def test_truncation_preserves_head_and_tail_and_cap():
    text = "Beginning of report. " + "Middle narrative sentences. " * 80 + "Last relevant ending."
    cut, changed = truncate_narrative(text, CharacterTokenizer(), 250)
    assert (
        changed
        and len(cut) <= 250
        and cut.startswith("Beginning")
        and cut.endswith("Last relevant ending.")
    )
    assert "[... narrative excerpt omitted ...]" in cut


def test_malformed_output_counts_as_incorrect():
    r = {
        "report_id": "1",
        "narrative": "We stopped.",
        "messages": [{}, {}, {"content": Brief("We stopped.").render()}],
    }
    score = score_output(r, "We stopped.", 5)
    assert not score["schema_valid"] and not score["factor_correct"]
    assert aggregate([score])["valid_schema"] == 0


def test_grounding_regression_blocks_acceptance():
    base = {
        "valid_schema": 0.98,
        "factor_acc": 0.5,
        "phase_acc": 0.5,
        "grounding_fail": 0.02,
        "recoverable_known_acc": 0.5,
        "recoverable_distribution": {"Yes": 2, "No": 2},
    }
    adapter = dict(
        base, factor_acc=0.8, phase_acc=0.8, grounding_fail=0.03, recoverable_known_acc=0.8
    )
    assert decide(base, adapter)["decision"].startswith("STOP")


def test_adapter_configuration_cannot_silently_change_base(tmp_path):
    import json
    from src.common import adapter_config

    config = {
        "model_id": "base-one",
        "model_revision": "frozen",
        "narrative_tokens": 1200,
        "max_seq_length": 2048,
    }
    (tmp_path / "debrief_config.json").write_text(json.dumps(config))
    assert adapter_config(tmp_path) == config
    path = tmp_path / "other.yaml"
    path.write_text(
        "model_id: another-base\nmodel_revision: frozen\nnarrative_tokens: 1200\nmax_seq_length: 2048\n"
    )
    with pytest.raises(ValueError, match="model_id"):
        adapter_config(tmp_path, path)

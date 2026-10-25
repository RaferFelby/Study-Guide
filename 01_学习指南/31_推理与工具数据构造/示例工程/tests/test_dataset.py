import copy
import json

import pytest

from data import deduplicate, fingerprint, make_raw_samples, make_sources
from formatting import encode_training_sample, make_review_sheet, to_messages
from pipeline import prepare_dataset, write_dataset
from splitting import check_leakage, group_related, split_samples
from validation import SampleError, add_units, clean_samples, validate_sample


def first_sample():
    return copy.deepcopy(make_raw_samples()[0])


def test_candidate_counts_failure_reasons_and_source_manifest():
    splits, report, review = prepare_dataset()
    assert (report["raw"], report["auto_valid"], report["unique"]) == (55, 50, 48)
    assert len(report["rejected"]) == 5 and len(report["duplicates"]) == 2
    assert {item["reason"] for item in report["rejected"]} == {
        "answer_wrong",
        "tool_result_wrong",
        "call_result_unmatched",
        "tool_not_allowed",
        "source_unknown",
    }
    assert report["split_sizes"] == {"train": 28, "dev": 10, "test": 10}
    assert report["split_groups"] == {"train": 14, "dev": 5, "test": 5}
    assert not report["leakage"] and not check_leakage(splits)
    assert report["stage"] == "candidate_only_pending_human_review"
    assert report["generation_model"] is None and report["training_executed"] is False
    assert (
        report["human_review_complete"] is False
        and review["human_review_complete"] is False
    )
    assert report["learning_curve_measured"] is False


@pytest.mark.parametrize(
    "mutation",
    [
        "fields",
        "blank",
        "family",
        "version",
        "usage",
        "model",
        "revision",
        "question",
        "arguments",
        "trace_length",
        "result_bool",
        "call_fields",
    ],
)
def test_wrong_structure_source_or_trace_is_rejected(mutation):
    sample = first_sample()
    if mutation == "fields":
        sample["password"] = "demo"
    elif mutation == "blank":
        sample["question"] = "  "
    elif mutation == "family":
        sample["family_id"] = "other"
    elif mutation == "version":
        sample["provenance"]["source_version"] = "v2"
    elif mutation == "usage":
        sample["provenance"]["usage_policy"] = "unknown"
    elif mutation == "model":
        sample["provenance"]["generation_model"] = "not_actually_called"
    elif mutation == "revision":
        sample["provenance"]["revision"] = True
    elif mutation == "question":
        sample["question"] = "一个真实订单的数量？"
    elif mutation == "arguments":
        sample["tool_calls"][0]["arguments"]["left"] = 2
    elif mutation == "trace_length":
        sample["tool_results"] = []
    elif mutation == "result_bool":
        sample["tool_results"][0]["total"] = True
    else:
        sample["tool_calls"][0]["path"] = "anything"
    with pytest.raises(SampleError):
        validate_sample(sample, make_sources())


@pytest.mark.parametrize("values", [(True, 1), (-1, 1), (31, 1), (1.5, 1)])
def test_tool_argument_boundaries(values):
    with pytest.raises(SampleError):
        add_units(*values)


def test_duplicate_ids_are_rejected_and_normalized_content_is_deduplicated():
    sample = first_sample()
    valid, rejected = clean_samples([sample, copy.deepcopy(sample)], make_sources())
    assert len(valid) == 1 and rejected[0]["reason"] == "sample_id_duplicate"
    duplicate = copy.deepcopy(sample)
    duplicate["sample_id"] = "another-id"
    duplicate["question"] = "  " + sample["question"] + "  "
    assert fingerprint(duplicate) == fingerprint(sample)
    unique, duplicates = deduplicate([sample, duplicate])
    assert len(unique) == 1 and duplicates == [
        {"removed": "another-id", "kept": sample["sample_id"]}
    ]
    changed = copy.deepcopy(sample)
    changed["tool_calls"][0]["arguments"]["left"] = 9
    assert fingerprint(changed) != fingerprint(sample)


def test_group_related_merges_transitive_source_and_family_links():
    samples = copy.deepcopy(make_raw_samples()[:3])
    samples[0]["source_id"] = "source-a"
    samples[0]["family_id"] = "family-a"
    samples[1]["source_id"] = "source-a"
    samples[1]["family_id"] = "family-b"
    samples[2]["source_id"] = "source-c"
    samples[2]["family_id"] = "family-b"
    assert len(group_related(samples)) == 1


@pytest.mark.parametrize(
    "field", ["source_id", "family_id", "plan_summary", "revision"]
)
def test_same_content_with_different_evidence_is_preserved(field):
    sample = first_sample()
    other = copy.deepcopy(sample)
    other["sample_id"] = "other-evidence"
    if field == "revision":
        other["provenance"]["revision"] = 2
    else:
        other[field] = "different-evidence"
    unique, removed = deduplicate([sample, other])
    assert len(unique) == 2 and not removed
    assert len(group_related(unique)) == 1


def test_split_is_deterministic_and_order_independent():
    valid, _ = clean_samples(make_raw_samples(), make_sources())
    samples, _ = deduplicate(valid)
    assert split_samples(samples) == split_samples(list(reversed(samples)))
    with pytest.raises(ValueError):
        split_samples(samples[:2])


def test_deliberate_leak_is_detected_for_ids_sources_families_and_content():
    sample = first_sample()
    findings = check_leakage(
        {"train": [sample], "dev": [copy.deepcopy(sample)], "test": []}
    )
    assert {item["field"] for item in findings} == {
        "sample_id",
        "source_id",
        "family_id",
        "fingerprint",
    }
    with pytest.raises(ValueError):
        check_leakage({"train": []})


def test_messages_and_byte_labels_supervise_only_assistant_bodies():
    sample = first_sample()
    messages = to_messages(sample)
    assert [item["role"] for item in messages] == [
        "system",
        "user",
        "assistant",
        "tool",
        "assistant",
    ]
    encoded = encode_training_sample(sample)
    assert len(encoded["input_ids"]) == len(encoded["labels"])
    assert encoded["real_model_compatible"] is False
    for span in encoded["spans"]:
        labels = encoded["labels"][span["start"] : span["end"]]
        if span["role"] == "assistant":
            assert labels == encoded["input_ids"][span["start"] : span["end"]]
        else:
            assert set(labels) == {-100}
    assert sum(span["supervised"] for span in encoded["spans"]) == 2
    assert "合成订单" in bytes(encoded["input_ids"]).decode("utf-8")
    with pytest.raises(ValueError, match="不静默截断"):
        encode_training_sample(sample, maximum_bytes=10)


def test_review_sheet_is_pending_diverse_and_does_not_approve_training():
    sources = make_sources()
    valid, _ = clean_samples(make_raw_samples(), sources)
    unique, _ = deduplicate(valid)
    sheet = make_review_sheet(unique)
    assert len(sheet["items"]) == 8
    assert len({item["sample_id"].split("-")[1] for item in sheet["items"]}) == 8
    assert all(
        item["decision"] == "pending" and item["reviewer"] == ""
        for item in sheet["items"]
    )
    assert sheet["human_review_complete"] is False


def test_export_retains_raw_candidates_provenance_and_never_overwrites(tmp_path):
    output = tmp_path / "new-dataset"
    report = write_dataset(output)
    assert len((output / "raw.jsonl").read_text(encoding="utf-8").splitlines()) == 55
    candidates = [
        json.loads(line)
        for line in (output / "candidates.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    ]
    assert len(candidates) == 48 and all("provenance" in row for row in candidates)
    assert json.loads((output / "report.json").read_text(encoding="utf-8")) == report
    for name, count in report["split_sizes"].items():
        rows = [
            json.loads(line)
            for line in (output / f"{name}.jsonl")
            .read_text(encoding="utf-8")
            .splitlines()
        ]
        assert len(rows) == count and all(
            row["stage"] == report["stage"] for row in rows
        )
    with pytest.raises(FileExistsError):
        write_dataset(output)

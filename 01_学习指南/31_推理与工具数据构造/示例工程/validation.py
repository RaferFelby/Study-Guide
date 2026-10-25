"""分别检查结构、工具轨迹及固定合成任务答案；不执行任意工具名。"""

from data import normalize_text, questions


class SampleError(ValueError):
    pass


def add_units(left, right):
    if any(type(value) is not int or not 0 <= value <= 30 for value in (left, right)):
        raise SampleError("tool_arguments_invalid")
    return left + right


def validate_sample(sample, sources):
    fields = {
        "sample_id",
        "source_id",
        "family_id",
        "question",
        "plan_summary",
        "tool_calls",
        "tool_results",
        "final_answer",
        "provenance",
    }
    if not isinstance(sample, dict) or set(sample) != fields:
        raise SampleError("sample_fields_invalid")
    for key in (
        "sample_id",
        "source_id",
        "family_id",
        "question",
        "plan_summary",
        "final_answer",
    ):
        if not isinstance(sample[key], str) or not 1 <= len(sample[key].strip()) <= 200:
            raise SampleError("sample_text_invalid")
    if sample["source_id"] not in sources:
        raise SampleError("source_unknown")
    source = sources[sample["source_id"]]
    if sample["family_id"] != source["family_id"]:
        raise SampleError("family_mismatch")
    provenance = sample["provenance"]
    if not isinstance(provenance, dict) or set(provenance) != {
        "source_version",
        "origin",
        "generator",
        "generation_model",
        "usage_policy",
        "revision",
    }:
        raise SampleError("provenance_invalid")
    if (
        provenance["source_version"] != source["version"]
        or provenance["usage_policy"] != source["usage_policy"]
        or source["usage_policy"] != "local_teaching_only"
    ):
        raise SampleError("source_version_or_usage_invalid")
    if (
        provenance["origin"] != "rule_generated_fixture"
        or provenance["generator"] != "fixed-addition-v1"
        or provenance["generation_model"] is not None
        or type(provenance["revision"]) is not int
        or provenance["revision"] < 1
    ):
        raise SampleError("generation_metadata_invalid")
    allowed = [
        normalize_text(text)
        for text in questions(source["order"], source["left"], source["right"])
    ]
    if normalize_text(sample["question"]) not in allowed:
        raise SampleError("question_source_mismatch")
    calls, results = sample["tool_calls"], sample["tool_results"]
    if (
        not isinstance(calls, list)
        or not isinstance(results, list)
        or len(calls) != 1
        or len(results) != 1
    ):
        raise SampleError("trace_length_invalid")
    call, result = calls[0], results[0]
    if (
        not isinstance(call, dict)
        or set(call) != {"id", "name", "arguments"}
        or not isinstance(call["id"], str)
        or not call["id"]
    ):
        raise SampleError("call_fields_invalid")
    if call["name"] != "add_units":
        raise SampleError("tool_not_allowed")
    arguments = call["arguments"]
    if not isinstance(arguments, dict) or set(arguments) != {"left", "right"}:
        raise SampleError("tool_arguments_invalid")
    total = add_units(arguments["left"], arguments["right"])
    if arguments != {"left": source["left"], "right": source["right"]}:
        raise SampleError("arguments_source_mismatch")
    if (
        not isinstance(result, dict)
        or set(result) != {"call_id", "total"}
        or result["call_id"] != call["id"]
    ):
        raise SampleError("call_result_unmatched")
    if type(result["total"]) is not int or result["total"] != total:
        raise SampleError("tool_result_wrong")
    if sample["final_answer"] != f"合成总数量为{total}件。":
        raise SampleError("answer_wrong")
    return {
        "sample_id": sample["sample_id"],
        "structural_valid": True,
        "trace_replayed": True,
        "fixture_answer_correct": True,
        "general_semantics_verified": False,
    }


def clean_samples(samples, sources):
    valid, rejected = [], []
    seen_ids = set()
    for sample in samples:
        identifier = sample.get("sample_id") if isinstance(sample, dict) else None
        try:
            validate_sample(sample, sources)
            if identifier in seen_ids:
                raise SampleError("sample_id_duplicate")
            seen_ids.add(identifier)
            valid.append(sample)
        except SampleError as error:
            rejected.append({"sample_id": identifier, "reason": str(error)})
    return valid, rejected

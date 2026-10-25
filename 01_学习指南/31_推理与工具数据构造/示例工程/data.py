"""生成明确合成的候选轨迹；不调用模型，不读取个人对话。"""

import copy
import json
import unicodedata


def normalize_text(text):
    return " ".join(unicodedata.normalize("NFKC", text).casefold().split())


def questions(order, left, right):
    return [
        f"合成订单{order:02d}：{left}件和{right}件，共有多少件？",
        f"请计算合成订单{order:02d}的两批数量：{left} + {right}。",
    ]


def make_sources():
    sources = {}
    for order in range(24):
        sources[f"source-{order:02d}"] = {
            "order": order,
            "left": order + 1,
            "right": order % 5 + 1,
            "family_id": f"family-{order:02d}",
            "version": "v1",
            "origin": "author_synthetic_fixture",
            "usage_policy": "local_teaching_only",
        }
    return sources


def make_sample(source_id, source, variant):
    total = source["left"] + source["right"]
    return {
        "sample_id": f"sample-{source['order']:02d}-{variant}",
        "source_id": source_id,
        "family_id": source["family_id"],
        "question": questions(source["order"], source["left"], source["right"])[
            variant
        ],
        "plan_summary": "调用add_units合并两批合成数量，并依据返回值作答。",
        "tool_calls": [
            {
                "id": "call-1",
                "name": "add_units",
                "arguments": {"left": source["left"], "right": source["right"]},
            }
        ],
        "tool_results": [{"call_id": "call-1", "total": total}],
        "final_answer": f"合成总数量为{total}件。",
        "provenance": {
            "source_version": "v1",
            "origin": "rule_generated_fixture",
            "generator": "fixed-addition-v1",
            "generation_model": None,
            "usage_policy": "local_teaching_only",
            "revision": 1,
        },
    }


def make_raw_samples():
    samples = []
    for source_id, source in make_sources().items():
        for variant in (0, 1):
            samples.append(make_sample(source_id, source, variant))
    for index in range(2):
        duplicate = copy.deepcopy(samples[index])
        duplicate["sample_id"] = f"duplicate-{index}"
        duplicate["question"] = "  " + duplicate["question"] + "  "
        samples.append(duplicate)
    for reason in (
        "wrong_answer",
        "wrong_result",
        "bad_call_id",
        "unknown_tool",
        "unknown_source",
    ):
        bad = copy.deepcopy(samples[0])
        bad["sample_id"] = "bad-" + reason
        if reason == "wrong_answer":
            bad["final_answer"] = "合成总数量为999件。"
        elif reason == "wrong_result":
            bad["tool_results"][0]["total"] = 999
        elif reason == "bad_call_id":
            bad["tool_results"][0]["call_id"] = "call-missing"
        elif reason == "unknown_tool":
            bad["tool_calls"][0]["name"] = "send_order"
        else:
            bad["source_id"] = "missing"
        samples.append(bad)
    return samples


def fingerprint(sample):
    # 不含sample_id：同一内容改ID不能逃过去重；数字和调用信息保留。
    content = {
        "question": normalize_text(sample["question"]),
        "calls": sample["tool_calls"],
        "results": sample["tool_results"],
        "answer": normalize_text(sample["final_answer"]),
    }
    return json.dumps(
        content, sort_keys=True, ensure_ascii=False, separators=(",", ":")
    )


def deduplicate(samples):
    unique, duplicates = [], []
    seen = {}
    for sample in samples:
        # 内容相同但来源/题族/修订或计划不同，先保留用于关联与人工核查。
        key = (
            fingerprint(sample),
            sample["source_id"],
            sample["family_id"],
            sample["plan_summary"],
            json.dumps(sample["provenance"], sort_keys=True),
        )
        if key in seen:
            duplicates.append({"removed": sample["sample_id"], "kept": seen[key]})
        else:
            seen[key] = sample["sample_id"]
            unique.append(copy.deepcopy(sample))
    return unique, duplicates
